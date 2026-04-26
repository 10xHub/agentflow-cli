# Security and Validators

Use this when adding prompt-injection protection, content validation, auth-sensitive tool behavior, or safety checks.

## Validator API

Validators subclass `BaseValidator` and implement:

```python
async def validate(self, messages: list[Message]) -> bool:
    ...
```

Register validators on `CallbackManager`:

```python
callback_manager = CallbackManager()
callback_manager.register_input_validator(MyValidator())
app = graph.compile(callback_manager=callback_manager)
```

## Built-ins

Exports from `agentflow.utils.validators`:

- `PromptInjectionValidator`
- `MessageContentValidator`
- `ValidationError`
- `register_default_validators`

Use `register_default_validators(callback_manager, strict_mode=True)` to enable standard protections. Strict mode blocks by raising `ValidationError`; lenient behavior may sanitize/log depending on validator settings.

## Callback-Based Safety

Use `register_before_invoke` for pre-model or pre-tool checks. Use `register_after_invoke` for output policy checks. Use `register_on_error` for controlled recovery values.

Common safety points:

- User input validation before AI invocation.
- Tool argument policy before tool execution.
- Model output validation before returning to API clients.
- Store/memory write validation.

## API Security Boundary

This reference covers graph-level validators. For HTTP auth, read `auth-and-authorization.md`.

For production:

- Enable API auth unless behind a trusted gateway.
- Restrict CORS origins.
- Keep docs endpoints off or protected if needed.
- Validate remote tool registrations if exposed beyond trusted clients.

## Rules

- Keep validators deterministic and fast.
- Avoid calling LLMs inside validators on the hot path unless explicitly intended.
- Include the relevant invocation type when registering callbacks.
- Raise `ValidationError` for expected policy failures.
- Log safely; sanitize user/tool data before logs.

## Source Map

- Callback system: `agentflow/agentflow/utils/callbacks.py`
- Validators: `agentflow/agentflow/utils/validators.py`
- API error handlers: `agentflow-api/agentflow_cli/src/app/core/exceptions/handle_errors.py`
- Main docs: `agentflow-docs/docs/reference/python/callback-manager.md`
- How-to: `agentflow-docs/docs/how-to/python/protect-against-prompt-injection.md`
