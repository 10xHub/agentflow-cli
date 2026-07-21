"""
Authorization backend system for AgentFlow CLI.

This module provides an authorization interface that developers can implement
to add resource-level access control to their AgentFlow applications.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any


logger = logging.getLogger("agentflow-cli.authorization")


class AuthorizationBackend(ABC):
    """
    Abstract base class for authorization backends.

    Developers should implement this class to define custom authorization logic
    for their AgentFlow applications. The authorize method is called before
    any resource operation to check if the user has permission.

    Example:
        class MyAuthorizationBackend(AuthorizationBackend):
            async def authorize(self, user, resource, action, resource_id=None, **context):
                # Check if user has permission
                if user.get("role") == "admin":
                    return True
                # Add custom logic here
                return False
    """

    @abstractmethod
    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context: Any,
    ) -> bool:
        """
        Check if user can perform action on resource.

        Args:
            user: User information dictionary containing at least 'user_id'
            resource: Resource type (e.g., 'graph', 'checkpointer', 'store')
            action: Action to perform (e.g., 'invoke', 'stream', 'read', 'write', 'delete')
            resource_id: Optional specific resource identifier (e.g., thread_id, namespace)
            **context: Additional context for authorization decision

        Returns:
            bool: True if authorized, False otherwise

        Raises:
            Exception: Can raise exceptions for auth failures or errors
        """

    def isolation_scope(self) -> str:
        """The data-isolation policy this backend implies, sent to storage per request.

        The API stamps this (server-side, non-hijackable) into ``config["policy"]`` so the
        checkpointer scopes storage the *same* way this backend decides access -- no
        contradiction between "allow_all" authz and a data layer that still filters.

        - ``"owner"`` -> storage is scoped to the caller's ``user_id`` (owner-only).
        - ``"none"``  -> storage is not scoped (any authenticated user sees everything).

        Defaults to ``"none"``. Override (or return ``"owner"``) to make a custom backend
        drive per-user storage isolation too.
        """
        return "none"

    def scopes_for(self, user: dict[str, Any]) -> list[str] | None:
        """Return the scopes this identity is granted, or None for "unrestricted".

        ``RequirePermission`` checks the required ``"<resource>:<action>"`` scope against
        this list. Returning ``None`` means the identity is not scope-restricted
        (permissive -- the default, so nothing breaks until scopes are issued).

        The default passes through scopes the identity already carries
        (``user["scopes"]``, e.g. from a JWT ``scope`` claim). A role-based backend
        overrides this to map ``user["roles"]`` to scopes.
        """
        scopes = user.get("scopes") if isinstance(user, dict) else None
        if isinstance(scopes, list | tuple | set | frozenset):
            return list(scopes)
        return None


class DefaultAuthorizationBackend(AuthorizationBackend):
    """
    Default authorization backend that allows all authenticated users.

    This implementation performs basic authentication check (user has user_id)
    but allows all operations. Use this as a starting point or for development.

    For production use, implement a custom AuthorizationBackend with proper
    access control logic based on your application's requirements.
    """

    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context: Any,
    ) -> bool:
        """
        Allow all authenticated users to perform any action.

        Args:
            user: User information dictionary
            resource: Resource type (not used in default implementation)
            action: Action to perform (not used in default implementation)
            resource_id: Optional resource identifier (not used in default implementation)
            **context: Additional context (not used in default implementation)

        Returns:
            bool: True if user has 'user_id', False otherwise
        """
        # Only check if user is authenticated (has user_id)
        return bool(user.get("user_id"))


class OwnershipAuthorizationBackend(AuthorizationBackend):
    """Object-level authorization: a user may only touch threads they own.

    This is the built-in "secure" backend. It enforces the rule most multi-tenant
    apps want without the developer writing any code: *a thread can be read, mutated,
    stopped or fixed only by the user who owns it.* Ownership is resolved from the
    configured checkpointer, whose thread registry records the owning ``user_id``.

    Decision table (for the thread-scoped resources ``graph`` and ``checkpointer``):

    - No ``user_id`` on the request -> deny (must be authenticated).
    - No ``resource_id`` (list / create-without-id, e.g. ``GET /v1/threads``, the graph
      schema endpoint) -> allow; those paths are already user-scoped by the service.
    - The thread does not exist yet -> allow (a brand-new session / empty read). For
      ``invoke``/``stream`` this starts a new thread owned by the caller.
    - The thread exists and the caller owns it -> allow.
    - The thread exists and is owned by someone else -> **deny, for every action**
      including ``invoke`` and ``stream``. This is the whole point: you cannot read,
      continue, stop, fix, or run another user's thread.

    Resources other than ``graph``/``checkpointer`` (store, files) are allowed through:
    they enforce their own per-user scoping (the store keys on ``user_id``; media checks
    file ownership in ``MediaService``).

    Ownership is resolved through a :class:`ThreadOwnershipResolver` in front of
    :meth:`BaseCheckpointer.aget_thread_owner`. Ownership is immutable, so the resolver
    caches it (in-process, plus optional shared Redis) -- after the first lookup a check is
    an in-memory hit, not a database round-trip per request. A checkpointer that cannot
    resolve ownership (raises ``NotImplementedError``) or that is not configured leaves
    nothing to enforce, so requests pass through with a warning. The in-memory checkpointer
    only records a thread when one is explicitly written, which is why this backend is the
    production default (Postgres) while development defaults to
    :class:`DefaultAuthorizationBackend`.
    """

    # Resources whose ``resource_id`` is a thread_id and therefore ownership-checkable.
    THREAD_RESOURCES = frozenset({"graph", "checkpointer"})

    def isolation_scope(self) -> str:
        # Owner-only access -> storage must be scoped to the caller too.
        return "owner"

    def __init__(
        self,
        checkpointer: Any | None = None,
        *,
        resolver: Any | None = None,
        redis: object | None = None,
    ) -> None:
        self._checkpointer = checkpointer
        self._resolver = resolver
        self._redis = redis
        self._resolver_built = resolver is not None

    @property
    def checkpointer(self) -> Any | None:
        """Resolve the checkpointer lazily from the DI container if not injected."""
        if self._checkpointer is None:
            try:
                from agentflow.storage.checkpointer import BaseCheckpointer
                from injectq import InjectQ

                self._checkpointer = InjectQ.get_instance().try_get(BaseCheckpointer)
            except Exception:  # pragma: no cover - defensive
                self._checkpointer = None
        return self._checkpointer

    def _get_resolver(self) -> Any | None:
        """Return the cached ownership resolver, building it once from the checkpointer.

        Returns None when no checkpointer is available (nothing to resolve).
        """
        if self._resolver_built:
            return self._resolver
        self._resolver_built = True
        cp = self.checkpointer
        if cp is None:
            self._resolver = None
        else:
            from agentflow_cli.src.app.core.auth.ownership_resolver import (
                ThreadOwnershipResolver,
            )

            self._resolver = ThreadOwnershipResolver(cp.aget_thread_owner, redis=self._redis)
        return self._resolver

    def evict(self, thread_id: str | int) -> Any:
        """Invalidate a thread's cached ownership (call on thread deletion).

        Returns the resolver's ``evict`` coroutine when a resolver exists, so callers may
        ``await`` it; returns None when there is nothing to evict.
        """
        resolver = self._get_resolver()
        if resolver is None:
            return None
        return resolver.evict(thread_id)

    async def aclose(self) -> None:
        """Close the L2 Redis client this backend created (called on app shutdown)."""
        client = self._redis
        if client is not None and hasattr(client, "aclose"):
            try:
                await client.aclose()
            except Exception as exc:  # pragma: no cover - best-effort shutdown
                logger.debug("Ownership Redis client close failed: %s", exc)

    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context: Any,
    ) -> bool:
        user_id = user.get("user_id") if user else None
        if not user_id:
            return False

        # Only thread-scoped resources are ownership-checked here.
        if resource not in self.THREAD_RESOURCES:
            return True

        # Endpoints without a specific thread (list/create) are user-scoped by the
        # service layer; nothing to authorize at the object level.
        if resource_id is None:
            return True

        resolver = self._get_resolver()
        if resolver is None:
            logger.warning(
                "Ownership authorization is active but no checkpointer is configured; "
                "allowing %s:%s (no persisted threads to protect).",
                resource,
                action,
            )
            return True

        return await self._authorize_ownership(
            resolver, str(resource_id), str(user_id), resource, action
        )

    async def _authorize_ownership(
        self,
        resolver: Any,
        resource_id: str,
        user_id: str,
        resource: str,
        action: str,
    ) -> bool:
        try:
            owner = await resolver.owner_of(resource_id)
        except NotImplementedError:
            logger.warning(
                "Checkpointer %s cannot resolve thread ownership; ownership "
                "authorization is inactive for %s:%s. Use a checkpointer that "
                "implements aget_thread_owner (e.g. PgCheckpointer) or configure a "
                "custom AuthorizationBackend.",
                type(self.checkpointer).__name__,
                resource,
                action,
            )
            return True
        except Exception as exc:
            # Fail closed: a resolution error must not silently grant access.
            logger.warning(
                "Ownership check failed for thread %s (user %s): %s; denying.",
                resource_id,
                user_id,
                exc,
            )
            return False

        # Unknown thread -> brand-new session (or an empty read); allow. Otherwise the
        # caller must be the owner, for EVERY action (invoke/stream included).
        if owner is None:
            return True
        return str(owner) == user_id


class RoleBasedAuthorizationBackend(OwnershipAuthorizationBackend):
    """RBAC: map a user's roles to scopes, on top of owner-only object isolation.

    Combines two things in one backend:

    - **Scopes** (what actions are allowed) -- ``scopes_for`` maps ``user["roles"]`` (or
      ``user["role"]``) to a set of scopes via the ``role_scopes`` table. ``RequirePermission``
      then enforces the required ``"<resource>:<action>"`` scope. A role granting ``"*"``
      gets every scope in :data:`agentflow.core.authz.ALL_SCOPES`.
    - **Isolation** (which rows are visible) -- inherited from
      :class:`OwnershipAuthorizationBackend` (owner-only threads), configurable via
      ``isolation``.

    Example::

        RoleBasedAuthorizationBackend(
            role_scopes={
                "admin": ["*"],
                "member": ["graph:invoke", "graph:stream", "checkpointer:read"],
            },
            default_scopes=["graph:read"],  # granted to everyone, even with no role
        )
    """

    def __init__(
        self,
        role_scopes: dict[str, Any] | None = None,
        *,
        default_scopes: Any = (),
        isolation: str = "owner",
        checkpointer: Any | None = None,
        resolver: Any | None = None,
        redis: object | None = None,
    ) -> None:
        super().__init__(checkpointer=checkpointer, resolver=resolver, redis=redis)
        self._role_scopes = {str(r): list(s) for r, s in (role_scopes or {}).items()}
        self._default_scopes = list(default_scopes)
        self._isolation = isolation if isolation in ("owner", "none") else "owner"

    def isolation_scope(self) -> str:
        return self._isolation

    @staticmethod
    def _roles_of(user: dict[str, Any]) -> list[str]:
        if not isinstance(user, dict):
            return []
        roles = user.get("roles")
        if roles is None:
            role = user.get("role")
            roles = [role] if role else []
        elif isinstance(roles, str):
            roles = [roles]
        return [str(r) for r in roles]

    def scopes_for(self, user: dict[str, Any]) -> list[str]:
        from agentflow.core.authz import ALL_SCOPES

        granted: set[str] = set(self._default_scopes)
        for role in self._roles_of(user):
            granted.update(self._role_scopes.get(role, []))
        if "*" in granted:
            return sorted(ALL_SCOPES)
        return sorted(granted)
