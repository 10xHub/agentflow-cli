import importlib
import inspect
import logging
import os
from pathlib import Path

from agentflow.core import CompiledGraph
from agentflow.storage.checkpointer import BaseCheckpointer
from agentflow.storage.store import BaseStore
from injectq import InjectQ

from agentflow_cli import BaseAuth
from agentflow_cli.src.app.core.auth.authorization import (
    AuthorizationBackend,
    DefaultAuthorizationBackend,
    OwnershipAuthorizationBackend,
    RoleBasedAuthorizationBackend,
)
from agentflow_cli.src.app.core.config.graph_config import GraphConfig
from agentflow_cli.src.app.utils.thread_name_generator import ThreadNameGenerator


logger = logging.getLogger("agentflow-cli.loader")


async def load_graph(path: str) -> CompiledGraph | None:
    if ":" not in path:
        raise ValueError(f"Invalid graph path format '{path}'. Expected 'module:attribute'.")

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)

        if callable(entry_point_obj):
            if inspect.iscoroutinefunction(entry_point_obj):
                app = await entry_point_obj()
            else:
                app = entry_point_obj()
        else:
            app = entry_point_obj

        if app is None:
            raise RuntimeError(f"Failed to obtain a runnable graph from {path}.")

        if isinstance(app, CompiledGraph):
            logger.info(f"Successfully loaded graph '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a CompiledGraph.")

    except ModuleNotFoundError as e:
        logger.error(f"Module not found when loading graph from {path}: {e}")
        raise ModuleNotFoundError(f"Module not found for graph path '{path}': {e}")
    except AttributeError as e:
        logger.error(f"Attribute not found when loading graph from {path}: {e}")
        raise AttributeError(f"Attribute not found for graph path '{path}': {e}")
    except Exception as e:
        logger.error(f"Error loading graph from {path}: {e}")
        raise Exception(f"Failed to load graph from {path}: {e}")

    return app


def load_checkpointer(path: str | None) -> BaseCheckpointer | None:
    if not path:
        return None

    if ":" not in path:
        raise ValueError(f"Invalid checkpointer path format '{path}'. Expected 'module:attribute'.")

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)
        checkpointer = entry_point_obj

        if checkpointer is None:
            raise RuntimeError(f"Failed to obtain a BaseCheckpointer graph from {path}.")

        if isinstance(checkpointer, BaseCheckpointer):
            logger.info(f"Successfully loaded BaseCheckpointer '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a BaseCheckpointer.")
    except ModuleNotFoundError as e:
        logger.error(f"Module not found when loading BaseCheckpointer from {path}: {e}")
        raise ModuleNotFoundError(f"Module not found for checkpointer path '{path}': {e}")
    except AttributeError as e:
        logger.error(f"Attribute not found when loading BaseCheckpointer from {path}: {e}")
        raise AttributeError(f"Attribute not found for checkpointer path '{path}': {e}")
    except Exception as e:
        logger.error(f"Error loading BaseCheckpointer from {path}: {e}")
        raise Exception(f"Failed to load BaseCheckpointer from {path}: {e}")

    return checkpointer


def load_store(path: str | None) -> BaseStore | None:
    if not path:
        return None

    if ":" not in path:
        raise ValueError(f"Invalid store path format '{path}'. Expected 'module:attribute'.")

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)
        store = entry_point_obj

        if store is None:
            raise RuntimeError(f"Failed to obtain a BaseStore from {path}.")

        if isinstance(store, BaseStore):
            logger.info(f"Successfully loaded graph '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a BaseStore.")
    except ModuleNotFoundError as e:
        logger.error(f"Module not found when loading BaseStore from {path}: {e}")
        raise ModuleNotFoundError(f"Module not found for store path '{path}': {e}")
    except AttributeError as e:
        logger.error(f"Attribute not found when loading BaseStore from {path}: {e}")
        raise AttributeError(f"Attribute not found for store path '{path}': {e}")
    except Exception as e:
        logger.error(f"Error loading BaseStore from {path}: {e}")
        raise Exception(f"Failed to load BaseStore from {path}: {e}")

    return store


