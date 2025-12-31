# Security Guide - AgentFlow CLI

**Version:** 1.0  
**Last Updated:** December 31, 2025  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Threat Model](#threat-model)
3. [Authentication](#authentication)
4. [Authorization](#authorization)
5. [Production Deployment](#production-deployment)
6. [Security Configuration](#security-configuration)
7. [Best Practices](#best-practices)
8. [Monitoring & Incident Response](#monitoring--incident-response)
9. [Security Testing](#security-testing)
10. [Vulnerability Reporting](#vulnerability-reporting)

---

## Overview

AgentFlow CLI provides a secure framework for building agent-based applications. This document outlines the security architecture, best practices, and deployment guidelines.

### Security Features

- **Authentication System**: JWT and custom authentication backends
- **Authorization Framework**: Resource-based access control with extensible backends
- **Request Size Limiting**: DoS protection with configurable limits
- **Error Sanitization**: Production-safe error messages
- **Security Headers**: Configurable security headers middleware
- **Log Sanitization**: Automatic redaction of sensitive data
- **Configuration Validation**: Startup warnings for insecure configurations

### Shared Responsibility Model

**Framework Responsibilities:**
- Provide secure authentication/authorization hooks
- Sanitize logs and error messages
- Validate configurations
- Protect against common attacks (DoS, CSRF, etc.)

**Developer Responsibilities:**
- Implement authentication backends securely
- Define authorization policies
- Manage secrets properly
- Follow deployment best practices
- Keep dependencies updated

---

## Threat Model

### Assets

1. **User Data**: Authentication tokens, personal information
2. **Graph State**: Agent execution state and checkpoints
3. **API Keys**: Third-party service credentials
4. **Configuration**: Environment variables and secrets

### Threat Actors

1. **External Attackers**: Unauthorized access attempts
2. **Malicious Users**: Authenticated users attempting privilege escalation
3. **Insider Threats**: Compromised credentials or malicious developers
4. **Automated Attacks**: Bots, scrapers, DoS attacks

### Attack Vectors

#### 1. Authentication Bypass
**Risk:** Unauthorized access to protected resources  
**Mitigation:**
- Use strong JWT secrets (minimum 256 bits)
- Implement token expiration
- Validate tokens on every request
- Use HTTPS in production

#### 2. Authorization Violations
**Risk:** Privilege escalation, unauthorized resource access  
**Mitigation:**
- Implement authorization checks on all endpoints
- Use resource-based access control
- Validate user permissions before operations
- Log authorization failures

#### 3. Denial of Service (DoS)
**Risk:** Service unavailability, resource exhaustion  
**Mitigation:**
- Request size limits (default 10MB)
- Rate limiting (optional, developer-implemented)
- Timeout configurations
- Resource monitoring

#### 4. Information Disclosure
**Risk:** Exposure of sensitive data through errors/logs  
**Mitigation:**
- Error message sanitization in production
- Log sanitization for sensitive fields
- Secure configuration warnings
- Generic error responses

#### 5. Injection Attacks
**Risk:** SQL injection, code injection, path traversal  
**Mitigation:**
- Input validation (developer responsibility)
- Parameterized queries
- Path validation
- Content-Type validation

#### 6. Cross-Site Request Forgery (CSRF)
**Risk:** Unauthorized actions via forged requests  
**Mitigation:**
- CORS configuration
- SameSite cookies
- CSRF tokens (for web frontends)

---

## Authentication

### JWT Authentication (Built-in)

AgentFlow provides built-in JWT authentication with secure defaults.

#### Setup

**agentflow.json:**
```json
{
  "auth": "jwt"
}
```

**.env:**
```bash
# Required: Strong secret key (minimum 256 bits)
JWT_SECRET_KEY=your-super-secret-key-here-min-32-chars

# Optional: Algorithm (default: HS256)
JWT_ALGORITHM=HS256

# Optional: Token expiration (default: 30 minutes)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

#### Generating Secure Secret Keys

```bash
# Generate a secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Token Format

```json
{
  "user_id": "user_123456789",
  "email": "user@example.com",
  "exp": 1735689600
}
```

#### Using Tokens

```bash
# Include in Authorization header
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8000/graph/invoke
```

### Custom Authentication

For custom authentication logic, implement the `BaseAuth` interface.

**Example: API Key Authentication**

**auth/api_key.py:**
```python
from agentflow_cli import BaseAuth
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
import os

class APIKeyAuth(BaseAuth):
    """API Key authentication backend."""
    
    def __init__(self):
        # Load valid API keys from environment or database
        self.valid_keys = set(os.getenv("API_KEYS", "").split(","))
    
    async def authenticate(
        self, 
        credentials: HTTPAuthorizationCredentials, 
        response: Response
    ) -> dict[str, str]:
        """Validate API key and return user context."""
        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        api_key = credentials.credentials
        
        # Validate API key
        if api_key not in self.valid_keys:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Return user context
        # Note: In production, fetch from database
        return {
            "user_id": f"api_key_{api_key[:8]}",
            "auth_method": "api_key",
            "permissions": ["read", "write"]
        }
    
    def extract_user_id(self, user: dict[str, str]) -> str | None:
        """Extract user ID from user context."""
        return user.get("user_id")
```

**agentflow.json:**
```json
{
  "auth": {
    "method": "custom",
    "path": "auth.api_key:APIKeyAuth"
  }
}
```

**.env:**
```bash
API_KEYS=key1_abc123xyz,key2_def456uvw,key3_ghi789rst
```

### Security Best Practices - Authentication

1. **Use HTTPS**: Always use HTTPS in production to prevent token interception
2. **Strong Secrets**: Use cryptographically secure random keys (minimum 256 bits)
3. **Token Expiration**: Set reasonable expiration times (15-60 minutes)
4. **Refresh Tokens**: Implement refresh token rotation for long-lived sessions
5. **Rate Limiting**: Protect authentication endpoints from brute force
6. **Audit Logging**: Log all authentication attempts (success and failure)
7. **Secure Storage**: Never commit secrets to version control

---

## Authorization

AgentFlow provides a flexible authorization framework that allows you to implement resource-based access control.

### Authorization Flow

```
Request → Authentication → Authorization → Resource Access
```

1. **Authentication**: Validates identity (who are you?)
2. **Authorization**: Validates permissions (what can you do?)
3. **Resource Access**: Executes operation

### Built-in Authorization Backend

The `DefaultAuthorizationBackend` allows all authenticated users.

```python
# Default behavior: any authenticated user can access resources
async def authorize(self, user, resource, action, resource_id=None, **context):
    return bool(user.get("user_id"))
```

### Custom Authorization Backend

Implement custom authorization logic by extending `AuthorizationBackend`.

**Example: Role-Based Access Control**

**auth/rbac_backend.py:**
```python
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend
from typing import Any

class RBACAuthorizationBackend(AuthorizationBackend):
    """Role-based access control backend."""
    
    # Define permission matrix
    PERMISSIONS = {
        "admin": {
            "graph": ["invoke", "stream", "read", "stop", "setup", "fix"],
            "checkpointer": ["read", "write", "delete"],
            "store": ["read", "write", "delete", "forget"]
        },
        "developer": {
            "graph": ["invoke", "stream", "read"],
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
        """Check if user's role has permission for resource action."""
        
        # Extract user role
        role = user.get("role", "viewer")
        
        # Get permissions for role
        role_permissions = self.PERMISSIONS.get(role, {})
        
        # Check if resource action is permitted
        allowed_actions = role_permissions.get(resource, [])
        
        is_authorized = action in allowed_actions
        
        # Log authorization decision
        if not is_authorized:
            print(f"Authorization denied: {role} cannot {action} on {resource}")
        
        return is_authorized
```

**agentflow.json:**
```json
{
  "auth": "jwt",
  "authorization": {
    "path": "auth.rbac_backend:RBACAuthorizationBackend"
  }
}
```

**Example: Resource Ownership**

**auth/ownership_backend.py:**
```python
from agentflow_cli.src.app.core.auth.authorization import AuthorizationBackend
from typing import Any

class OwnershipAuthorizationBackend(AuthorizationBackend):
    """Resource ownership-based authorization."""
    
    def __init__(self, db_service=None):
        self.db = db_service  # Inject your database service
    
    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context
    ) -> bool:
        """Check if user owns the resource or has admin role."""
        
        user_id = user.get("user_id")
        role = user.get("role", "user")
        
        # Admins can access everything
        if role == "admin":
            return True
        
        # For read operations, allow authenticated users
        if action == "read":
            return True
        
        # For write/delete operations, check ownership
        if resource_id and self.db:
            owner_id = await self.db.get_resource_owner(resource, resource_id)
            return owner_id == user_id
        
        # Default: deny
        return False
```

### Using Authorization in Endpoints

Authorization is automatically enforced using the `RequirePermission` dependency:

```python
from agentflow_cli.src.app.core.auth.permissions import RequirePermission
from fastapi import Depends

@router.post("/graph/invoke")
async def invoke_graph(
    user: dict = Depends(RequirePermission("graph", "invoke")),
    # ... other parameters
):
    # user is authenticated and authorized
    # Proceed with graph invocation
    pass
```

### Security Best Practices - Authorization

1. **Deny by Default**: Deny access unless explicitly permitted
2. **Least Privilege**: Grant minimum necessary permissions
3. **Validate on Every Request**: Never cache authorization decisions
4. **Resource-Level Control**: Check permissions for specific resources
5. **Audit Authorization Failures**: Log all denied access attempts
6. **Separate Authentication and Authorization**: Keep concerns separate
7. **Test Authorization Logic**: Comprehensive unit tests for all scenarios

---

## Production Deployment

### Security Checklist

Before deploying to production, ensure:

#### Environment Configuration
- [ ] `MODE=production` is set
- [ ] `IS_DEBUG=false`
- [ ] `JWT_SECRET_KEY` is set to a strong random value (32+ chars)
- [ ] `ORIGINS` is set to specific domains (not `*`)
- [ ] `ALLOWED_HOST` is set to specific hosts (not `*`)
- [ ] `DOCS_PATH` and `REDOCS_PATH` are empty or removed
- [ ] All secrets are stored securely (not in version control)

#### Network Security
- [ ] HTTPS is enabled with valid SSL/TLS certificates
- [ ] Firewall rules restrict access to necessary ports only
- [ ] API is behind a reverse proxy (Nginx, Traefik, etc.)
- [ ] Rate limiting is configured
- [ ] DDoS protection is in place

#### Application Security
- [ ] Authentication is enabled
- [ ] Authorization backend is implemented
- [ ] Request size limits are configured
- [ ] Security headers are enabled
- [ ] Error messages are sanitized
- [ ] Logs are sanitized

#### Monitoring
- [ ] Logging is configured and centralized
- [ ] Metrics collection is enabled
- [ ] Alerting is configured for security events
- [ ] Regular security audits are scheduled

### Secure Environment Configuration

**Production .env:**
```bash
# Application Mode
MODE=production

# Security
IS_DEBUG=false
JWT_SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS - Specific domains only
ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Networking
ALLOWED_HOST=yourdomain.com,app.yourdomain.com
HOST=0.0.0.0
PORT=8000

# Disable API documentation in production
DOCS_PATH=
REDOCS_PATH=

# Request limits
MAX_REQUEST_SIZE=10485760  # 10MB

# Redis (if using)
REDIS_URL=redis://redis:6379/0

# Database (if using)
DATABASE_URL=postgresql://user:pass@db:5432/dbname

# Monitoring
LOG_LEVEL=INFO
SENTRY_DSN=<your-sentry-dsn>
```

### Docker Deployment

**Dockerfile (Production):**
```dockerfile
FROM python:3.11-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/ping')"

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "agentflow_cli.src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml (Production):**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODE=production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ORIGINS=${ORIGINS}
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env.production
    depends_on:
      - redis
    restart: unless-stopped
    # Security: Read-only root filesystem
    read_only: true
    tmpfs:
      - /tmp
    # Security: Drop capabilities
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 512M
  
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    # Security: Run as non-root
    user: "999:999"

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: unless-stopped

volumes:
  redis_data:
```

**nginx.conf (Security Headers):**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Security Configuration

### Configuration Warnings

AgentFlow validates your configuration on startup and warns about insecure settings:

```python
# Example startup warnings
⚠️  SECURITY WARNING: CORS ORIGINS='*' in production.
   Set ORIGINS to specific domains.

⚠️  SECURITY WARNING: DEBUG mode enabled in production!
   Set IS_DEBUG=false

⚠️  SECURITY WARNING: API docs enabled in production!
   Set DOCS_PATH and REDOCS_PATH to empty strings
```

### Request Size Limits

Configure maximum request size to prevent DoS attacks:

**.env:**
```bash
# Default: 10MB
MAX_REQUEST_SIZE=10485760

# For larger file uploads
MAX_REQUEST_SIZE=52428800  # 50MB

# For API-only (small payloads)
MAX_REQUEST_SIZE=1048576  # 1MB
```

Requests exceeding the limit receive a 413 error:
```json
{
  "error": {
    "code": "REQUEST_TOO_LARGE",
    "message": "Request body too large",
    "max_size_bytes": 10485760,
    "max_size_mb": 10.0
  }
}
```

### Error Message Sanitization

In production mode, error messages are sanitized to prevent information disclosure:

**Development Mode** (MODE=development):
```json
{
  "error": {
    "code": "GRAPH_EXECUTION_ERROR",
    "message": "Failed to execute node 'process_data': KeyError: 'missing_field' at line 42 in processor.py",
    "request_id": "req_123456789"
  }
}
```

**Production Mode** (MODE=production):
```json
{
  "error": {
    "code": "GRAPH_EXECUTION_ERROR",
    "message": "An error occurred executing the graph.",
    "request_id": "req_123456789"
  }
}
```

Detailed errors are always logged server-side for debugging.

### Log Sanitization

Sensitive data is automatically redacted from logs:

```python
# Before sanitization
logger.info(f"User authenticated: {user}")
# Output: User authenticated: {'user_id': '123', 'token': 'eyJhbGc...'}

# After sanitization
logger.info(f"User authenticated: {sanitize_for_logging(user)}")
# Output: User authenticated: {'user_id': '123', 'token': '***REDACTED***'}
```

Sensitive patterns include:
- `token`, `password`, `secret`, `key`, `credential`
- `authorization`, `api_key`, `access_token`, `refresh_token`
- JWT tokens (detected by pattern matching)

### Security Headers

AgentFlow automatically adds security headers to protect against common web vulnerabilities:

**Enabled by Default:**

**.env:**
```bash
# Security headers configuration (all optional, shown with defaults)
SECURITY_HEADERS_ENABLED=true

# HSTS (HTTP Strict Transport Security)
HSTS_ENABLED=true
HSTS_MAX_AGE=31536000  # 1 year in seconds
HSTS_INCLUDE_SUBDOMAINS=true
HSTS_PRELOAD=false

# Other security headers
FRAME_OPTIONS=DENY  # Options: DENY, SAMEORIGIN, ALLOW-FROM <uri>
CONTENT_TYPE_OPTIONS=nosniff
XSS_PROTECTION=1; mode=block
REFERRER_POLICY=strict-origin-when-cross-origin

# Advanced policies (uses sensible defaults if not specified)
PERMISSIONS_POLICY=  # Optional: geolocation=(), microphone=(), camera=()
CSP_POLICY=  # Optional: default-src 'self'; ...
```

**Headers Added:**

1. **X-Content-Type-Options: nosniff**
   - Prevents MIME-type sniffing
   - Protects against drive-by download attacks

2. **X-Frame-Options: DENY**
   - Prevents clickjacking attacks
   - Use SAMEORIGIN to allow framing from same origin

3. **X-XSS-Protection: 1; mode=block**
   - Enables browser XSS filtering (legacy browsers)
   - Modern browsers rely on CSP

4. **Strict-Transport-Security** (HTTPS only)
   - Enforces HTTPS for all future requests
   - Only added when request is over HTTPS
   - Default: `max-age=31536000; includeSubDomains`

5. **Content-Security-Policy**
   - Controls which resources can load
   - Default policy:
     ```
     default-src 'self';
     script-src 'self' 'unsafe-inline';
     style-src 'self' 'unsafe-inline';
     img-src 'self' data: https:;
     font-src 'self' data:;
     connect-src 'self';
     frame-ancestors 'none';
     base-uri 'self';
     form-action 'self'
     ```

6. **Referrer-Policy: strict-origin-when-cross-origin**
   - Controls referrer information sent with requests
   - Balances privacy and functionality

7. **Permissions-Policy**
   - Controls browser features (geolocation, camera, etc.)
   - Default: Denies most permissions

**Custom Configuration Example:**

```bash
# .env - Custom CSP for application with external resources
CSP_POLICY=default-src 'self'; script-src 'self' https://cdn.example.com; img-src 'self' https:; connect-src 'self' https://api.example.com

# Custom Permissions-Policy
PERMISSIONS_POLICY=geolocation=(self), camera=(), microphone=()

# Allow framing from same origin
FRAME_OPTIONS=SAMEORIGIN

# Enable HSTS preload (requires HTTPS and specific configuration)
HSTS_PRELOAD=true
```

**Disabling Security Headers:**

```bash
# Disable all security headers (not recommended)
SECURITY_HEADERS_ENABLED=false

# Disable only HSTS (e.g., for local development)
HSTS_ENABLED=false
```

**Testing Security Headers:**

```bash
# Test with curl
curl -I https://yourdomain.com/ping

# Expected headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# Content-Security-Policy: default-src 'self'; ...
# Referrer-Policy: strict-origin-when-cross-origin
# Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## Best Practices

### Secrets Management

**❌ Don't:**
```python
# Never hardcode secrets
JWT_SECRET_KEY = "my-secret-key"

# Never commit .env files
git add .env
```

**✅ Do:**
```python
# Use environment variables
import os
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

# Use secret management services
# - AWS Secrets Manager
# - HashiCorp Vault
# - Google Secret Manager
# - Azure Key Vault

# Generate strong secrets
import secrets
secret = secrets.token_urlsafe(32)
```

### Input Validation

**❌ Don't:**
```python
# Never trust user input
sql = f"SELECT * FROM users WHERE id = {user_input}"

# Never execute arbitrary code
eval(user_input)
```

**✅ Do:**
```python
from pydantic import BaseModel, validator

class GraphRequest(BaseModel):
    input: dict
    thread_id: str | None = None
    
    @validator('thread_id')
    def validate_thread_id(cls, v):
        if v and not v.isalnum():
            raise ValueError("Invalid thread_id format")
        return v

# Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = ?", (user_input,))
```

### Dependency Management

**✅ Best Practices:**
```bash
# Pin dependencies
pip install -r requirements.txt

# Regular updates
pip list --outdated

# Security audits
pip-audit

# Use virtual environments
python -m venv venv
source venv/bin/activate
```

### Access Control

**✅ Principle of Least Privilege:**
```python
# Grant minimum necessary permissions
PERMISSIONS = {
    "viewer": {
        "graph": ["read"],
        "checkpointer": ["read"],
        "store": ["read"]
    },
    "editor": {
        "graph": ["read", "invoke"],
        "checkpointer": ["read", "write"],
        "store": ["read", "write"]
    }
}
```

### Logging and Monitoring

**✅ Security Event Logging:**
```python
# Log authentication events
logger.info(f"Authentication successful: {user_id}")
logger.warning(f"Authentication failed: {ip_address}")

# Log authorization failures
logger.warning(f"Authorization denied: {user_id} tried {action} on {resource}")

# Log security events
logger.error(f"Request size limit exceeded: {content_length} bytes")
logger.error(f"Suspicious path detected: {path}")
```

---

## Monitoring & Incident Response

### Security Metrics

Monitor these key security metrics:

1. **Authentication Metrics**
   - Failed authentication attempts
   - Successful authentications
   - Token expirations
   - Unusual login patterns

2. **Authorization Metrics**
   - Authorization failures by user
   - Authorization failures by resource
   - Privilege escalation attempts

3. **Request Metrics**
   - Request rate by endpoint
   - Rejected requests (size limit, rate limit)
   - Error rates
   - Response times

4. **Application Metrics**
   - Unhealthy dependencies
   - Configuration warnings
   - Exception rates
   - Resource usage

### Logging Configuration

**Centralized Logging:**
```python
# Use structured logging
import structlog

logger = structlog.get_logger()
logger.info(
    "authentication_attempt",
    user_id=user_id,
    ip_address=ip,
    success=True,
    timestamp=datetime.utcnow().isoformat()
)
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- Datadog
- CloudWatch (AWS)
- Stackdriver (GCP)

### Incident Response

**Security Incident Checklist:**

1. **Detect**: Monitor for security events
2. **Assess**: Determine severity and impact
3. **Contain**: Isolate affected systems
4. **Eradicate**: Remove threat
5. **Recover**: Restore normal operations
6. **Review**: Post-incident analysis

**Emergency Response:**
```bash
# Rotate compromised secrets
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Restart services with new secrets
docker-compose restart api

# Revoke compromised tokens (implement token blacklist)
redis-cli DEL "token:blacklist:<token_jti>"

# Review access logs
grep "401\|403" /var/log/nginx/access.log

# Block malicious IPs
iptables -A INPUT -s <malicious_ip> -j DROP
```

---

## Security Testing

### Unit Testing

**Test Authentication:**
```python
import pytest
from fastapi.testclient import TestClient

def test_authentication_required(client: TestClient):
    """Test that endpoints require authentication."""
    response = client.post("/graph/invoke")
    assert response.status_code == 401

def test_valid_jwt_token(client: TestClient, valid_token: str):
    """Test that valid JWT tokens are accepted."""
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.post("/graph/invoke", headers=headers)
    assert response.status_code != 401
```

**Test Authorization:**
```python
def test_authorization_denied(client: TestClient, viewer_token: str):
    """Test that viewers cannot invoke graphs."""
    headers = {"Authorization": f"Bearer {viewer_token}"}
    response = client.post("/graph/invoke", headers=headers)
    assert response.status_code == 403

def test_authorization_granted(client: TestClient, admin_token: str):
    """Test that admins can invoke graphs."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/graph/invoke", headers=headers)
    assert response.status_code != 403
```

### Integration Testing

**Test Security Headers:**
```python
def test_security_headers(client: TestClient):
    """Test that security headers are present."""
    response = client.get("/ping")
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
```

**Test Rate Limiting:**
```python
def test_rate_limiting(client: TestClient):
    """Test that rate limiting works."""
    for _ in range(100):
        response = client.get("/ping")
    assert response.status_code == 429  # Too Many Requests
```

### Penetration Testing

**Recommended Tools:**
- OWASP ZAP
- Burp Suite
- Nikto
- SQLMap
- Nmap

**Test Scenarios:**
- Authentication bypass attempts
- SQL injection
- Cross-site scripting (XSS)
- Path traversal
- DoS attacks
- Credential brute forcing

---

## Vulnerability Reporting

### Responsible Disclosure

If you discover a security vulnerability in AgentFlow CLI:

1. **Do Not** disclose publicly until patched
2. **Email**: security@10xhub.com
3. **Include**:
   - Vulnerability description
   - Steps to reproduce
   - Impact assessment
   - Suggested fix (if known)

### Response Timeline

- **24 hours**: Initial response
- **7 days**: Severity assessment
- **30 days**: Patch development
- **60 days**: Public disclosure (coordinated)

### Security Updates

Subscribe to security announcements:
- GitHub Security Advisories
- Release Notes
- Security Mailing List

---

## Additional Resources

### Documentation
- [Authentication Guide](./docs/authentication.md)
- [Deployment Guide](./docs/deployment.md)
- [Configuration Guide](./docs/configuration.md)

### Security Standards
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

### Tools
- [pip-audit](https://github.com/pypa/pip-audit) - Dependency vulnerability scanner
- [Bandit](https://github.com/PyCQA/bandit) - Python security linter
- [Safety](https://github.com/pyupio/safety) - Dependency security checker

---

## Changelog

### Version 1.0 (December 31, 2025)
- Initial security guide
- Authentication and authorization documentation
- Production deployment checklist
- Security best practices
- Monitoring and incident response guidelines

---

**Questions or Concerns?**  
Contact: security@10xhub.com
