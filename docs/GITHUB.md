# GitHub setup

**Repository:** https://github.com/vaibhav11123/agentcogs (private)

## CI

Every push and PR to `main` runs [.github/workflows/ci.yml](../.github/workflows/ci.yml):

| Check | What it runs |
|-------|----------------|
| SDK Tests | `pytest tests/` |
| Backend Tests | `pytest backend/tests/` (mocked DB/Redis) |
| Dashboard Build | `npm ci && npm run build` |

PyPI publish (on GitHub Release) waits for the same CI jobs to pass.

## Branch protection

`main` requires:

- Pull request before merge (no direct pushes)
- Status checks: **SDK Tests**, **Backend Tests**, **Dashboard Build**
- Branch up to date with `main` before merge

## Day-to-day workflow

```bash
git checkout -b your-branch
# ... changes ...
git push -u origin your-branch
gh pr create --fill
# merge after CI is green
```

## Transfer to `agentcogs` org (when ready)

The `agentcogs` GitHub organization must exist first (create at https://github.com/organizations/plan).

```bash
# After you own/create the org:
gh repo transfer agentcogs --user agentcogs --yes
```

Then update URLs:

- `pyproject.toml` → `https://github.com/agentcogs/agentcogs`
- `README.md` monorepo table link

Re-add branch protection on the repo under the org if GitHub resets rules during transfer.
