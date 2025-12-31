"""
Role-Based Access Control (RBAC) Authorization Example

This example demonstrates how to implement RBAC authorization in AgentFlow CLI.

RBAC Model:
- Roles: admin, developer, viewer
- Permissions: Defined per resource and action
- Assignment: Users have one or more roles

Setup:
1. Create this file in your project (e.g., auth/rbac_backend.py)
2. Configure agentflow.json to use this backend
3. Ensure user context includes 'role' field
"""

from typing import Any

# Import the authorization backend interface
# In your project: from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend


class RBACAuthorizationBackend(AuthorizationBackend):
    """
    Role-Based Access Control (RBAC) authorization backend.

    Defines permissions for different roles across all resources.
    """

    # Permission matrix: role -> resource -> [actions]
    PERMISSIONS = {
        "admin": {
            # Admins have full access to everything
            "graph": ["invoke", "stream", "read", "stop", "setup", "fix"],
            "checkpointer": ["read", "write", "delete"],
            "store": ["read", "write", "delete", "forget"],
        },
        "developer": {
            # Developers can execute graphs and manage data
            "graph": ["invoke", "stream", "read", "setup"],
            "checkpointer": ["read", "write"],
            "store": ["read", "write"],
        },
        "viewer": {
            # Viewers have read-only access
            "graph": ["read"],
            "checkpointer": ["read"],
            "store": ["read"],
        },
        "guest": {
            # Guests have minimal access
            "graph": [],
            "checkpointer": [],
            "store": [],
        },
    }

    def __init__(self):
        """Initialize RBAC backend."""
        print("RBAC Authorization Backend initialized")
        print(f"Configured roles: {', '.join(self.PERMISSIONS.keys())}")

    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context,
    ) -> bool:
        """
        Check if user's role has permission for the requested action.

        Args:
            user: User context (must include 'role' field)
            resource: Resource being accessed (e.g., 'graph', 'checkpointer')
            action: Action being performed (e.g., 'invoke', 'read', 'write')
            resource_id: Optional specific resource identifier
            **context: Additional context for authorization decision

        Returns:
            True if authorized, False otherwise
        """
        # Extract user information
        user_id = user.get("user_id", "unknown")
        role = user.get("role", "guest")  # Default to 'guest' if no role

        # Get permissions for the user's role
        role_permissions = self.PERMISSIONS.get(role, {})

        # Get allowed actions for the resource
        allowed_actions = role_permissions.get(resource, [])

        # Check if action is permitted
        is_authorized = action in allowed_actions

        # Log authorization decision
        if is_authorized:
            print(f"✓ Authorization granted: {user_id} ({role}) can {action} on {resource}")
        else:
            print(f"✗ Authorization denied: {user_id} ({role}) cannot {action} on {resource}")
            print(f"  Allowed actions: {allowed_actions}")

        return is_authorized


class HierarchicalRBACBackend(AuthorizationBackend):
    """
    Hierarchical RBAC with role inheritance.

    Roles can inherit permissions from parent roles:
    admin > developer > viewer > guest
    """

    # Define role hierarchy (child -> parent)
    ROLE_HIERARCHY = {
        "admin": ["developer", "viewer", "guest"],
        "developer": ["viewer", "guest"],
        "viewer": ["guest"],
        "guest": [],
    }

    # Base permissions per role
    BASE_PERMISSIONS = {
        "admin": {
            "graph": ["stop", "fix"],  # Admin-only actions
            "checkpointer": ["delete"],
            "store": ["delete", "forget"],
        },
        "developer": {
            "graph": ["invoke", "stream", "setup"],
            "checkpointer": ["write"],
            "store": ["write"],
        },
        "viewer": {"graph": ["read"], "checkpointer": ["read"], "store": ["read"]},
        "guest": {
            # No base permissions
        },
    }

    def __init__(self):
        """Initialize hierarchical RBAC backend."""
        print("Hierarchical RBAC Authorization Backend initialized")

    def get_all_permissions(self, role: str) -> dict[str, list[str]]:
        """
        Get all permissions for a role, including inherited ones.

        Args:
            role: User's role

        Returns:
            Dictionary of resource -> actions
        """
        permissions: dict[str, list[str]] = {}

        # Get base permissions for this role
        base_perms = self.BASE_PERMISSIONS.get(role, {})
        for resource, actions in base_perms.items():
            permissions.setdefault(resource, []).extend(actions)

        # Inherit permissions from parent roles
        parent_roles = self.ROLE_HIERARCHY.get(role, [])
        for parent_role in parent_roles:
            parent_perms = self.BASE_PERMISSIONS.get(parent_role, {})
            for resource, actions in parent_perms.items():
                permissions.setdefault(resource, []).extend(actions)

        # Remove duplicates
        for resource in permissions:
            permissions[resource] = list(set(permissions[resource]))

        return permissions

    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context,
    ) -> bool:
        """Check authorization with role hierarchy."""
        role = user.get("role", "guest")
        user_id = user.get("user_id", "unknown")

        # Get all permissions (including inherited)
        all_permissions = self.get_all_permissions(role)
        allowed_actions = all_permissions.get(resource, [])

        is_authorized = action in allowed_actions

        if not is_authorized:
            print(f"✗ Authorization denied: {user_id} ({role}) cannot {action} on {resource}")

        return is_authorized


