# Slack cost spike alerts

AgentCOGS can post to a **Slack Incoming Webhook** when a customer's run cost spikes (z-score or multiplier above normal).

This is **operate-phase** setup — complete [quickstart](../quickstart.md) first so events flow into the dashboard.

## Setup

1. In Slack: **Apps** → create or pick an app → **Incoming Webhooks** → add to a channel → copy the webhook URL.
2. In AgentCOGS: **Settings** → **Cost spike alerts** → paste the URL → **Save**.
3. Click **Send test to Slack** — you should see a test message in that channel within a few seconds.

## What triggers an alert

After each ingested run, the backend checks rolling cost for that customer + workflow:

- Fewer than 5 historical runs: flag if cost &gt; **$5**
- Otherwise: flag if z-score &gt; **2.5** or cost &gt; **3×** the 30-day mean
- Suppression: at most one alert per customer + workflow every **6 hours**

Alerts include a button linking to the customer page in the dashboard (with the run highlighted when opened from Slack).

## Email alerts

Optionally set **Alert email** on the same Settings card. Email requires Resend to be configured on the API (`RESEND_API_KEY`).

## Security

- Treat the webhook URL like a password. Anyone with the URL can post to your channel.
- The dashboard only shows a **masked** URL after save; paste a new URL to replace.
- Use **Clear Slack** to remove the webhook from your workspace.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test returns 502 | URL invalid or Slack rejected the payload — recreate the webhook in Slack |
| Test returns 400 | No webhook saved — paste URL and Save or Send test |
| No spike alerts | Spikes may be suppressed (6h window) or under threshold — check **Alerts** page |
| Button opens wrong page | Ensure you're on a current dashboard build (links use customer UUID) |

See also [troubleshooting.md](../troubleshooting.md).
