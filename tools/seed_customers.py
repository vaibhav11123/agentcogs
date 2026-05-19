#!/usr/bin/env python3
"""Upsert demo customers from personas.py (single source of truth for revenue/budget)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS))

from personas import ALL_PERSONAS, DEMO_OPERATOR_EMAIL, DEMO_WORKSPACE_NAME  # noqa: E402


def _sql_literal(val: str) -> str:
    return val.replace("'", "''")


def build_sql(workspace_id: str) -> str:
    lines = [
        f"-- Demo customers for workspace {workspace_id}",
        f"UPDATE workspaces SET name = '{_sql_literal(DEMO_WORKSPACE_NAME)}', "
        f"alert_email = '{_sql_literal(DEMO_OPERATOR_EMAIL)}' "
        f"WHERE id = '{workspace_id}'::uuid;",
    ]
    for p in ALL_PERSONAS:
        budget = "NULL" if p.monthly_budget_usd is None else str(p.monthly_budget_usd)
        lines.append(
            f"INSERT INTO customers (workspace_id, external_id, display_name, "
            f"monthly_revenue_usd, monthly_budget_usd) "
            f"VALUES ('{workspace_id}'::uuid, '{_sql_literal(p.external_id)}', "
            f"'{_sql_literal(p.display_name)}', {p.monthly_revenue_usd}, {budget}) "
            f"ON CONFLICT (workspace_id, external_id) DO UPDATE SET "
            f"display_name = EXCLUDED.display_name, "
            f"monthly_revenue_usd = EXCLUDED.monthly_revenue_usd, "
            f"monthly_budget_usd = EXCLUDED.monthly_budget_usd;"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Emit SQL to seed demo customers")
    ap.add_argument("--workspace-id", required=True)
    args = ap.parse_args()
    sys.stdout.write(build_sql(args.workspace_id))


if __name__ == "__main__":
    main()
