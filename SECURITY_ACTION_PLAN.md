# Security Action Plan - AgentFlow CLI

**Created:** December 31, 2024  
**Based on:** SECURITY_REVIEW.md  
**Status:** Planning  
**Timeline:** 4-6 weeks for P0-P1, ongoing for P2-P3

---

## Overview

This action plan addresses the framework-level security improvements identified in the security review. Items are prioritized based on impact and effort.

### Priority Levels

- **P0 (Critical):** Must be done before next release (1-2 weeks)
- **P1 (High):** Should be done soon (2-4 weeks)
- **P2 (Medium):** Nice to have (1-2 months)
- **P3 (Low):** Long-term improvements (3+ months)

---

## P0: Critical - Framework Security (Week 1-2)

### Task 1.1: Add Authorization Hooks System

**Priority:** P0  
**Effort:** 2-3 days  
**Assignee:** Backend Team

**Description:**
Create an authorization backend interface that developers can implement to add resource-level access control.

**Implementation Steps:**

1. **Create Authorization Backend Interface**
   - File: `agentflow_cli/src/app/core/auth/authorization.py`
   - Create abstract `AuthorizationBackend` class
   - Add `authorize()` method with resource, action, user parameters
   - Create `DefaultAuthorizationBackend` implementation

2. **Update Dependency Injection**
   - File: `agentflow_cli/src/app/loader.py`
   - Add authorization backend loading logic
   - Bind to InjectQ container
   - Support optional authorization config

3. **Update API Endpoints**
   - Files: `agentflow_cli/src/app/routers/graph/router.py`
   - Files: `agentflow_cli/src/app/routers/checkpointer/router.py`
   - Files: `agentflow_cli/src/app/routers/store/router.py`
   - Add authorization checks before operations
   - Inject `AuthorizationBackend` via InjectAPI
   - Call `authorize()` with appropriate parameters

4. **Update Configuration**
   - File: `agentflow_cli/src/app/core/config/graph_config.py`
   - Add `authorization_path` property
   - Support authorization config in `agentflow.json`

**Acceptance Criteria:**
- [x] `AuthorizationBackend` abstract class created
- [x] Default implementation allows all authenticated users
- [x] All resource endpoints check authorization
- [x] Configuration supports authorization path
- [x] Documentation includes authorization example
- [x] Unit tests for authorization logic

**Example Code:**
```python
# agentflow_cli/src/app/core/auth/authorization.py
from abc import ABC, abstractmethod
from typing import Any

class AuthorizationBackend(ABC):
    @abstractmethod
    async def authorize(
        self,
        user: dict[str, Any],
        resource: str,
        action: str,
        resource_id: str | None = None,
        **context
    ) -> bool:
        """Check if user can perform action on resource."""
        pass

class DefaultAuthorizationBackend(AuthorizationBackend):
    async def authorize(self, user, resource, action, resource_id=None, **context):
        return bool(user.get("user_id"))
```

---

### Task 1.2: Add Log Sanitization

**Priority:** P0  
**Effort:** 1 day  
**Assignee:** Backend Team

**Description:**
Prevent sensitive data (tokens, passwords, etc.) from being logged at any log level.

**Implementation Steps:**

1. **Create Sanitization Utility**
   - File: `agentflow_cli/src/app/core/utils/log_sanitizer.py` (new)
   - Implement recursive sanitization function
   - Define sensitive field patterns
   - Handle dicts, lists, strings

2. **Update Logger Configuration**
   - File: `agentflow_cli/src/app/core/config/setup_logs.py`
   - Create custom log formatter with sanitization
   - Apply to all handlers

3. **Update Existing Log Calls**
   - Files: All routers and services
   - Replace direct user dict logging with sanitized version
   - Update: `logger.debug(f"User: {user}")` → `logger.debug(f"User: {sanitize_for_logging(user)}")`

**Files to Update:**
- `agentflow_cli/src/app/routers/graph/router.py`
- `agentflow_cli/src/app/routers/checkpointer/router.py`
- `agentflow_cli/src/app/routers/store/router.py`
- `agentflow_cli/src/app/routers/graph/services/graph_service.py`
- `agentflow_cli/src/app/routers/checkpointer/services/checkpointer_service.py`
- `agentflow_cli/src/app/routers/store/services/store_service.py`

