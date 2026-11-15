"""Replay the payloads of the APIs a workspace joins, through our handlers.

Stripe, Slack, Resend, and LiteLLM are not called. The bodies match their
published objects. A signature is computed the way Stripe computes it.
"""
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Backend CI runs with PYTHONPATH=. and does not install the SDK.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.auth import issue_jwt
from app.models import CostEventIn
from app.services.stripe_mrr import subscription_monthly_usd
from app.services.stripe_sync import _meter_already_recorded, sync_daily
from agentcogs.integrations.litellm_event import build_ingest_event


YEARLY_SUB = {
    "id": "sub_yearly",
    "object": "subscription",
    "status": "active",
    "customer": "cus_harbor",
    "items": {
        "object": "list",
        "data": [
            {
                "id": "si_1",
                "quantity": 1,
                "price": {
                    "id": "price_year",
                    "unit_amount": 120000,
                    "recurring": {
                        "interval": "year",
                        "interval_count": 1,
                        "usage_type": "licensed",
                    },
                },
            },
            {
                "id": "si_meter",
                "quantity": 1,
                "price": {
                    "id": "price_meter",
                    "unit_amount": 1,
                    "recurring": {
                        "interval": "month",
                        "interval_count": 1,
                        "usage_type": "metered",
                    },
                },
            },
        ],
    },
    "discount": None,
}


def test_stripe_subscription_object_becomes_monthly_revenue():
    import stripe

    assert subscription_monthly_usd(YEARLY_SUB) == 100.0
    live = stripe.Subscription.construct_from(YEARLY_SUB, "sk_test")
    assert subscription_monthly_usd(live) == 100.0


def test_litellm_openai_usage_and_anthropic_usage_both_validate():
    now = datetime.now(timezone.utc)
    openai_kwargs = {
        "model": "gpt-4o-mini",
        "user": "harbor_clinic",
        "response_cost": 0.0021,
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
        "metadata": {"agentcogs_workflow_id": "intake"},
        "start_time": now,
    }
    anthropic_kwargs = {
        "model": "claude-3-5-sonnet",
        "metadata": {"agentcogs_customer_id": "harbor_clinic", "agentcogs_workflow_id": "intake"},
        "response_cost": 0.84,
        "usage": {"input_tokens": 4200, "output_tokens": 900},
        "start_time": now,
    }
    for kwargs, in_tok, out_tok in (
        (openai_kwargs, 120, 30),
        (anthropic_kwargs, 4200, 900),
    ):
        event = build_ingest_event(kwargs, status="completed")
        parsed = CostEventIn.model_validate(event)
        model = next(iter(parsed.models.values()))
        assert model.input_tokens == in_tok
        assert model.output_tokens == out_tok
        assert parsed.customer_id == "harbor_clinic"

    assert build_ingest_event({"model": "gpt-4o-mini"}, status="completed") is None


def test_stripe_duplicate_meter_identifier_is_already_recorded():
    import stripe

    exc = stripe.error.InvalidRequestError(
        "A meter event with a duplicate identifier has already been submitted.",
        "identifier",
        code="invalid_request_error",
    )
    exc.json_body = {
        "error": {
            "code": "invalid_request_error",
            "message": "A meter event with a duplicate identifier has already been submitted.",
        }
    }
    assert _meter_already_recorded(exc) is True

    other = stripe.error.InvalidRequestError("No such meter", "event_name")
    assert _meter_already_recorded(other) is False


@pytest.mark.asyncio
async def test_sync_daily_marks_duplicate_meter_events_synced():
    import stripe

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    row = {
        "stripe_customer_id": "cus_harbor",
        "stripe_account_id": "acct_123",
        "customer_id": "00000000-0000-0000-0000-0000000000c1",
        "workspace_id": "00000000-0000-0000-0000-0000000000a1",
        "total": 1.25,
        "event_ids": ["00000000-0000-0000-0000-0000000000e1"],
    }
    db = AsyncMock()
    db.fetch = AsyncMock(return_value=[row])
    db.execute = AsyncMock()
    exc = stripe.error.InvalidRequestError(
        "A meter event with a duplicate identifier has already been submitted.",
        "identifier",
    )
    with patch("app.services.stripe_sync.settings") as s, patch(
        "app.services.stripe_sync.stripe.billing.MeterEvent.create", side_effect=exc
    ) as create:
        s.stripe_api_key = "sk_test_x"
        s.stripe_meter_event_name = "agentcogs_ai_usage"
        count = await sync_daily(db)
    assert count == 1
    create.assert_called_once()
    payload = create.call_args.kwargs["payload"]
    assert payload["stripe_customer_id"] == "cus_harbor"
    assert payload["value"] == "125"
    assert create.call_args.kwargs["stripe_account"] == "acct_123"
    db.execute.assert_awaited()
    assert yesterday.isoformat() in create.call_args.kwargs["identifier"]


