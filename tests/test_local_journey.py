"""Local journey: one machine, no model call, enforcement off unless turned on."""

import json
from datetime import date
from urllib.request import urlopen

import pytest

from agentcogs.assistant import handle
from agentcogs.cli import main
from agentcogs.errors import ConfigurationError
from agentcogs.instrument import customer, instrument
from agentcogs.localhttp import make_server
from agentcogs.localstore import (
    add_month,
    add_residual,
    connect,
    doctor,
    init_home,
    prepare_migration,
    read_credits,
    record_event,
    render_balance_html,
    render_dashboard,
    set_credits,
    set_enforce,
    set_subscription,
    subscription_margin,
    verify_fixture,
)
from agentcogs.reports import (
    concentration,
    credit_balance,
    plan_margin,
    recommended_budget_micro,
    regression_comment,
    unattributed_share,
    warning_micro,
)


def test_init_prices_the_fixture_and_refuses_to_overwrite(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGENTCOGS_HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["agentcogs", "init"])
    main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["events"] == 1
    assert payload["incurred_micro"] == 24600
    assert payload["budget_enforce"] is False

    monkeypatch.setattr("sys.argv", ["agentcogs", "init"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2

    monkeypatch.setattr("sys.argv", ["agentcogs", "init", "--yes"])
    main()
    again = json.loads(capsys.readouterr().out)
    assert again["events"] == 1
    assert doctor(tmp_path) == []


def test_doctor_and_demo_show_the_priced_customer(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGENTCOGS_HOME", str(tmp_path))
    init_home(tmp_path)
    verify_fixture(tmp_path)
    monkeypatch.setattr("sys.argv", ["agentcogs", "doctor"])
    main()
    assert capsys.readouterr().out.strip() == "ok"
    page = render_dashboard(tmp_path)
    assert "customer_001" in page
    assert "$0.0246" in page
    assert "false" in page


def test_dashboard_serves_the_fixture_on_loopback(tmp_path):
    init_home(tmp_path)
    verify_fixture(tmp_path)
    server = make_server(tmp_path, 0)
    port = server.server_address[1]
    import threading

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{port}/") as response:
            body = response.read().decode("utf-8")
        assert response.status == 200
        assert "$0.0246" in body
    finally:
        server.shutdown()


def test_unknown_model_is_flagged_and_stores_nothing(tmp_path):
    init_home(tmp_path)
    conn = connect(tmp_path)
    with pytest.raises(ValueError, match="UNKNOWN_MODEL"):
        record_event(
            conn,
            run_id="mystery",
            customer_id="customer_001",
            provider="OpenAI",
            workflow="other",
            model="made-up-model",
            case={"calls": [{"call_id": "c", "lanes": {"uncached_input": 10}}], "segments": []},
        )
    assert conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM model_flags").fetchone()["n"] == 1
    conn.close()


def test_changed_bill_is_rejected_and_enforce_stays_off(tmp_path):
    init_home(tmp_path)
    verify_fixture(tmp_path)
    conn = connect(tmp_path)
    with pytest.raises(ValueError, match="PAYLOAD_MISMATCH"):
        record_event(
            conn,
            run_id="fixture-document-analysis",
            customer_id="customer_001",
            provider="OpenAI",
            workflow="Document analysis",
            model="gpt-4o-mini",
            case={"calls": [{"call_id": "c", "lanes": {"uncached_input": 9000}}], "segments": []},
        )
    record_event(
        conn,
        run_id="second",
        customer_id="customer_001",
        provider="OpenAI",
        workflow="Document analysis",
        model="gpt-4o-mini",
        case={"calls": [{"call_id": "c", "lanes": {"uncached_input": 1000}}], "segments": []},
        budget_micro=1,
    )
    assert conn.execute("SELECT COUNT(*) AS n FROM audits").fetchone()["n"] == 1
    assert conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"] == 2
    set_enforce(conn, True)
    with pytest.raises(ValueError, match="BUDGET_EXCEEDED"):
        record_event(
            conn,
            run_id="third",
            customer_id="customer_001",
            provider="OpenAI",
            workflow="Document analysis",
            model="gpt-4o-mini",
            case={"calls": [{"call_id": "c", "lanes": {"uncached_input": 1000}}], "segments": []},
            budget_micro=1,
        )
    assert conn.execute("SELECT COUNT(*) AS n FROM events WHERE run_id='third'").fetchone()["n"] == 0
    conn.close()


def test_customer_context_is_required_and_does_not_read_a_prompt():
    seen = {}

    def call(prompt):
        seen["prompt"] = prompt
        return "ok"

    wrapped = instrument(call)
    with pytest.raises(ConfigurationError):
        wrapped("secret prompt")
    with customer("customer_001"):
        assert wrapped("secret prompt") == "ok"
    assert seen["prompt"] == "secret prompt"
    assert instrument()["prompts"] is False


def test_health_cards_hide_until_the_book_can_fill_them():
    assert concentration({"a": 10, "b": 20}) is None
    share = concentration({"a": 38, "b": 10, "c": 10, "d": 10, "e": 10, "f": 22})
    assert share is not None
    assert share["customers"][0] == "a"
    assert share["held_micro"] == 38 + 22 + 10 + 10 + 10
    assert unattributed_share(
        [{"day": "2026-11-25", "provider_micro": 100, "ledger_micro": 90}],
        date(2026, 11, 25),
    ) is None
    assert unattributed_share(
        [{"day": "2026-11-20", "provider_micro": 1000, "ledger_micro": 972}],
        date(2026, 11, 25),
    ) == pytest.approx(0.028)


def test_missing_fee_leaves_margin_blank_and_budget_matches_the_formula(tmp_path):
    assert plan_margin(None, 100) is None
    assert plan_margin(0, 100) is None
    assert plan_margin(3_800_000_000, 3_040_000_000) == pytest.approx(0.20)
    assert recommended_budget_micro(49_000_000, 70) == 14_700_000
    assert warning_micro(14_700_000) == 11_760_000
    init_home(tmp_path)
    conn = connect(tmp_path)
    set_subscription(conn, "customer_001", plan="Pro", fee_micro=None, stripe_customer_id=None)
    blank = subscription_margin(conn, "customer_001")
    assert blank["margin"] is None
    assert blank["needs_mapping"] is True
    set_subscription(conn, "customer_001", plan="Pro", fee_micro=49_000_000, stripe_customer_id="cus_123")
    filled = subscription_margin(conn, "customer_001")
    assert filled["needs_mapping"] is False
    assert filled["margin"] == pytest.approx(1.0)
    conn.close()


def test_regression_comment_is_the_fixture_increase():
    text = regression_comment(31_000, 48_000, 310_000_000, "Increased input context length")
    assert "54.8%" in text
    assert "$480" in text
    assert "$0.031" in text
    assert "$0.048" in text
    assert "comment" in text
    assert "Increased input context length" in text


def test_embed_balance_matches_the_script():
    categories = {"Research assistant": 3200, "Document analysis": 2100, "Chat assistant": 980}
    balance = credit_balance(10_000, categories)
    assert balance["used"] == 6280
    assert balance["remaining"] == 3720
    html = render_balance_html(balance)
    assert "6280 / 10000" in html
    assert "3720" in html


def test_embed_route_reads_the_stored_balance(tmp_path):
    init_home(tmp_path)
    conn = connect(tmp_path)
    set_credits(
        conn,
        "customer_001",
        10_000,
        {"Research assistant": 3200, "Document analysis": 2100, "Chat assistant": 980},
    )
    conn.close()
    server = make_server(tmp_path, 0)
    import threading

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_address[1]}/embed/balance?customer=customer_001") as response:
            body = response.read().decode("utf-8")
        assert "3720" in body
    finally:
        server.shutdown()
    assert read_credits(connect(tmp_path), "customer_001")["used"] == 6280


def test_assistant_reads_two_months_and_refuses_writes(tmp_path):
    init_home(tmp_path)
    conn = connect(tmp_path)
    add_month(conn, {"month": "2026-10", "revenue_micro": 12_500_000_000, "ai_micro": 3_250_000_000})
    add_month(
        conn,
        {
            "month": "2026-11",
            "revenue_micro": 12_500_000_000,
            "ai_micro": 4_250_000_000,
            "retry_micro": 420_000_000,
            "pro_usage_micro": 310_000_000,
            "model_change_micro": 180_000_000,
        },
    )
    listed = handle(conn, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert names == ["margin_change"]
    reply = handle(conn, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "margin_change"}})
    assert "74%" in reply["result"]["text"]
    assert "66%" in reply["result"]["text"]
    assert "most of the change" in reply["result"]["text"]
    denied = handle(conn, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "set_budget"}})
    assert denied["error"]["message"] == "WRITE_NOT_ENABLED"
    conn.close()