def load_container(path: str | None) -> InjectQ | None:
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)
        container = entry_point_obj

        if container is None:
            raise RuntimeError(f"Failed to obtain a InjectQ from {path}.")

        if isinstance(container, InjectQ):
            logger.info(f"Successfully loaded InjectQ '{function_name}' from {path}.")
        else:
            raise TypeError("Loaded object is not a InjectQ.")
    except Exception as e:
        logger.error(f"Error loading InjectQ from {path}: {e}")
        raise Exception(f"Failed to load InjectQ from {path}: {e}")

    # if we have container, set it as the global instance
    if container:
        container.activate()

    return container


def load_auth(path: str | None) -> BaseAuth | None:
    if not path:
        return None

    if ":" not in path:
        raise ValueError(f"Invalid auth path format '{path}'. Expected 'module:attribute'.")

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)

        if inspect.isclass(entry_point_obj) and issubclass(entry_point_obj, BaseAuth):
            auth = entry_point_obj()
        elif isinstance(entry_point_obj, BaseAuth):
            auth = entry_point_obj
        else:
            raise TypeError("Loaded object is not a subclass or instance of BaseAuth.")

        logger.info(f"Successfully loaded BaseAuth '{function_name}' from {path}.")
    except ModuleNotFoundError as e:
        logger.error(f"Module not found when loading BaseAuth from {path}: {e}")
        raise ModuleNotFoundError(f"Module not found for auth path '{path}': {e}")
    except AttributeError as e:
        logger.error(f"Attribute not found when loading BaseAuth from {path}: {e}")
        raise AttributeError(f"Attribute not found for auth path '{path}': {e}")
    except Exception as e:
        logger.error(f"Error loading BaseAuth from {path}: {e}")
        raise Exception(f"Failed to load BaseAuth from {path}: {e}")

    return auth


def load_authorization(path: str | None) -> AuthorizationBackend | None:
    """
    Load authorization backend from the specified path.

    Args:
        path: Module path in format 'module:attribute' or None

    Returns:
        AuthorizationBackend instance or None if path is not provided

    Raises:
        Exception: If loading fails or object is not AuthorizationBackend
    """
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)

        # If it's a class, instantiate it; if it's an instance, use as is
        if inspect.isclass(entry_point_obj) and issubclass(entry_point_obj, AuthorizationBackend):
            authorization = entry_point_obj()
        elif isinstance(entry_point_obj, AuthorizationBackend):
            authorization = entry_point_obj
        else:
            raise TypeError("Loaded object is not a subclass or instance of AuthorizationBackend.")

        logger.info(f"Successfully loaded AuthorizationBackend '{function_name}' from {path}.")
    except Exception as e:
        logger.error(f"Error loading AuthorizationBackend from {path}: {e}")
        raise Exception(f"Failed to load AuthorizationBackend from {path}: {e}")

    return authorization


def load_thread_name_generator(path: str | None) -> ThreadNameGenerator | None:
    if not path:
        return None

    module_name_importable, function_name = path.split(":")

    try:
        module = importlib.import_module(module_name_importable)
        entry_point_obj = getattr(module, function_name)

        # If it's a class, instantiate it; if it's an instance, use as is
        if inspect.isclass(entry_point_obj) and issubclass(entry_point_obj, ThreadNameGenerator):
            thread_name_generator = entry_point_obj()
        elif isinstance(entry_point_obj, ThreadNameGenerator):
            thread_name_generator = entry_point_obj
        else:
            raise TypeError("Loaded object is not a subclass or instance of ThreadNameGenerator.")

        logger.info(f"Successfully loaded ThreadNameGenerator '{function_name}' from {path}.")
    except Exception as e:
        logger.error(f"Error loading ThreadNameGenerator from {path}: {e}")
        raise Exception(f"Failed to load ThreadNameGenerator from {path}: {e}")

    return thread_name_generator


def load_and_bind_auth(container: InjectQ, auth_config: dict) -> None:
    from agentflow_cli.src.app.core.auth.jwt_auth import JwtAuth

    method = auth_config.get("method")
    path = auth_config.get("path")
    if not path or not method:
        raise ValueError("Both 'method' and 'path' must be specified in auth_config.")

    # Extract file path before the ':' for existence check
    module_or_path = path.split(":", 1)[0] if ":" in path else path

    # Simple handling: if it appears to be a filesystem path, use it; otherwise
    # convert dotted module path to a file path like src/auth/custom_auth.py
    if os.path.sep in module_or_path or module_or_path.endswith(".py"):
        file_path = Path(module_or_path)
    elif "." in module_or_path and os.path.sep not in module_or_path:
        file_path = Path(module_or_path.replace(".", os.path.sep) + ".py")
    else:
        file_path = Path(module_or_path)

    if not file_path.exists():
        raise ValueError(f"Custom auth path does not exist: {module_or_path}")

    auth_backends = {
        "custom": lambda: load_auth(path),
        "jwt": lambda: JwtAuth(),
        "none": lambda: None,
    }

    auth_backend = auth_backends.get(method, lambda: None)()
    container.bind_instance(BaseAuth, auth_backend, allow_none=True)


