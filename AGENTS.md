# Agent instructions (this repository)

Instructions for coding agents working in this repo.

## Git commits and pull requests

- **Never** add `Co-authored-by: Cursor`, `Made with Cursor`, `Generated with Cursor`, or any agent attribution trailers unless the human explicitly asks for them in that message.
- **Never** commit: `.cursor/`, `docs/internal/`, `docs/launch/`, GTM playbooks (`docs/*PLAYBOOK*`, `docs/GTM_*`, etc.), `.env` files, or `tools/.demo_env`.
- Run `./scripts/audit_before_public.sh` before pushing if you changed what is tracked.

## Product scope

- Public repo is **MIT / self-host first** — SDK, backend, dashboard, user docs only.
- Maintainer GTM and IDE config stay **local** (see `.gitignore`).

## Hooks

After clone, run: `./scripts/install-githooks.sh`
