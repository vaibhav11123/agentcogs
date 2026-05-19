# Langfuse discussion #9708 — reply (paste or posted via gh)

**Thread:** https://github.com/orgs/langfuse/discussions/9708

---

This is exactly the problem we built AgentCOGS for.

On the API path: the v2 Metrics API does not support `groupBy` on `userId` (filter-only). For per-user **cost totals**, Langfuse’s legacy Daily Metrics API works: `GET /api/public/metrics/daily?userId={your_tenant_id}&fromTimestamp=...&toTimestamp=...` — loop once per customer, batch daily.

AgentCOGS can do two things: (1) **SDK** — wrap your LLM calls with `agentcogs.run(customer_id=...)` for real-time per-customer cost + budget caps; (2) **import** — join that cost with customer revenue for a margin leaderboard (the part spreadsheets usually do).

If you’re doing this manually today: [quickstart](https://github.com/vaibhav11123/agentcogs/blob/main/docs/quickstart.md) (~10 min to first dashboard row).