**Acceptance Criteria:**
- [x] Sanitization utility created and tested
- [x] All user dict logging uses sanitization
- [x] JWT tokens are detected and redacted
- [x] Sensitive field patterns are comprehensive
- [x] Unit tests verify sanitization
- [x] Performance impact is minimal

**Example Code:**
```python
# agentflow_cli/src/app/core/utils/log_sanitizer.py
import re
from typing import Any

SENSITIVE_PATTERNS = {
    'token', 'password', 'secret', 'key', 'credential',
    'authorization', 'api_key', 'access_token', 'refresh_token'
}

JWT_PATTERN = re.compile(r'^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$')

def sanitize_for_logging(data: Any) -> Any:
    """Recursively sanitize sensitive data."""
    if isinstance(data, dict):
        return {
            k: '***REDACTED***' if any(p in k.lower() for p in SENSITIVE_PATTERNS) 
            else sanitize_for_logging(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_for_logging(item) for item in data]
    elif isinstance(data, str) and JWT_PATTERN.match(data):
        return '***JWT_TOKEN***'
    return data
```

---

### Task 1.3: Add Security Configuration Warnings

**Priority:** P0  
**Effort:** 1 day  
**Assignee:** Backend Team

**Description:**
Add warnings when insecure configurations are detected in production mode.

**Implementation Steps:**

1. **Update Settings Class**
   - File: `agentflow_cli/src/app/core/config/settings.py`
   - Add validators for CORS, MODE, DEBUG settings
   - Add `model_post_init` for startup warnings
   - Normalize MODE to lowercase

2. **Add Startup Security Check**
   - File: `agentflow_cli/src/app/main.py`
   - Run security configuration check on startup
   - Log warnings for insecure configurations
   - Create summary of security posture

**Acceptance Criteria:**
- [x] Warnings for CORS wildcard in production
- [x] Warnings for DEBUG mode in production
- [x] Warnings for enabled docs in production
- [x] MODE is normalized to lowercase
- [x] Startup security check runs
- [x] Warnings are visible in logs

**Example Code:**
```python
# agentflow_cli/src/app/core/config/settings.py
from pydantic import validator

class Settings(BaseSettings):
    # ... existing fields ...
    
    @validator("ORIGINS")
    def warn_cors_wildcard(cls, v):
        mode = os.environ.get("MODE", "development").lower()
        if v == "*" and mode == "production":
            logger.warning(
                "⚠️  SECURITY WARNING: CORS ORIGINS='*' in production.\n"
                "   Set ORIGINS to specific domains."
            )
        return v
    
    @validator("MODE", pre=True)
    def normalize_mode(cls, v):
        return v.lower() if v else "development"
    
    def model_post_init(self, __context):
        if self.MODE == "production":
            if self.IS_DEBUG:
                logger.warning("⚠️  DEBUG mode enabled in production!")
            if self.DOCS_PATH or self.REDOCS_PATH:
                logger.warning("⚠️  API docs enabled in production!")
```

---

## P1: High Priority - Framework Improvements (Week 3-4)

### Task 2.1: Add Request Size Limit Middleware

**Priority:** P1  
**Effort:** 1 day  
**Assignee:** Backend Team

**Description:**
Prevent DoS attacks through large request bodies by adding configurable size limits.

**Implementation Steps:**

1. **Create Middleware**
   - File: `agentflow_cli/src/app/core/middleware/request_limits.py` (new)
   - Implement `RequestSizeLimitMiddleware`
   - Default limit: 10MB
   - Return 413 for oversized requests

2. **Add to Setup**
   - File: `agentflow_cli/src/app/core/config/setup_middleware.py`
   - Add middleware to app
   - Make limit configurable via settings

3. **Add Configuration**
   - File: `agentflow_cli/src/app/core/config/settings.py`
   - Add `MAX_REQUEST_SIZE` setting
   - Default to 10MB

**Acceptance Criteria:**
- [x] Middleware created and tested
- [x] Default 10MB limit applied
- [x] Configurable via environment variable
- [x] Returns proper error response
- [x] Documentation updated
- [x] Integration tests added

---

### Task 2.2: Improve Error Message Sanitization

**Priority:** P1  
**Effort:** 2 days  
**Assignee:** Backend Team

**Description:**
Ensure error messages don't expose internal details in production.

**Implementation Steps:**