def test_backup_runs_before_a_migration_and_export_round_trips(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGENTCOGS_HOME", str(tmp_path))
    init_home(tmp_path)
    verify_fixture(tmp_path)
    dest = prepare_migration(tmp_path)
    assert dest.exists()
    monkeypatch.setattr("sys.argv", ["agentcogs", "export"])
    main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["events"][0]["incurred_micro"] == 24600
    assert payload["events"][0]["customer_id"] == "customer_001"


def _clear_sdk(monkeypatch) -> None:
    monkeypatch.delenv("AGENTCOGS_API_KEY", raising=False)
    monkeypatch.delenv("AGENTCOGS_ENDPOINT", raising=False)
    monkeypatch.delenv("AGENTCOGS_WORKSPACE_ID", raising=False)
    from agentcogs.config import _config

    _config.api_key = None
    _config.offline = False
    _config.workspace_id = None
    _config.endpoint = "http://localhost:8000"


def test_own_call_is_stored_in_the_local_ledger(tmp_path, monkeypatch):
    import sys
    import threading
    from pathlib import Path

    from openai import OpenAI

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from mimic_providers import OPENAI_USAGE, ProviderMimic

    import agentcogs
    from agentcogs._shekel_compat import lanes_from_usage
    from agentcogs.kernel.attribute import price_call
    from agentcogs.localstore import export_json, price_book

    _clear_sdk(monkeypatch)
    monkeypatch.setenv("AGENTCOGS_HOME", str(tmp_path))
    init_home(tmp_path)
    verify_fixture(tmp_path)
    server = ProviderMimic()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with agentcogs.run(customer_id="acme", workflow_id="support"):
            OpenAI(api_key="sk-mimic", base_url=f"{server.origin}/v1").chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
            )
        payload = export_json(tmp_path)
        customers = {row["customer_id"] for row in payload["events"]}
        assert customers == {"customer_001", "acme"}
        acme = next(row for row in payload["events"] if row["customer_id"] == "acme")
        expected = price_call(lanes_from_usage("openai", OPENAI_USAGE), price_book())[1]
        assert acme["incurred_micro"] == expected
        assert acme["workflow"] == "support"
        assert acme["model"] == "gpt-4o-mini"
        assert payload["status"]["budget_enforce"] is False
        assert payload["status"]["events"] == 2
    finally:
        server.shutdown()
        _clear_sdk(monkeypatch)


