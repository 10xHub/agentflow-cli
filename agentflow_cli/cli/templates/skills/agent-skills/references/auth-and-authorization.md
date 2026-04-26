# Auth and Authorization

Use this when changing HTTP authentication, authorization, permission checks, or client auth examples.

## Authentication Modes

Default:

- `auth: null`
- No authentication.
- Suitable only for local development or trusted gateways.

JWT:

- `auth: "jwt"`
- Requires `JWT_SECRET_KEY` and `JWT_ALGORITHM`.
- Requests use `Authorization: Bearer <token>`.
- Decoded JWT payload becomes the endpoint `user` context.

Custom:

```json
{
  "auth": {
    "method": "custom",
    "path": "graph.auth:MyAuthBackend"
  }
}
```

Custom auth backends implement `BaseAuth.authenticate(request) -> dict | None`.

## Authorization

Authorization decides whether an authenticated user can perform a resource/action pair.

Configure:

```json
{
  "authorization": "graph.auth:my_authorization_backend"
}
```

Backends implement:

```python
async def authorize(self, user: dict, resource: str, action: str) -> bool:
    ...
```

Common resources/actions:

- `graph`: `invoke`, `stream`, `read`, `stop`, `setup`, `fix`
- `checkpointer`: `read`, `write`, `delete`
- `store`: `read`, `write`, `delete`
- `files`: `upload`, `read`

Routes use `RequirePermission(resource, action)`.

## TypeScript Client

Pass auth headers through the client config:

```typescript
const client = new AgentFlowClient({
  baseUrl: "http://127.0.0.1:8000",
  headers: { Authorization: `Bearer ${token}` },
});
```

## Rules

- Do not use unauthenticated API mode in production unless a trusted gateway handles auth.
- Keep authorization separate from graph business logic.
- Return 401 for authentication failure and 403 for authorization failure.
- Use sanitized logging for tokens and user payloads.
- Update permission tables when adding routes.

## Source Map

- Base auth: `agentflow-api/agentflow_cli/src/app/core/auth/base_auth.py`
- JWT auth: `agentflow-api/agentflow_cli/src/app/core/auth/jwt_auth.py`
- Auth backend loader: `agentflow-api/agentflow_cli/src/app/core/auth/auth_backend.py`
- Authorization: `agentflow-api/agentflow_cli/src/app/core/auth/authorization.py`
- Permission dependency: `agentflow-api/agentflow_cli/src/app/core/auth/permissions.py`
- Main docs: `agentflow-docs/docs/reference/api-cli/auth.md`
- Production docs: `agentflow-docs/docs/how-to/production/auth-and-authorization.md`
