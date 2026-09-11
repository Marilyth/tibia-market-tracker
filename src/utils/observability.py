# telemetry.py
import logging

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter


def setup(service_name: str):
    resource = Resource.create({
        "service.name": service_name,
    })

    # Traces
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(trace_provider)

    # Metrics
    metric_provider = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(OTLPMetricExporter())
        ],
    )
    metrics.set_meter_provider(metric_provider)

    # Logs
    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter())
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(
        LoggingHandler(level=logging.INFO, logger_provider=log_provider)
    )