def test_remote_key_does_not_write_the_local_ledger(tmp_path, monkeypatch):
    import sys
    import threading
    from pathlib import Path

    from openai import OpenAI

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from mimic_providers import ProviderMimic

    import agentcogs
    from agentcogs.localstore import export_json

    monkeypatch.setenv("AGENTCOGS_HOME", str(tmp_path))
    init_home(tmp_path)
    verify_fixture(tmp_path)
    server = ProviderMimic()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    agentcogs.init(
        api_key="acg_live_MIMIC",
        workspace_id="ws_mimic",
        endpoint=server.origin,
        register_atexit=False,
    )
    try:
        with agentcogs.run(customer_id="acme", workflow_id="support"):
            OpenAI(api_key="sk-mimic", base_url=f"{server.origin}/v1").chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=8,
            )
        payload = export_json(tmp_path)
        assert [row["customer_id"] for row in payload["events"]] == ["customer_001"]
    finally:
        server.shutdown()
        agentcogs.shutdown()
        _clear_sdk(monkeypatch)


def test_closed_residual_feeds_the_health_row(tmp_path):
    init_home(tmp_path)
    conn = connect(tmp_path)
    add_residual(conn, "2026-11-20", 1000, 972)
    from agentcogs.localstore import health

    report = health(conn, date(2026, 11, 25))
    assert report["unattributed_share"] == pytest.approx(0.028)
    assert report["concentration"] is None
    conn.close()
