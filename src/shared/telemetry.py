"""Best-effort OpenTelemetry → Azure Monitor wiring for lab entrypoints.

Calling `configure_telemetry("noclar-orchestrator")` once at process
startup ships every outgoing HTTP call (Foundry agent SDK, httpx
Function-tool calls) and any manual spans to the App Insights instance
identified by `APPLICATIONINSIGHTS_CONNECTION_STRING`. Because the same
App Insights resource is wired to the Function App **and** the Foundry
project, the orchestrator span, the Foundry agent spans, and the
Function request spans all share one `operation_Id` and stitch into a
single end-to-end transaction in App Insights.

No-ops cleanly if the connection string is missing (local dev without
azd outputs) or if the packages are not installed.
"""

from __future__ import annotations

import logging
import os

_log = logging.getLogger(__name__)
_configured = False


def configure_telemetry(service_name: str) -> None:
    """Idempotently configure Azure Monitor + httpx OTel instrumentation."""
    global _configured
    if _configured:
        return

    conn = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn:
        _log.debug("APPLICATIONINSIGHTS_CONNECTION_STRING not set; tracing disabled.")
        return

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    except ImportError as exc:
        _log.warning("OTel packages not installed (%s); tracing disabled.", exc)
        return

    # Set OTEL_SERVICE_NAME *before* configure_azure_monitor builds the
    # default Resource — the `resource_attributes` kwarg is unreliable across
    # azure-monitor-opentelemetry versions and silently leaves cloud_RoleName
    # as "unknown_service" in App Insights. The env var path is honored by
    # the OTel SDK at Resource construction time.
    os.environ.setdefault("OTEL_SERVICE_NAME", service_name)

    configure_azure_monitor(connection_string=conn)
    HTTPXClientInstrumentor().instrument()
    _configured = True
    _log.info("Azure Monitor tracing configured for service.name=%s", service_name)