# Built-in authorization backends selectable by name in ``agentflow.json``.
_BUILTIN_AUTHORIZATION = {
    "ownership": OwnershipAuthorizationBackend,  # object-level: owner-only thread access
    "allow_all": DefaultAuthorizationBackend,  # authenticated == authorized
    "default": DefaultAuthorizationBackend,  # alias for allow_all
    "none": DefaultAuthorizationBackend,  # alias for allow_all
}


def _build_ownership_redis(redis_url: str | None) -> object | None:
    """Build an async Redis client for the ownership L2 cache, or None.

    Returns None (L1-only) when no URL is configured or the ``redis`` package is absent;
    the resolver degrades gracefully either way.
    """
    if not redis_url:
        return None
    try:
        from redis.asyncio import Redis as AsyncRedis  # type: ignore[import]
    except ImportError:
        logger.warning(
            "REDIS configured but the 'redis' package is not installed; ownership cache "
            "runs in-process only (L1). Install the redis extra to share it across workers."
        )
        return None
    try:
        client = AsyncRedis.from_url(redis_url, decode_responses=False)
        logger.info("Ownership authorization L2 cache enabled (shared Redis).")
        return client
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to build ownership Redis client: %s; using L1 cache only.", exc)
        return None


def _resolve_authorization_backend(
    authorization: str | dict | None, redis_url: str | None = None
) -> AuthorizationBackend:
    """Pick the authorization backend from config, defaulting by run mode.

    Resolution order (developer choice always wins):

    1. A dict ``{"backend": "rbac", "roles": {...}, ...}`` -> role-based access control.
    2. ``"module:attr"`` -> the developer's custom :class:`AuthorizationBackend`.
    3. A built-in name (``"ownership"``, ``"allow_all"``/``"default"``/``"none"``) ->
       that backend, regardless of mode.
    4. Not configured (``null``) -> secure-by-default in production
       (:class:`OwnershipAuthorizationBackend`), permissive in development
       (:class:`DefaultAuthorizationBackend`). Either can be overridden via (1)/(2)/(3).

    ``redis_url`` (when set) backs the ownership cache's shared L2 tier.
    """
    # 1. Config-driven RBAC: {"backend": "rbac", "roles": {...}, "default_scopes": [...]}
    if isinstance(authorization, dict):
        backend_name = (authorization.get("backend") or authorization.get("type") or "").lower()
        if backend_name in ("rbac", "role_based", "roles"):
            logger.info("Using RoleBasedAuthorizationBackend (config-driven roles).")
            return RoleBasedAuthorizationBackend(
                role_scopes=authorization.get("roles") or authorization.get("role_scopes") or {},
                default_scopes=authorization.get("default_scopes") or (),
                isolation=authorization.get("isolation", "owner"),
                redis=_build_ownership_redis(redis_url),
            )
        raise ValueError(
            f"Unknown authorization backend config: {authorization!r}. For RBAC use "
            '{"backend": "rbac", "roles": {...}}.'
        )

    if authorization and ":" in authorization:
        backend = load_authorization(authorization)
        logger.info("Using custom AuthorizationBackend from '%s'.", authorization)
        return backend  # type: ignore[return-value]

    if authorization:
        key = authorization.strip().lower()
        builtin = _BUILTIN_AUTHORIZATION.get(key)
        if builtin is None:
            raise ValueError(
                f"Unknown authorization backend '{authorization}'. Use a 'module:attr' "
                f"path or one of: {', '.join(sorted(_BUILTIN_AUTHORIZATION))}."
            )
        logger.info("Using built-in '%s' authorization backend.", key)
        if builtin is OwnershipAuthorizationBackend:
            return OwnershipAuthorizationBackend(redis=_build_ownership_redis(redis_url))
        return builtin()

    # Not configured: default by mode.
    from agentflow_cli.src.app.core.config.settings import get_settings

    if get_settings().MODE == "production":
        logger.info(
            "No authorization configured; defaulting to OwnershipAuthorizationBackend "
            "(owner-only thread access) because MODE=production. Set "
            '"authorization": "allow_all" to opt out.'
        )
        return OwnershipAuthorizationBackend(redis=_build_ownership_redis(redis_url))

    logger.info(
        "No authorization configured; defaulting to DefaultAuthorizationBackend "
        "(allows all authenticated users) in development. Set "
        '"authorization": "ownership" to enforce owner-only access here too.'
    )
    return DefaultAuthorizationBackend()


