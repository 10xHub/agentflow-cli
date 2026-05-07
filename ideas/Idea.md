# Onboarding Flow — Implementation Idea

## Goal

Make `agentflow init` interactive and template-driven, so users get a smooth setup
without passing any extra CLI arguments.

---

## Recommendation: `questionary` + `string.Template`

### Why This Stack

- **`string.Template`** — built into Python, zero extra dependency. Uses `$placeholder`
  syntax. Simple enough for our needs (substituting agent name, auth type, etc. into files).
- **`questionary`** — one pip install, gives arrow-key select prompts. Much better UX
  than numbered `click.prompt()` choices.

Only upgrade to Jinja2 if we ever need conditional blocks *inside* template files
(e.g., "only include this import if auth=JWT"). For now, we don't need that.

---

## Interactive Flow

```
agentflow init

  What is your agent name? (default: MyAgent)
  → text input

  Quick Start or Production setup? (default: Quick Start)
  → arrow-key select

  [if Production]
  What type of authentication? (Options: JWT, Custom, None)
  → arrow-key select

  [if Production]
  Do you want rate limiting? (Options: No, Memory Based, Redis Based)
  → arrow-key select
```

All answers are collected into a single plain dict (the "context").

---

## Template Strategy

### Directory Structure

Keep the existing `templates/dev/` and `templates/prod/` dirs as-is.
Files that need dynamic values use `$placeholder` syntax:

```
templates/dev/agentflow.json     →  "agent": "$agent_name"
templates/prod/agentflow.json    →  "agent": "$agent_name", "auth": "$auth"
```

### Copy + Render Logic

Walk the selected template directory. For each file:
- Read content
- Run `string.Template(content).substitute(context)`
- Write to destination path

That's one for-loop. No renderer class needed.

---

## Context Dict Example

```python
context = {
    "agent_name": "MyAgent",
    "auth": "jwt",           # or "custom" or "none"
    "rate_limit": "memory",  # or "redis" or "none"
}
```

The `agentflow.json` template uses these values directly.

---

## agentflow.json Behavior

| User Choice        | agentflow.json value          |
|--------------------|-------------------------------|
| Auth: JWT          | `"auth": "jwt"`               |
| Auth: Custom       | `"auth": "custom"`            |
| Auth: None         | `"auth": null`                |
| Rate limit: Redis  | `"rate_limit": "redis"`       |
| Rate limit: Memory | `"rate_limit": "memory"`      |
| Rate limit: No     | `"rate_limit": null`          |

---

## After Init — Next Steps

Once files are written, guide the user:

```
1. agentflow skills        ← install coding agent skills
2. pip install google-genai
3. Set up your .env file
4. agentflow play          ← enjoy!
```

---

## What Changes in Code

| File | Change |
|------|--------|
| `agentflow_cli/cli/commands/init.py` | Replace static file writes with prompt → context → render loop |
| `agentflow_cli/cli/templates/dev/agentflow.json` | Add `$agent_name` placeholder |
| `agentflow_cli/cli/templates/prod/agentflow.json` | Add `$agent_name`, `$auth`, `$rate_limit` placeholders |
| `requirements.txt` / `pyproject.toml` | Add `questionary` dependency |
| `defaults.py` | Can be cleaned up — most constants move into template files |
