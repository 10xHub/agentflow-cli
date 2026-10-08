# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| `0.7.x` (`10xgraph-api`) | Yes |
| `< 0.7` (`10xscale-agentflow-cli`) | No |

Only the latest minor release receives security fixes. `10xgraph-api` is
pre-1.0; there are no long-term support branches yet. `10xscale-agentflow-cli` is no
longer published; upgrade to `10xgraph-api` to receive fixes.

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Report privately through either channel:

1. **GitHub private vulnerability reporting** (preferred) - go to the
   [Security tab](https://github.com/10xGraph/10xgraph-api/security/advisories/new) and
   open a draft advisory.
2. **Email** - `contact@10xscale.ai`, with `SECURITY` in the subject line.

Please include:

- The affected version (`10xgraph version` output).
- A description of the issue and its impact.
- Reproduction steps or a proof of concept.
- Any relevant configuration (`10xgraph.json`, auth mode, rate limit backend) with
  secrets redacted.

## What to expect

| Stage | Target |
|---|---|
| Acknowledgement of your report | 3 business days |
| Initial assessment and severity | 7 business days |
| Fix released, or a status update if longer | 30 days |

We will credit you in the release notes unless you ask us not to. Please give us a
reasonable window to ship a fix before publishing details.

## Scope

In scope:

- Authentication and authorization bypass in `tenxgraph_api/src/app/core/auth/`,
  including cross-user (IDOR) access to threads, checkpoints, or store memories.
- Route guard bypass - reaching a non-public route without a `RequirePermission` check.
- Rate limit bypass.
- Secret leakage through logs, error responses, or generated scaffolding.
- Path traversal or arbitrary file write in the media/upload endpoints or in
  `10xgraph init` scaffolding.
- Insecure defaults that a deployment would inherit without noticing.

Out of scope:

- Vulnerabilities in a user's own agent graph, tools, or `BaseAuth` subclass.
- Issues that require an already-compromised host or an attacker-controlled
  `10xgraph.json`.
- Missing hardening in a deliberately permissive development configuration
  (`MODE=development`).
- Denial of service through unbounded resource use in a user-supplied tool.

## Deployment hardening

The API refuses to start on some misconfigurations rather than warning - notably wildcard
CORS combined with credentials in production. For anything else, in production set:

- `MODE=production` and `IS_DEBUG=false`
- `ORIGINS` to an explicit comma-separated list, never `*`
- `JWT_SECRET_KEY` to a random value of 32 characters or more
- An `authorization` backend (production defaults to `ownership`; do not weaken it to
  `allow_all`)
