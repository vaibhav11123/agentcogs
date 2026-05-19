# Security policy

## Supported versions

Security fixes are applied on the `main` branch. Release tags (when published) receive backports at maintainer discretion.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security-sensitive reports.**

Email or DM the maintainer with:

- Description of the issue and impact
- Steps to reproduce
- Affected paths (SDK, backend, dashboard)
- Suggested fix (if any)

We aim to acknowledge within **72 hours** and share a remediation timeline when confirmed.

## Scope

In scope:

- Authentication and session handling (`backend/app/auth.py`, cookies)
- Ingest API abuse, tenant isolation, API key handling
- Dashboard API authorization
- Secret leakage in logs or Slack alert payloads

Out of scope (unless chained with a product bug):

- Misconfiguration of your own `.env` or self-hosted deployment
- Third-party services (Stripe, Resend, Supabase, etc.)

## Safe defaults for self-hosters

- Rotate `JWT_SECRET` and API keys in production
- Do not commit `.env`, `tools/.demo_env`, or real API keys
- Run `./scripts/audit_before_public.sh` before publishing forks publicly