1. **Update Error Handlers**
   - File: `agentflow_cli/src/app/core/exceptions/handle_errors.py`
   - Add production/development mode checks
   - Create generic error messages for production
   - Include correlation IDs in all errors

2. **Create Safe Error Messages**
   - Create mapping of status codes to safe messages
   - Return detailed errors only in development

3. **Add Error Response Schema**
   - Include correlation ID in all responses
   - Document error response format

**Acceptance Criteria:**
- [x] Production mode returns generic errors
- [x] Development mode returns detailed errors
- [x] All errors include correlation ID
- [x] Internal details not exposed
- [x] Error format documented
- [x] Tests for both modes

---

### Task 2.3: Create Security Documentation

**Priority:** P1  
**Effort:** 3 days  
**Assignee:** Documentation Team

**Description:**
Create comprehensive security documentation for developers.

**Implementation Steps:**

1. **Create SECURITY.md**
   - File: `SECURITY.md` (new in project root)
   - Cover threat model
   - Authentication setup guide
   - Authorization patterns
   - Production deployment checklist
   - Secure configuration examples

2. **Update README**
   - Add security section
   - Link to SECURITY.md
   - Add production checklist summary

3. **Create Examples**
   - Directory: `examples/security/` (new)
   - JWT authentication example
   - Custom auth backend example
   - Authorization backend example
   - Secure production config

4. **API Documentation**
   - Add security notes to API docs
   - Document authentication requirements
   - Explain authorization flow

**Acceptance Criteria:**
- [x] SECURITY.md created with comprehensive guide
- [x] README has security section
- [x] Examples for auth and authz
- [x] Production deployment guide
- [x] Configuration examples
- [x] Best practices documented

---

### Task 2.4: Improve User Context Injection

**Priority:** P1  
**Effort:** 2 days  
**Assignee:** Backend Team

**Description:**
Improve how user context flows through the application using DI.

**Implementation Steps:**

1. **Create UserContext Class**
   - File: `agentflow_cli/src/app/core/auth/user_context.py` (new)
   - Create `UserContext` model
   - Store user info and request metadata

2. **Update Services**
   - Files: Service classes
   - Remove manual `_config()` methods
   - Use injected `UserContext`
   - Simplify service methods

3. **Update Container Configuration**
   - File: `agentflow_cli/src/app/loader.py`
   - Configure scoped user context binding
   - Ensure context available in all services

**Acceptance Criteria:**
- [ ] UserContext class created
- [ ] Services use injected context
- [ ] Manual config merging removed
- [ ] Context properly scoped
- [ ] Tests verify context injection
- [ ] Backward compatibility maintained

---

## P2: Medium Priority - Developer Experience (Month 2)

### Task 3.1: Add Rate Limiting Helper

**Priority:** P2  
**Effort:** 2 days  
**Assignee:** Backend Team

**Description:**
Provide optional rate limiting utility for developers.

**Implementation Steps:**

1. **Create Helper Module**
   - File: `agentflow_cli/src/app/utils/rate_limit.py` (new)
   - Implement `setup_rate_limiting()` function
   - Support slowapi integration
   - Make it optional (not required dependency)

2. **Add Documentation**
   - Document how to use rate limiting
   - Provide configuration examples
   - Show Redis integration

3. **Create Example**
   - Directory: `examples/rate_limiting/` (new)
   - Show basic rate limiting
   - Show distributed rate limiting with Redis

**Acceptance Criteria:**
- [ ] Helper function created
- [ ] Documentation complete
- [ ] Example provided
- [ ] Optional dependency documented
- [ ] Works with and without Redis

---

### Task 3.2: Add Security Headers Middleware

**Priority:** P2  
**Effort:** 1 day  
**Assignee:** Backend Team

**Description:**
Provide optional security headers middleware.

**Implementation Steps:**

1. **Create Middleware**
   - File: `agentflow_cli/src/app/core/middleware/security_headers.py` (new)
   - Implement `SecurityHeadersMiddleware`
   - Add standard security headers
   - Make configurable

2. **Add Documentation**
   - Explain each header
   - Show how to enable
   - Document customization

**Headers to Add:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (if HTTPS)
- `Content-Security-Policy` (configurable)

**Acceptance Criteria:**
- [x] Middleware created
- [x] All headers configurable
- [x] Documentation complete
- [x] Example provided
- [x] Tests added

---

### Task 3.3: Add Module Path Validation

