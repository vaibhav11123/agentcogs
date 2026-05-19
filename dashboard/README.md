# AgentCOGS Dashboard

React dashboard for per-customer LLM cost attribution and gross margin.

## Setup

```bash
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_URL` to your backend (default `http://localhost:8000`).

## Views

- **Leaderboard** — customers sorted by AI cost, margin, budget status
- **Customer detail** — daily cost chart + LangGraph node breakdown
- **Settings** — monthly CSV export

Deploy to Vercel with root `dashboard/`.