@pytest.mark.asyncio
async def test_oauth_callback_stores_the_connected_account(mock_app):
    app, mock_db, _ = mock_app
    transport = ASGITransport(app=app)
    token = {
        "access_token": "sk_test_connected",
        "scope": "read_write",
        "livemode": False,
        "token_type": "bearer",
        "stripe_user_id": "acct_1Harbor",
        "stripe_publishable_key": "pk_test_connected",
    }
    with patch("app.routes.stripe_connect.settings") as s, patch(
        "app.routes.stripe_connect.stripe.OAuth.token", return_value=token
    ):
        s.stripe_api_key = "sk_test_platform"
        s.app_base_url = "http://localhost:3000"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/v1/stripe/oauth/callback",
                params={"code": "ac_123", "state": "00000000-0000-0000-0000-00000000a001"},
                follow_redirects=False,
            )
    assert resp.status_code == 307
    assert "stripe=connected" in resp.headers["location"]
    sql, account, ws = mock_db.execute.await_args.args
    assert "stripe_account_id" in sql
    assert account == "acct_1Harbor"


@pytest.mark.asyncio
async def test_sync_revenue_writes_the_normalised_subscription(mock_app):
    app, mock_db, _ = mock_app
    transport = ASGITransport(app=app)
    cookie = issue_jwt("00000000-0000-0000-0000-00000000a001", "local@localhost")

    async def fetchval(sql, *params):
        if "stripe_account_id" in sql:
            return "acct_1Harbor"
        return None

    async def fetch(sql, *params):
        return [{"id": "00000000-0000-0000-0000-0000000000c1", "stripe_customer_id": "cus_harbor"}]

    mock_db.fetchval = AsyncMock(side_effect=fetchval)
    mock_db.fetch = AsyncMock(side_effect=fetch)
    import stripe

    page = stripe.ListObject.construct_from(
        {"object": "list", "data": [YEARLY_SUB], "has_more": False},
        "sk_test",
    )
    with patch("app.routes.stripe_connect.settings") as s, patch(
        "app.routes.stripe_connect.stripe.Subscription.list", return_value=page
    ):
        s.stripe_api_key = "sk_test_platform"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("acg_session", cookie)
            resp = await client.post("/v1/stripe/sync-revenue")
    assert resp.status_code == 200
    assert resp.json() == {"updated": 1, "skipped": 0}
    args = mock_db.execute.await_args.args
    assert args[1] == 100.0


@pytest.mark.asyncio
async def test_signed_stripe_webhook_upgrades_the_workspace(mock_app):
    import stripe

    app, mock_db, _ = mock_app
    secret = "whsec_test_secret_value"
    event = {
        "id": "evt_test",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test",
                "object": "checkout.session",
                "customer": "cus_workspace",
                "metadata": {
                    "workspace_id": "00000000-0000-0000-0000-00000000a001",
                    "plan": "starter",
                },
            }
        },
    }
    payload = json.dumps(event, separators=(",", ":"))
    stamp = int(time.time())
    signed = hmac.new(
        secret.encode(),
        f"{stamp}.{payload}".encode(),
        hashlib.sha256,
    ).hexdigest()
    header = f"t={stamp},v1={signed}"
    transport = ASGITransport(app=app)
    with patch("app.routes.billing.settings") as s:
        s.stripe_webhook_secret = secret
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/billing/webhook",
                content=payload,
                headers={"stripe-signature": header, "content-type": "application/json"},
            )
    assert resp.status_code == 200, resp.text
    parsed = stripe.Webhook.construct_event(payload, header, secret)
    assert parsed["type"] == "checkout.session.completed"
    args = mock_db.execute.await_args.args
    assert args[1] == "starter"
    assert args[2] == "cus_workspace"


@pytest.mark.asyncio
async def test_checkout_refuses_a_placeholder_price(mock_app):
    app, _, _ = mock_app
    cookie = issue_jwt("00000000-0000-0000-0000-00000000a001", "local@localhost")
    transport = ASGITransport(app=app)
    with patch("app.routes.billing.settings") as s, patch(
        "app.routes.billing.stripe.checkout.Session.create"
    ) as create:
        s.stripe_api_key = "sk_test_x"
        s.app_base_url = "http://localhost:3000"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("acg_session", cookie)
            resp = await client.post("/v1/billing/checkout", json={"plan": "starter"})
    assert resp.status_code == 503
    create.assert_not_called()