class MultiRoleRBACBackend(AuthorizationBackend):
    """
    RBAC backend supporting multiple roles per user.

    Users can have multiple roles, and are authorized if ANY role
    grants the required permission.
    """

    PERMISSIONS = {
        "admin": {
            "graph": ["invoke", "stream", "read", "stop", "setup", "fix"],
            "checkpointer": ["read", "write", "delete"],
            "store": ["read", "write", "delete", "forget"],
        },
        "developer": {
            "graph": ["invoke", "stream", "read", "setup"],
            "checkpointer": ["read", "write"],
            "store": ["read", "write"],
        },
        "viewer": {"graph": ["read"], "checkpointer": ["read"], "store": ["read"]},
    }

    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context,
    ) -> bool:
        """
        Check if any of user's roles grant permission.

        User context should include 'roles' as a list.
        """
        user_id = user.get("user_id", "unknown")

        # Support both single role and multiple roles
        roles = user.get("roles", [])
        if not roles:
            single_role = user.get("role")
            if single_role:
                roles = [single_role]

        if not roles:
            print(f"✗ No roles found for user {user_id}")
            return False

        # Check if any role grants permission
        for role in roles:
            role_permissions = self.PERMISSIONS.get(role, {})
            allowed_actions = role_permissions.get(resource, [])

            if action in allowed_actions:
                print(f"✓ Authorization granted: {user_id} ({role}) can {action} on {resource}")
                return True

        print(f"✗ Authorization denied: {user_id} {roles} cannot {action} on {resource}")
        return False


"""
CONFIGURATION:

# agentflow.json
{
  "auth": "jwt",
  "authorization": {
    "path": "auth.rbac_backend:RBACAuthorizationBackend"
  },
  "agent": "graph.react:app"
}

# For hierarchical RBAC
{
  "authorization": {
    "path": "auth.rbac_backend:HierarchicalRBACBackend"
  }
}

# For multi-role RBAC
{
  "authorization": {
    "path": "auth.rbac_backend:MultiRoleRBACBackend"
  }
}
"""

"""
USER CONTEXT EXAMPLES:

# Single role
{
  "user_id": "user_123",
  "email": "john@example.com",
  "role": "developer"
}

# Multiple roles
{
  "user_id": "user_456",
  "email": "admin@example.com",
  "roles": ["admin", "developer"]
}

# JWT token payload
{
  "user_id": "user_789",
  "email": "viewer@example.com",
  "role": "viewer",
  "exp": 1735689600
}
"""

"""
TESTING EXAMPLES:

# tests/test_rbac_authorization.py
import pytest
from auth.rbac_backend import RBACAuthorizationBackend

@pytest.fixture
def rbac_backend():
    return RBACAuthorizationBackend()

@pytest.mark.asyncio
async def test_admin_full_access(rbac_backend):
    user = {"user_id": "admin1", "role": "admin"}
    
    # Admin can do everything
    assert await rbac_backend.authorize(user, "graph", "invoke")
    assert await rbac_backend.authorize(user, "graph", "stop")
    assert await rbac_backend.authorize(user, "checkpointer", "delete")

@pytest.mark.asyncio
async def test_developer_limited_access(rbac_backend):
    user = {"user_id": "dev1", "role": "developer"}
    
    # Developer can invoke but not stop
    assert await rbac_backend.authorize(user, "graph", "invoke")
    assert not await rbac_backend.authorize(user, "graph", "stop")

@pytest.mark.asyncio
async def test_viewer_read_only(rbac_backend):
    user = {"user_id": "viewer1", "role": "viewer"}
    
    # Viewer can only read
    assert await rbac_backend.authorize(user, "graph", "read")
    assert not await rbac_backend.authorize(user, "graph", "invoke")
    assert not await rbac_backend.authorize(user, "checkpointer", "write")

@pytest.mark.asyncio
async def test_guest_no_access(rbac_backend):
    user = {"user_id": "guest1", "role": "guest"}
    
    # Guest has no access
    assert not await rbac_backend.authorize(user, "graph", "read")
    assert not await rbac_backend.authorize(user, "graph", "invoke")
"""

"""
INTEGRATION WITH ENDPOINTS:

All AgentFlow endpoints automatically use the configured authorization backend.

# Example: Graph invocation endpoint
@router.post("/graph/invoke")
async def invoke_graph(
    user: dict = Depends(RequirePermission("graph", "invoke")),
    request: GraphRequest
):
    # User is authenticated and authorized
    # Role-based access control is enforced
    # Only admin and developer roles can reach this point
    pass

# Example: Checkpointer delete endpoint
@router.delete("/checkpointer/thread/{thread_id}")
async def delete_thread(
    thread_id: str,
    user: dict = Depends(RequirePermission("checkpointer", "delete"))
):
    # Only admin role can delete threads
    pass
"""

"""
CUSTOMIZATION:

# Add custom roles
PERMISSIONS["analyst"] = {
    "graph": ["read"],
    "checkpointer": ["read"],
    "store": ["read", "write"]
}

# Add custom resources
PERMISSIONS["admin"]["reports"] = ["read", "write", "delete"]

# Context-aware permissions
async def authorize(self, user, resource, action, resource_id=None, **context):
    # Check time-based restrictions
    if context.get("after_hours"):
        return user.get("role") == "admin"
    
    # Check IP-based restrictions
    if context.get("external_ip"):
        return action == "read"
    
    # Standard RBAC check
    return await super().authorize(user, resource, action, resource_id, **context)
"""
