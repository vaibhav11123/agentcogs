# GitHub setup

**Repository:** https://github.com/vaibhav11123/agentcogs

**Visibility:** public (MIT). Pre-flight: `./scripts/audit_before_public.sh` — see [OPEN_SOURCE.md](OPEN_SOURCE.md).

## CI

Every push and PR to `main` runs [.github/workflows/ci.yml](../.github/workflows/ci.yml):

| Check | What it runs |
|-------|----------------|
| SDK Tests | `pytest tests/` |
| Backend Tests | `pytest backend/tests/` (mocked DB/Redis) |
| Dashboard Build | `npm ci && npm run build` |

PyPI publish (on GitHub Release) waits for the same CI jobs to pass.

## Branch protection

**Status:** CI checks run on every push/PR. **Rules on `main` are not enabled yet** — GitHub requires **Pro** (or a **public** repo) for branch protection on private repositories.

When you have Pro (or make the repo public), run:

```bash
gh api --method PUT repos/vaibhav11123/agentcogs/branches/main/protection \
  -f required_pull_request_reviews='{"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":0}' \
  -f enforce_admins=false \
  -F allow_force_pushes=false \
  -F allow_deletions=false \
  -f restrictions=null \
  -f required_status_checks='{"strict":true,"checks":[{"context":"SDK Tests"},{"context":"Backend Tests"},{"context":"Dashboard Build"}]}'
```

Or use **Settings → Branches → Add rule** for `main` with:

- Require a pull request before merging
- Require status checks: **SDK Tests**, **Backend Tests**, **Dashboard Build**
- Require branches to be up to date

Until then, use PRs manually so CI must pass before merge.

## Day-to-day workflow

```bash
git checkout -b your-branch
# ... changes ...
git push -u origin your-branch
gh pr create --fill
# merge after CI is green
```

## Transfer to `agentcogs` org (when ready)

The `agentcogs` org does **not** exist on GitHub yet (cannot create via `gh` CLI). Create it first:

1. https://github.com/organizations/plan — choose a plan and create org `agentcogs`
2. Transfer the repo:

```bash
gh repo transfer vaibhav11123/agentcogs agentcogs --yes
```

If your CLI uses the older flag form:

```bash
gh repo transfer agentcogs --user agentcogs --yes
```

Then update URLs:

- `pyproject.toml` → `https://github.com/agentcogs/agentcogs`
- `README.md` monorepo table link

Re-add branch protection on the repo under the org if GitHub resets rules during transfer.