@pytest.mark.asyncio
async def test_slack_alert_links_the_customer_uuid():
    from app.services.alerts import send_alert

    customer_id = "968a6a71-e456-40f6-ba15-70585002b171"
    data = {
        "id": "anom-1",
        "z_score": 4,
        "multiplier": 3.5,
        "mean_usd": 0.2,
        "display_name": "Harbor Clinic",
        "external_id": "harbor_clinic",
        "customer_id": customer_id,
        "workflow_id": "intake",
        "total_usd": 1.25,
        "event_id": "evt-1",
        "slack_webhook_url": "https://hooks.slack.com/services/T/B/xxx",
        "alert_email": None,
    }
    db = AsyncMock()
    db.fetchrow = AsyncMock(return_value=data)
    db.execute = AsyncMock()
    posted = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            posted["url"] = url
            posted["json"] = json
            return FakeResp()

    with patch("app.services.alerts.settings") as s, patch(
        "app.services.alerts.httpx.AsyncClient", FakeClient
    ):
        s.app_base_url = "http://localhost:3000"
        s.resend_api_key = ""
        await send_alert(db, "anom-1")

    body = posted["json"]
    assert body["text"].startswith("⚠️ Cost spike: Harbor Clinic")
    assert body["blocks"][0]["type"] == "section"
    button = body["blocks"][2]["elements"][0]
    assert button["url"] == f"http://localhost:3000/customers/{customer_id}?event=evt-1"
    assert "harbor_clinic" not in button["url"]
    assert len(body["blocks"][1]["fields"]) <= 10


@pytest.mark.asyncio
async def test_resend_failure_does_not_claim_the_code_was_sent(mock_app):
    app, _, mock_redis = mock_app
    mock_redis.setex = AsyncMock()
    transport = ASGITransport(app=app)
    with patch("app.routes.auth.settings") as s, patch(
        "app.routes.auth.resend.Emails.send", side_effect=RuntimeError("invalid from address")
    ):
        s.resend_api_key = "re_test"
        s.alert_from_email = "alerts@agentcogs.dev"
        s.environment = "production"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/v1/auth/request", json={"email": "ops@harbor.example"})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_selfhost_import_accepts_more_than_five_customers(mock_app):
    app, mock_db, _ = mock_app
    cookie = issue_jwt("00000000-0000-0000-0000-00000000a001", "local@localhost")
    customers = [
        {"external_id": f"clinic_{i}", "display_name": f"Clinic {i}", "monthly_revenue_usd": 100}
        for i in range(6)
    ]
    transport = ASGITransport(app=app)
    with patch("app.routes.customers.settings") as s:
        s.environment = "selfhost"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("acg_session", cookie)
            resp = await client.post("/v1/customers/import", json={"customers": customers})
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 6
    assert mock_db.fetch.await_count == 0


@pytest.mark.asyncio
async def test_saved_slack_webhook_receives_the_test_message(mock_app):
    app, mock_db, _ = mock_app
    cookie = issue_jwt("00000000-0000-0000-0000-00000000a001", "local@localhost")
    posted = {}

    async def fetchrow(sql, *args):
        if sql.strip().startswith("SELECT slack_webhook_url FROM"):
            return {"slack_webhook_url": "https://hooks.slack.com/services/T/B/saved"}
        from conftest import _default_fetchrow
        return _default_fetchrow(sql, *args)

    mock_db.fetchrow = AsyncMock(side_effect=fetchrow)

    class FakeResp:
        status_code = 200
        text = "ok"

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            posted["url"] = url
            posted["json"] = json
            return FakeResp()

    transport = ASGITransport(app=app)
    with patch("app.routes.alerts.httpx.AsyncClient", FakeClient):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("acg_session", cookie)
            resp = await client.post("/v1/alerts/test")
    assert resp.status_code == 200, resp.text
    assert posted["url"] == "https://hooks.slack.com/services/T/B/saved"
    assert posted["json"]["blocks"][2]["elements"][0]["url"].endswith("/settings")


@pytest.mark.asyncio
async def test_ingest_rejects_a_run_id_that_is_not_a_uuid(mock_app):
    app, _, _ = mock_app
    transport = ASGITransport(app=app)
    body = {
        "run_id": "run_not_a_uuid",
        "customer_id": "harbor_clinic",
        "ts": int(time.time()),
        "status": "completed",
        "total_usd": 0.01,
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/ingest",
            json=body,
            headers={"Authorization": "Bearer acg_live_TESTKEY"},
        )
    assert resp.status_code == 422
