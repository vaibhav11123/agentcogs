"""LangGraph helper — set tenant from configurable and wrap run()."""
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from ..budget import RunContext, run


@contextmanager
def agentcogs_run(
    config: Optional[dict] = None,
    *,
    customer_id: Optional[str] = None,
    workflow_id: str = "default",
    workspace_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Iterator[RunContext]:
    """Context manager for LangGraph invoke blocks.

    Reads tenant_id from config[\"configurable\"][\"tenant_id\"] when customer_id omitted.

    Example:
        with agentcogs_run(config, workflow_id=\"research_agent\") as ctx:
            result = graph.invoke(state, config)
    """
    cfg = config or {}
    configurable = cfg.get("configurable") or {}
    tenant = (
        customer_id
        or configurable.get("tenant_id")
        or configurable.get("customer_id")
    )
    with run(
        customer_id=str(tenant) if tenant else None,
        workflow_id=workflow_id,
        workspace_id=workspace_id,
        metadata=metadata,
    ) as ctx:
        yield ctx
