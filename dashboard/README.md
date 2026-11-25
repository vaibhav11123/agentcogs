# AgentCOGS Dashboard

React dashboard for customer-level AI unit economics. AI margin is the monthly fee minus attributed AI cost, divided by the fee. It is not total customer profitability.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_URL` to the API you deployed, for example `https://api.yourdomain.com`. Leave it unset for the public sample. The two maintainer hosts are treated as unset, so that sample stays the static book.

## Views

- **Leaderboard** — customers sorted by AI cost, margin, budget status
- **Customer detail** — daily cost chart + LangGraph node breakdown
- **Settings** — monthly CSV export

Deploy to Vercel with root `dashboard/`.