**Priority:** P2  
**Effort:** 1 day  
**Assignee:** Backend Team

**Description:**
Add validation warnings for unusual module paths.

**Implementation Steps:**

1. **Update Loader**
   - File: `agentflow_cli/src/app/loader.py`
   - Add `validate_module_path()` function
   - Check for path traversal patterns
   - Warn about unusual patterns

2. **Add Tests**
   - Test valid paths
   - Test suspicious patterns
   - Verify warnings are logged

**Acceptance Criteria:**
- [ ] Validation function added
- [ ] Warnings for suspicious paths
- [ ] No false positives
- [ ] Tests comprehensive
- [ ] Documentation updated

---

### Task 3.4: Add CLI Path Validation

**Priority:** P2  
**Effort:** 1 day  
**Assignee:** CLI Team

**Description:**
Validate paths in CLI commands to prevent path traversal.

**Implementation Steps:**

1. **Create Validation Utility**
   - File: `agentflow_cli/cli/core/path_validator.py` (new)
   - Implement `validate_safe_path()` function
   - Check for traversal attempts
   - Restrict to allowed directories

2. **Update Init Command**
   - File: `agentflow_cli/cli/commands/init.py`
   - Add path validation
   - Reject dangerous paths

3. **Update Build Command**
   - File: `agentflow_cli/cli/commands/build.py`
   - Add path validation

**Acceptance Criteria:**
- [ ] Validation utility created
- [ ] Init command validates paths
- [ ] Build command validates paths
- [ ] Tests for path traversal
- [ ] Error messages helpful

---

## P3: Long-term - Advanced Features (Month 3+)

### Task 4.1: Add Audit Logging System

**Priority:** P3  
**Effort:** 1 week  
**Assignee:** Backend Team

**Description:**
Provide optional audit logging for security events.

**Implementation Steps:**

1. **Create Audit Logger**
   - File: `agentflow_cli/src/app/core/audit/audit_logger.py` (new)
   - Define audit event types
   - Create structured logging format
   - Support multiple backends

2. **Add Event Tracking**
   - Track authentication events
   - Track authorization failures
   - Track resource access
   - Track configuration changes

3. **Create Storage Backends**
   - File backend
   - Database backend
   - External service backend (e.g., Splunk)

**Acceptance Criteria:**
- [ ] Audit logging system created
- [ ] Key events tracked
- [ ] Multiple backends supported
- [ ] Documentation complete
- [ ] Example configuration

---

### Task 4.2: Create Security Testing Tools

**Priority:** P3  
**Effort:** 1 week  
**Assignee:** QA Team

**Description:**
Develop tools to help developers test security configurations.

**Implementation Steps:**

1. **Create Security Checker CLI**
   - File: `agentflow_cli/cli/commands/security_check.py` (new)
   - Scan configuration for issues
   - Check for common misconfigurations
   - Generate security report

2. **Add Unit Test Helpers**
   - Create auth testing utilities
   - Create authz testing utilities
   - Mock authentication helpers

3. **Create Integration Tests**
   - Test authentication flows
   - Test authorization scenarios
   - Test security headers
   - Test rate limiting

**Acceptance Criteria:**
- [ ] Security check command created
- [ ] Testing utilities provided
- [ ] Integration tests comprehensive
- [ ] Documentation for testing
- [ ] CI/CD integration guide

---

### Task 4.3: Add RBAC Support

**Priority:** P3  
**Effort:** 2 weeks  
**Assignee:** Backend Team

**Description:**
Provide optional Role-Based Access Control framework.

**Implementation Steps:**

1. **Create RBAC Models**
   - File: `agentflow_cli/src/app/core/auth/rbac/` (new directory)
   - Define Role, Permission models
   - Create policy engine
   - Support hierarchical roles

2. **Create RBAC Backend**
   - Implement `RBACAuthorizationBackend`
   - Support role assignments
   - Support permission checks

3. **Add Storage Layer**
   - In-memory store
   - Database store
   - External policy service

**Acceptance Criteria:**
- [ ] RBAC models defined
- [ ] Policy engine implemented
- [ ] Storage backends created
- [ ] Example implementation
- [ ] Comprehensive documentation

---

### Task 4.4: Create Deployment Templates

**Priority:** P3  
**Effort:** 1 week  
**Assignee:** DevOps Team

