# Authentication Guide

This guide covers implementing authentication in your AgentFlow application using JWT or custom authentication backends.

## Table of Contents

- [Overview](#overview)
- [Security Considerations](#security-considerations)
- [No Authentication](#no-authentication)
- [JWT Authentication](#jwt-authentication)
- [Custom Authentication](#custom-authentication)
- [Authorization](#authorization)
- [BaseAuth Interface](#baseauth-interface)
- [Best Practices](#best-practices)
- [Examples](#examples)

---

## Overview

AgentFlow supports three authentication modes:

1. **No Authentication** - For development or internal APIs
2. **JWT Authentication** - Built-in JWT token validation
3. **Custom Authentication** - Implement your own auth logic

Authentication is configured in `agentflow.json`:

```json
{
  "auth": null | "jwt" | {
    "method": "custom",
    "path": "module:class"
  }
}
```

---

## Security Considerations

### Authentication vs Authorization

**Authentication** answers: *"Who are you?"*
- Verifies user identity
- Validates credentials (tokens, API keys, etc.)
- Returns user context

**Authorization** answers: *"What can you do?"*
- Controls access to resources
- Enforces permissions
- Checks user roles and privileges

AgentFlow provides both:
- **Authentication**: Via this authentication system
- **Authorization**: Via the [Authorization Framework](../SECURITY.md#authorization)

See [SECURITY.md](../SECURITY.md) for comprehensive security documentation.

### Security Requirements by Environment

**Development:**
- Can use `auth: null` for convenience
- Use simple secrets for testing
- API docs can be enabled

**Staging:**
- Should use JWT or custom authentication
- Use environment-specific secrets
- Test security configurations

**Production:**
- **MUST** use JWT or custom authentication
- **MUST** use strong, random secrets (32+ characters)
- **MUST** use HTTPS
- **MUST** disable API documentation
- **MUST** implement authorization
- **MUST** enable request size limits
- **MUST** configure specific CORS origins

### Security Checklist

Before deploying to production:

- [ ] Authentication enabled (`auth: "jwt"` or custom)
- [ ] Strong JWT secret configured (generate with `secrets.token_urlsafe(32)`)
- [ ] HTTPS enabled with valid SSL/TLS certificates
- [ ] Authorization backend implemented
- [ ] CORS configured with specific domains (not `*`)
- [ ] API documentation disabled (`DOCS_PATH=` and `REDOCS_PATH=`)
- [ ] Debug mode disabled (`IS_DEBUG=false`)
- [ ] Request size limits configured (`MAX_REQUEST_SIZE=10485760`)
- [ ] Rate limiting implemented
- [ ] Security headers configured
- [ ] Logs sanitized for sensitive data

See the [Production Deployment Checklist](../SECURITY.md#production-deployment) for complete details.

---

## No Authentication

### Configuration

**agentflow.json:**
```json
{
  "agent": "graph.react:app",
  "auth": null
}
```

### Usage

All API endpoints will be accessible without authentication.

```bash
# No auth header required
curl http://localhost:8000/ping
curl -X POST http://localhost:8000/threads
```

### When to Use

- ✅ Development and testing
- ✅ Internal APIs behind a firewall
- ✅ APIs with alternative security (API Gateway, VPN)
- ❌ Public-facing production APIs
- ❌ APIs handling sensitive data

---

## JWT Authentication

### Configuration

**Step 1: Configure agentflow.json**

```json
{
  "agent": "graph.react:app",
  "auth": "jwt"
}
```

**Step 2: Set Environment Variables**

**.env:**
```bash
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
```

### Supported Algorithms

| Algorithm | Type | Description |
|-----------|------|-------------|
| HS256 | HMAC | SHA-256 (recommended for single server) |
| HS384 | HMAC | SHA-384 |
| HS512 | HMAC | SHA-512 |
| RS256 | RSA | SHA-256 (for distributed systems) |
| RS384 | RSA | SHA-384 |
| RS512 | RSA | SHA-512 |
| ES256 | ECDSA | SHA-256 |
| ES384 | ECDSA | SHA-384 |
| ES512 | ECDSA | SHA-512 |

### Generating Secrets

**For HS256 (symmetric):**
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

**For RS256 (asymmetric):**
```bash
# Generate private key
openssl genrsa -out private.pem 2048

# Generate public key
openssl rsa -in private.pem -outform PEM -pubout -out public.pem

# Use private key content as JWT_SECRET_KEY
cat private.pem
```

### Creating JWT Tokens

**Python example:**
```python
import jwt
from datetime import datetime, timedelta

def create_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        "your-secret-key",
        algorithm="HS256"
    )
    
    return token

# Usage
token = create_token("user123", "john_doe")
print(f"Token: {token}")
```

**Node.js example:**
```javascript
const jwt = require('jsonwebtoken');

function createToken(userId, username) {
    const payload = {
        user_id: userId,
        username: username,
        exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60), // 24 hours
        iat: Math.floor(Date.now() / 1000)
    };
    
    return jwt.sign(payload, 'your-secret-key', { algorithm: 'HS256' });
}

const token = createToken('user123', 'john_doe');
console.log(`Token: ${token}`);
```

### Using JWT Tokens

**With curl:**
```bash
# Create a thread
curl -X POST http://localhost:8000/threads \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"

# Send a message
curl -X POST http://localhost:8000/threads/abc123/messages \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello"}'
```

**With Python requests:**
```python
import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Create thread
response = requests.post(
    "http://localhost:8000/threads",
    headers=headers
)

thread_id = response.json()["thread_id"]

# Send message
response = requests.post(
    f"http://localhost:8000/threads/{thread_id}/messages",
    headers=headers,
    json={"content": "Hello, AI!"}
)

print(response.json())
```

**With JavaScript fetch:**
```javascript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const headers = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
};

// Create thread
fetch("http://localhost:8000/threads", {
    method: "POST",
    headers: headers
})
.then(res => res.json())
.then(data => {
    const threadId = data.thread_id;
    
    // Send message
    return fetch(`http://localhost:8000/threads/${threadId}/messages`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ content: "Hello, AI!" })
    });
})
.then(res => res.json())
.then(data => console.log(data));
```

### JWT Token Structure

A JWT consists of three parts: Header, Payload, and Signature.

**Header:**
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload (claims):**
```json
{
  "user_id": "user123",
  "username": "john_doe",
  "email": "john@example.com",
  "roles": ["user", "admin"],
  "exp": 1735689600,  // Expiration time
  "iat": 1735603200   // Issued at
}
```

**Signature:**
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret
)
```

### Token Validation

The JWT middleware automatically validates:
- ✅ Token signature
- ✅ Token expiration (`exp` claim)
- ✅ Token format

### Error Responses

**Missing token:**
```json
{
  "detail": "Not authenticated"
}
```
Status: 401 Unauthorized

**Invalid token:**
```json
{
  "detail": "Could not validate credentials"
}
```
Status: 401 Unauthorized

**Expired token:**
```json
{
  "detail": "Token has expired"
}
```
Status: 401 Unauthorized

---

## Custom Authentication

### Overview

Implement custom authentication for:
- OAuth 2.0 / OpenID Connect
- API keys
- Firebase Authentication
- Auth0
- Custom database authentication
- Multi-factor authentication

### Configuration

**agentflow.json:**
```json
{
  "agent": "graph.react:app",
  "auth": {
    "method": "custom",
    "path": "auth.custom:MyAuthBackend"
  }
}
```

### Implementation

**auth/custom.py:**
```python
from agentflow_cli import BaseAuth
from fastapi import Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from typing import Any

class MyAuthBackend(BaseAuth):
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict[str, Any] | None:
        """
        Authenticate user based on credentials.
        
        Args:
            res: FastAPI Response object (for setting cookies, headers)
            credential: HTTPAuthorizationCredentials with token
            
        Returns:
            dict with user info including 'user_id', or raises HTTPException
        """
        token = credential.credentials
        
        # Your authentication logic here
        user = self.verify_token(token)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )
        
        # Return user information
        # This will be merged with the graph config
        return {
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"]
        }
    
    def verify_token(self, token: str) -> dict | None:
        """Implement your token verification logic."""
        # Example: Query database, call external API, etc.
        pass
```

---

## Authorization

### Overview

After authentication establishes *who* the user is, authorization determines *what* they can do. AgentFlow provides a flexible authorization framework.

### Authorization Flow

```
Request → Authentication → Authorization → Resource Access
           (Who are you?)   (What can you do?)
```

All AgentFlow endpoints automatically enforce authorization using the `RequirePermission` dependency:

```python
from agentflow_cli.src.app.core.auth.permissions import RequirePermission
from fastapi import Depends

@router.post("/graph/invoke")
async def invoke_graph(
    user: dict = Depends(RequirePermission("graph", "invoke")),
    request: GraphRequest
):
    # User is authenticated AND authorized
    # Can proceed with graph invocation
    pass
```

### Implementing Authorization

**Step 1: Create Authorization Backend**

```python
# auth/rbac_backend.py
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend
from typing import Any

class RBACAuthorizationBackend(AuthorizationBackend):
    """Role-Based Access Control authorization."""
    
    PERMISSIONS = {
        "admin": {
            "graph": ["invoke", "stream", "read", "stop", "setup", "fix"],
            "checkpointer": ["read", "write", "delete"],
            "store": ["read", "write", "delete", "forget"]
        },
        "developer": {
            "graph": ["invoke", "stream", "read", "setup"],
            "checkpointer": ["read", "write"],
            "store": ["read", "write"]
        },
        "viewer": {
            "graph": ["read"],
            "checkpointer": ["read"],
            "store": ["read"]
        }
    }
    
    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context
    ) -> bool:
        """Check if user's role permits the action."""
        role = user.get("role", "viewer")
        role_permissions = self.PERMISSIONS.get(role, {})
        allowed_actions = role_permissions.get(resource, [])
        return action in allowed_actions
```

**Step 2: Configure agentflow.json**

```json
{
  "auth": "jwt",
  "authorization": {
    "path": "auth.rbac_backend:RBACAuthorizationBackend"
  },
  "agent": "graph.react:app"
}
```

**Step 3: Include Role in User Context**

Ensure your authentication returns user role:

```python
# JWT payload
{
  "user_id": "user_123",
  "email": "user@example.com",
  "role": "developer",  # Include role for authorization
  "exp": 1735689600
}
```

### Authorization Examples

See [examples/security/](../examples/security/) for complete implementations:
- **RBAC** - Role-Based Access Control
- **Ownership** - Resource ownership-based authorization
- **ABAC** - Attribute-Based Access Control

### Resources and Actions

AgentFlow defines these resources and actions:

**Graph Resource:**
- `invoke` - Execute graph
- `stream` - Stream graph execution
- `read` - View graph details and state
- `stop` - Stop running graph
- `setup` - Configure graph
- `fix` - Fix graph errors

**Checkpointer Resource:**
- `read` - View state, messages, threads
- `write` - Update state, add messages
- `delete` - Delete threads, messages, state

**Store Resource:**
- `read` - Search and view memories
- `write` - Create and update memories
- `delete` - Delete memories
- `forget` - Permanently forget memories

### Authorization Best Practices

1. **Deny by Default** - Only grant explicit permissions
2. **Least Privilege** - Grant minimum necessary access
3. **Validate Every Request** - Never cache authorization decisions
4. **Resource-Level Control** - Check permissions for specific resources
5. **Audit Failures** - Log all authorization denials
6. **Separate Concerns** - Keep authentication and authorization logic separate

For complete authorization documentation, see [SECURITY.md - Authorization](../SECURITY.md#authorization).

---

## BaseAuth Interface

### Abstract Method

```python
from abc import ABC, abstractmethod
from typing import Any
from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials

class BaseAuth(ABC):
    @abstractmethod
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict[str, Any] | None:
        """
        Authenticate the user based on credentials.
        
        Returns:
            - Empty dict {} if no authentication required
            - Dict with user info if authentication successful
            - Raises HTTPException if authentication fails
            
        The returned dict should contain at least:
            - user_id: Unique user identifier
            
        Optional fields:
            - username: User's username
            - email: User's email
            - roles: List of user roles
            - Any other user-specific data
            
        These fields will be merged with the graph config,
        making them available throughout your agent graph.
        """
        raise NotImplementedError
```

### Return Values

**No authentication required:**
```python
return {}
```

**Authentication successful:**
```python
return {
    "user_id": "user123",
    "username": "john_doe",
    "email": "john@example.com",
    "roles": ["user", "premium"],
    "subscription": "pro"
}
```

**Authentication failed:**
```python
from fastapi import HTTPException

raise HTTPException(
    status_code=401,
    detail="Invalid token"
)
```

---

## Best Practices

### Security

1. **Use strong secrets:**
   ```bash
   # Generate a secure secret
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Never commit secrets:**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo ".env.*" >> .gitignore
   echo "!.env.example" >> .gitignore
   ```

3. **Use environment-specific secrets:**
   ```bash
   # Development
   JWT_SECRET_KEY=dev-secret-key
   
   # Production (different secret!)
   JWT_SECRET_KEY=prod-super-secure-key-87y23h9823h
   ```

4. **Rotate secrets regularly:**
   ```python
   # Support multiple keys for rotation
   JWT_SECRET_KEYS = [
       "new-key",  # Try this first
       "old-key"   # Fallback for old tokens
   ]
   ```

5. **Use HTTPS in production:**
   - JWT tokens should only be transmitted over HTTPS
   - Configure SSL/TLS on your server or load balancer

### Token Management

1. **Set appropriate expiration:**
   ```python
   # Short-lived for sensitive operations
   exp = datetime.utcnow() + timedelta(hours=1)
   
   # Longer for regular use
   exp = datetime.utcnow() + timedelta(days=7)
   ```

2. **Include required claims:**
   ```python
   payload = {
       "user_id": user_id,      # Required
       "exp": expiration,        # Required
       "iat": issued_at,         # Recommended
       "jti": token_id,          # For revocation
       "aud": "agentflow-api",   # Audience
       "iss": "auth-service"     # Issuer
   }
   ```

3. **Implement token refresh:**
   ```python
   # Issue refresh token separately
   access_token = create_token(user_id, expires_in=timedelta(hours=1))
   refresh_token = create_refresh_token(user_id, expires_in=timedelta(days=30))
   ```

4. **Validate all claims:**
   ```python
   # Check expiration
   if payload["exp"] < time.time():
       raise TokenExpired
   
   # Check audience
   if payload["aud"] != "agentflow-api":
       raise InvalidAudience
   ```

### Error Handling

1. **Provide clear error messages:**
   ```python
   if not token:
       raise HTTPException(401, "Authorization header missing")
   
   if token_expired:
       raise HTTPException(401, "Token has expired")
   
   if invalid_signature:
       raise HTTPException(401, "Invalid token signature")
   ```

2. **Log authentication failures:**
   ```python
   logger.warning(
       f"Failed authentication attempt from {request.client.host}"
   )
   ```

3. **Rate limit authentication attempts:**
   ```python
   # Use Redis or similar
   attempts = redis.incr(f"auth_attempts:{ip}")
   if attempts > 10:
       raise HTTPException(429, "Too many attempts")
   ```

---

## Examples

### Firebase Authentication

```python
# auth/firebase.py
from agentflow_cli import BaseAuth
from fastapi import Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)

class FirebaseAuth(BaseAuth):
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict:
        try:
            # Verify Firebase ID token
            decoded_token = auth.verify_id_token(credential.credentials)
            uid = decoded_token['uid']
            
            return {
                "user_id": uid,
                "email": decoded_token.get('email'),
                "email_verified": decoded_token.get('email_verified'),
                "name": decoded_token.get('name')
            }
        except Exception as e:
            raise HTTPException(401, f"Invalid Firebase token: {e}")
```

**agentflow.json:**
```json
{
  "auth": {
    "method": "custom",
    "path": "auth.firebase:FirebaseAuth"
  }
}
```

### API Key Authentication

```python
# auth/api_key.py
from agentflow_cli import BaseAuth
from fastapi import Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import hashlib

class APIKeyAuth(BaseAuth):
    def __init__(self):
        # In production, load from database
        self.api_keys = {
            "hashed_key_1": {
                "user_id": "user1",
                "name": "Service Account 1",
                "permissions": ["read", "write"]
            },
            "hashed_key_2": {
                "user_id": "user2",
                "name": "Service Account 2",
                "permissions": ["read"]
            }
        }
    
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict:
        # Hash the provided API key
        api_key = credential.credentials
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Look up in database
        user_data = self.api_keys.get(key_hash)
        
        if not user_data:
            raise HTTPException(401, "Invalid API key")
        
        return {
            "user_id": user_data["user_id"],
            "name": user_data["name"],
            "permissions": user_data["permissions"]
        }
```

### OAuth 2.0 Authentication

```python
# auth/oauth.py
from agentflow_cli import BaseAuth
from fastapi import Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import requests

class OAuth2Auth(BaseAuth):
    def __init__(self):
        self.oauth_server = "https://oauth.example.com"
    
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict:
        # Verify token with OAuth server
        response = requests.get(
            f"{self.oauth_server}/userinfo",
            headers={"Authorization": f"Bearer {credential.credentials}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(401, "Invalid OAuth token")
        
        user_info = response.json()
        
        return {
            "user_id": user_info["sub"],
            "email": user_info["email"],
            "name": user_info["name"],
            "picture": user_info.get("picture")
        }
```

### Database Authentication

```python
# auth/database.py
from agentflow_cli import BaseAuth
from fastapi import Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

class DatabaseAuth(BaseAuth):
    def __init__(self):
        self.db = self.get_db_connection()
        self.secret_key = "your-secret-key"
    
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict:
        try:
            # Decode JWT
            payload = jwt.decode(
                credential.credentials,
                self.secret_key,
                algorithms=["HS256"]
            )
            
            user_id = payload["user_id"]
            
            # Query database
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user or not user.is_active:
                raise HTTPException(401, "User not found or inactive")
            
            return {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "roles": [role.name for role in user.roles],
                "permissions": user.get_permissions()
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
    
    def get_db_connection(self) -> Session:
        # Implement your database connection
        pass
```

### Multi-Factor Authentication

```python
# auth/mfa.py
from agentflow_cli import BaseAuth
from fastapi import Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import pyotp

class MFAAuth(BaseAuth):
    def authenticate(
        self,
        res: Response,
        credential: HTTPAuthorizationCredentials
    ) -> dict:
        # Token format: "jwt_token:mfa_code"
        try:
            jwt_token, mfa_code = credential.credentials.split(":")
        except ValueError:
            raise HTTPException(401, "Invalid token format. Expected: jwt:mfa_code")
        
        # Verify JWT
        user_data = self.verify_jwt(jwt_token)
        
        # Verify MFA code
        totp = pyotp.TOTP(user_data["mfa_secret"])
        if not totp.verify(mfa_code):
            raise HTTPException(401, "Invalid MFA code")
        
        return {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "mfa_verified": True
        }
    
    def verify_jwt(self, token: str) -> dict:
        # Implement JWT verification
        pass
```

---

## Testing Authentication

### Testing with curl

```bash
# No auth
curl http://localhost:8000/ping

# JWT auth
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/threads

# API key
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/threads
```

### Testing with pytest

```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
import jwt
from datetime import datetime, timedelta

client = TestClient(app)

def create_test_token(user_id="test_user"):
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")

def test_no_auth_fails():
    response = client.post("/threads")
    assert response.status_code == 401

def test_invalid_token_fails():
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.post("/threads", headers=headers)
    assert response.status_code == 401

def test_valid_token_succeeds():
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/threads", headers=headers)
    assert response.status_code == 200

def test_expired_token_fails():
    payload = {
        "user_id": "test_user",
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired
    }
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/threads", headers=headers)
    assert response.status_code == 401
```

---

## Additional Resources

- [JWT.io](https://jwt.io/) - JWT debugger and documentation
- [Configuration Guide](./configuration.md) - Complete configuration reference
- [Deployment Guide](./deployment.md) - Production deployment strategies
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) - FastAPI security documentation
