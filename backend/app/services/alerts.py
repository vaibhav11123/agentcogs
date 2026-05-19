"""Slack + Resend email alert delivery."""
import logging

import httpx
import resend

from ..config import settings

log = logging.getLogger("agentcogs.alerts")

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


async def send_alert(db, anomaly_id: str):
    """Look up the anomaly + dispatch Slack and/or email."""
    data = await db.fetchrow(
        """
        SELECT a.id, a.z_score, a.multiplier, a.mean_usd,
               c.display_name, c.external_id,
               e.workflow_id, e.total_usd, e.id AS event_id,
               w.slack_webhook_url, w.alert_email
        FROM anomalies a
        JOIN customers c ON c.id = a.customer_id
        JOIN cost_events e ON e.id = a.cost_event_id
        JOIN workspaces w ON w.id = a.workspace_id
        WHERE a.id = $1
        """,
        anomaly_id,
    )
    if not data:
        return

    name = data["display_name"] or data["external_id"]
    mult = float(data["multiplier"] or 0)
    cost = float(data["total_usd"])
    workflow = data["workflow_id"]
    event_id = data["event_id"]

    summary = (
        f"⚠️ Cost spike: {name} ran '{workflow}' for ${cost:.4f} "
        f"— {mult:.1f}× above normal."
    )
    base = settings.app_base_url.rstrip("/")
    drill_url = f"{base}/customers/{data['external_id']}?event={event_id}"

    if data["slack_webhook_url"]:
        await _send_slack(data["slack_webhook_url"], summary, drill_url, data)
    if data["alert_email"] and settings.resend_api_key:
        _send_email(data["alert_email"], summary, drill_url, data)

    await db.execute(
        "UPDATE anomalies SET alerted_at = NOW() WHERE id = $1",
        anomaly_id,
    )


async def _send_slack(webhook_url: str, summary: str, drill_url: str, data: dict):
    payload = {
        "text": summary,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{summary}*"}},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Customer:*\n{data['display_name'] or data['external_id']}",
                    },
                    {"type": "mrkdwn", "text": f"*Workflow:*\n`{data['workflow_id']}`"},
                    {"type": "mrkdwn", "text": f"*Cost:*\n${float(data['total_usd']):.4f}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Normal avg:*\n${float(data['mean_usd'] or 0):.4f}",
                    },
                ],
            },
            {
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open in AgentCOGS"},
                    "url": drill_url,
                }],
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(webhook_url, json=payload)
    except Exception as e:
        log.warning("slack delivery failed: %s", e)


def _send_email(to: str, summary: str, drill_url: str, data: dict):
    try:
        resend.Emails.send({
            "from": settings.alert_from_email,
            "to": to,
            "subject": f"AgentCOGS alert: {data['display_name'] or data['external_id']}",
            "html": f"""
                <p><strong>{summary}</strong></p>
                <ul>
                  <li>Customer: {data['display_name'] or data['external_id']}</li>
                  <li>Workflow: <code>{data['workflow_id']}</code></li>
                  <li>Cost: ${float(data['total_usd']):.4f}</li>
                  <li>Normal avg: ${float(data['mean_usd'] or 0):.4f}</li>
                </ul>
                <p><a href="{drill_url}">Open in AgentCOGS →</a></p>
            """,
        })
    except Exception as e:
        log.warning("email delivery failed: %s", e)