**Description:**
Provide secure deployment templates for common platforms.

**Implementation Steps:**

1. **Docker Compose Template**
   - Include reverse proxy (Nginx/Traefik)
   - HTTPS configuration
   - Security best practices
   - Environment management

2. **Kubernetes Templates**
   - Deployment manifests
   - Service definitions
   - Ingress configuration
   - Secret management

3. **Cloud Platform Guides**
   - AWS deployment guide
   - GCP deployment guide
   - Azure deployment guide
   - Security checklist for each

**Acceptance Criteria:**
- [ ] Docker Compose template
- [ ] Kubernetes manifests
- [ ] Cloud deployment guides
- [ ] Security properly configured
- [ ] Documentation complete

---

## Implementation Timeline

### Week 1-2: P0 Critical Items
- [x] Task 1.1: Authorization hooks (3 days) - COMPLETED
- [x] Task 1.2: Log sanitization (1 day) - COMPLETED
- [x] Task 1.3: Security warnings (1 day) - COMPLETED
- [x] Code review and testing (2 days) - COMPLETED

### Week 3-4: P1 High Priority
- [x] Task 2.1: Request size limits (1 day) - COMPLETED
- [x] Task 2.2: Error sanitization (2 days) - COMPLETED
- [x] Task 2.3: Security documentation (3 days) - COMPLETED
- [ ] Task 2.4: User context injection (2 days)
- [ ] Integration testing (2 days)

### Month 2: P2 Medium Priority
- [ ] Task 3.1: Rate limiting helper (2 days)
- [x] Task 3.2: Security headers (1 day) - COMPLETED
- [ ] Task 3.3: Module path validation (1 day)
- [ ] Task 3.4: CLI path validation (1 day)
- [ ] Testing and documentation (5 days)

### Month 3+: P3 Long-term
- [ ] Task 4.1: Audit logging (1 week)
- [ ] Task 4.2: Security testing tools (1 week)
- [ ] Task 4.3: RBAC support (2 weeks)
- [ ] Task 4.4: Deployment templates (1 week)

---

## Testing Strategy

### Unit Tests
- [ ] Authorization backend tests
- [ ] Log sanitization tests
- [ ] Configuration validation tests
- [ ] Middleware tests

### Integration Tests
- [ ] Auth flow tests
- [ ] Authorization checks tests
- [ ] Error handling tests
- [ ] Security header tests

### Security Tests
- [ ] Penetration testing
- [ ] Configuration scanning
- [ ] Dependency vulnerability scanning
- [ ] OWASP Top 10 validation

---

## Documentation Updates

### Required Documentation
- [ ] SECURITY.md - Comprehensive security guide
- [ ] README.md - Security section
- [ ] API documentation - Security notes
- [ ] Configuration guide - Security settings
- [ ] Deployment guide - Production checklist
- [ ] Examples - Auth/authz implementations

---

## Success Metrics

### Code Quality
- [ ] 100% of P0 items completed
- [ ] 80%+ test coverage for security code
- [ ] Zero critical security findings
- [ ] All warnings properly documented

### Developer Experience
- [ ] Security documentation rated helpful (>4/5)
- [ ] Examples cover common use cases
- [ ] Configuration errors are clear
- [ ] Migration path is smooth

### Security Posture
- [ ] Authorization hooks available
- [ ] Sensitive data not logged
- [ ] Production warnings in place
- [ ] Security best practices documented

---

## Risk Management

### Potential Risks
1. **Breaking Changes** - Authorization changes might break existing code
   - Mitigation: Backward compatibility, clear migration guide
   
2. **Performance Impact** - Sanitization might slow logging
   - Mitigation: Performance testing, optimization
   
3. **Adoption** - Developers might not follow best practices
   - Mitigation: Good documentation, helpful warnings, examples

### Rollback Plan
- Each feature should be toggleable
- Keep backward compatibility where possible
- Document migration steps clearly

---

## Sign-off

- [ ] Security team approval
- [ ] Engineering team approval
- [ ] Documentation team approval
- [ ] Product team approval

---

## Notes

- This plan focuses on framework-level improvements
- Developer responsibilities remain unchanged
- All changes should maintain backward compatibility
- Documentation is as important as code changes

**Next Steps:**
1. Review and approve this action plan
2. Create GitHub issues for each task
3. Assign tasks to team members
4. Begin implementation of P0 items
