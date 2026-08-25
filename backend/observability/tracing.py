"""
AgentOS — Distributed Tracing Configuration

Configures OpenTelemetry for W3C Trace Context propagation across the agentic workflow.
"""

import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

_initialized = False

def init_tracing(app_name: str = "AgentOS"):
    """Initialize OpenTelemetry tracing with W3C Trace Context."""
    global _initialized
    if _initialized:
        return

    provider = TracerProvider()
    
    # We output to console for local, Jaeger or GCP Trace for cloud
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Enable W3C Trace Context
    set_global_textmap(TraceContextTextMapPropagator())
    
    _initialized = True
    logger.info("Distributed Tracing Initialized (W3C Trace Context)")

def get_tracer(name: str):
    """Get a tracer instance for the current module."""
    if not _initialized:
        init_tracing()
    return trace.get_tracer(name)