def load_and_bind_authorization(
    container: InjectQ,
    authorization_path: str | None,
    redis_url: str | None = None,
) -> None:
    backend = _resolve_authorization_backend(authorization_path, redis_url)
    container.bind_instance(AuthorizationBackend, backend)


async def attach_all_modules(
    config: GraphConfig,
    container: InjectQ,
) -> CompiledGraph | None:
    graph = await load_graph(config.graph_path)
    logger.info("All modules attached successfully")

    # This binding we have done already in the library
    # # Bind checkpointer instance if configured
    # checkpointer = load_checkpointer(config.checkpointer_path)
    # container.bind_instance(BaseCheckpointer, checkpointer, allow_none=True)

    # Bind the store instance (if configured) so the /v1/store endpoints — which
    # inject BaseStore via StoreService — can serve it. Without this the store
    # router reports "Store is not configured" even when agentflow.json sets one.
    store = load_store(config.store_path)
    container.bind_instance(BaseStore, store, allow_none=True)

    # Bind the in-memory telemetry store so the graph service can record run
    # events and the /v1/observability endpoints can reconstruct traces.
    #
    # This is a dev-only convenience: it lets the playground show a trace without
    # any external observability backend. It is NOT durable and NOT meant for
    # production (use OTEL / a publisher there instead). So we only bind it
    # outside production; in production the store stays unbound and the
    # /v1/observability endpoints return a clean, empty "disabled" response.
    from agentflow_cli.src.app.core.config.settings import get_settings
    from agentflow_cli.src.app.utils.telemetry_store import TelemetryStore

    if get_settings().MODE != "production":
        container.bind_instance(TelemetryStore, TelemetryStore())
        logger.info("Local in-memory telemetry store bound (dev mode)")
    else:
        logger.info("Production mode: local telemetry store disabled (use OTEL/publisher)")

    # load auth backend
    auth_config = config.auth_config()
    if auth_config:
        load_and_bind_auth(container, auth_config)
    else:
        # Auth disabled is a legitimate choice (single-user / trusted network), but it
        # must not be silent -- an operator who simply forgot to set `auth` should see
        # it at startup. This warns; it does not force auth on.
        logger.warning(
            "⚠️  Authentication is DISABLED (no `auth` configured). Every request runs "
            "as `anonymous` with no access control. This is fine for single-user or "
            "trusted-network deployments; set `auth` in agentflow.json to enable it."
        )
        # bind None
        container.bind_instance(BaseAuth, None, allow_none=True)

    # load thread name generator
    thread_name_generator_path = config.thread_name_generator_path
    if thread_name_generator_path:
        thread_name_generator = load_thread_name_generator(thread_name_generator_path)
        container.bind_instance(ThreadNameGenerator, thread_name_generator)
    else:
        # bind None if not configured
        container.bind_instance(ThreadNameGenerator, None, allow_none=True)

    # load authorization backend. The ownership cache's shared L2 tier reuses the
    # configured Redis URL (config `redis`, else settings.REDIS_URL); absent -> L1 only.
    from agentflow_cli.src.app.core.config.settings import get_settings

    authorization_path = config.authorization_path
    ownership_redis_url = config.redis_url or get_settings().REDIS_URL
    load_and_bind_authorization(container, authorization_path, ownership_redis_url)

    # --- Media service wiring ---
    from agentflow_cli.src.app.core.config.media_settings import (
        MediaSettings,
        get_media_settings,
    )
    from agentflow_cli.src.app.routers.media import MediaService

    media_settings = get_media_settings()
    container.bind_instance(MediaSettings, media_settings)
    media_service = MediaService(settings=media_settings)
    container.bind_instance(MediaService, media_service)

    logger.info("Container loaded successfully")
    logger.debug(f"Container dependency graph: {container.get_dependency_graph()}")

    return graph
