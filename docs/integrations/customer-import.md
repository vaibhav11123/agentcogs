# Customer import API

Pre-fill the dashboard with customers before the first SDK event.

**Note:** Import does **not** attribute LLM spend. You still need `agentcogs.run()` in application code.

```http
POST /v1/customers/import
Cookie: acg_session=...
Content-Type: application/json

{
  "customers": [
    {
      "external_id": "acme_123",
      "display_name": "Acme Corp",
      "monthly_revenue_usd": 8200,
      "monthly_budget_usd": 500
    }
  ],
  "mode": "upsert"
}
```

Response: `{ "created": 1, "updated": 0, "errors": [] }`

Free tier: total unique customers cannot exceed 5.

## Related

- [Customer ID mapping](../concepts/customer-id.md)
- [Quickstart](../quickstart.md)
