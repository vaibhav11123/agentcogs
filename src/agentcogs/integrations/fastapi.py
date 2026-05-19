"""Starlette/FastAPI middleware — set tenant context once per request."""
from typing import Callable, Optional, Sequence

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..context import set_customer, set_workflow


class AgentCOGSMiddleware(BaseHTTPMiddleware):
    """Populate agentcogs context from each HTTP request.

    Example:
        app.add_middleware(
            AgentCOGSMiddleware,
            customer_id=lambda req: req.state.tenant_id,
        )
    """

    def __init__(
        self,
        app,
        customer_id: Callable[[Request], Optional[str]],
        workflow_id: Optional[Callable[[Request], Optional[str]]] = None,
        exclude_paths: Sequence[str] = ("/health", "/health/ready"),
    ):
        super().__init__(app)
        self._customer_id = customer_id
        self._workflow_id = workflow_id
        self._exclude = tuple(exclude_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in self._exclude:
            return await call_next(request)
        try:
            cid = self._customer_id(request)
            set_customer(cid)
            if self._workflow_id is not None:
                set_workflow(self._workflow_id(request))
            return await call_next(request)
        finally:
            set_customer(None)
            set_workflow(None)
