# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Summary, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter("shashguru_requests_total", "Total number of requests by endpoint",
                        ["endpoint", "method", "status"])
REQUEST_DURATION = Summary("shashguru_request_duration_seconds", "Request duration in seconds by endpoint",
                           ["endpoint", "method"])
ACTIVE_REQUESTS = Gauge("shashguru_active_requests", "Number of active requests by endpoint", ["endpoint"])
ERROR_COUNT = Counter("shashguru_errors_total", "Total number of errors by endpoint",
                      ["endpoint", "error_type"])

LLM_TOKENS = Counter("shashguru_llm_tokens_total", "LLM tokens by provider, model and direction",
                     ["provider", "model", "direction"])
LLM_CREDITS = Counter("shashguru_credits_charged_total", "Credits charged for managed LLM calls", ["provider", "model"])
LLM_CALLS = Counter("shashguru_llm_calls_total", "LLM calls by billing mode and outcome",
                    ["billing", "status"])  # status: ok | error | aborted | payment_required

EXCLUDED = {"/metrics", "/health"}


def _endpoint(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXCLUDED:
            return await call_next(request)
        start = time.perf_counter()
        method = request.method
        # The route template is only known after routing, so the gauge uses the raw path.
        gauge_key = request.url.path
        ACTIVE_REQUESTS.labels(endpoint=gauge_key).inc()
        try:
            response = await call_next(request)
        except Exception as e:
            endpoint = _endpoint(request)
            REQUEST_COUNT.labels(endpoint=endpoint, method=method, status="500").inc()
            ERROR_COUNT.labels(endpoint=endpoint, error_type=type(e).__name__).inc()
            raise
        else:
            REQUEST_COUNT.labels(endpoint=_endpoint(request), method=method,
                                 status=str(response.status_code)).inc()
            return response
        finally:
            REQUEST_DURATION.labels(endpoint=_endpoint(request), method=method).observe(
                time.perf_counter() - start)
            ACTIVE_REQUESTS.labels(endpoint=gauge_key).dec()


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
