"""
Authorization backend system for AgentFlow CLI.

This module provides an authorization interface that developers can implement
to add resource-level access control to their AgentFlow applications.
"""

from abc import ABC, abstractmethod
from typing import Any


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
        pass


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
