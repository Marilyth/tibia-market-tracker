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


_STANDARD_LOG_RECORD_ATTRS = frozenset(
    vars(logging.LogRecord(name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None))
)


class HomogeneousLogAttributes(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in vars(record).items():
            if key in _STANDARD_LOG_RECORD_ATTRS:
                continue
        
            # mitmproxy causes mixed type warnings to pop up all the time.
            # Make them all string.
            if isinstance(value, (list, tuple)) and value:
                element_types = {type(element) for element in value if element is not None}
                if len(element_types) > 1:
                    record.__dict__[key] = str(value)

        return True


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

    log_handler = LoggingHandler(level=logging.INFO, logger_provider=log_provider)
    log_handler.addFilter(HomogeneousLogAttributes())
    root_logger.addHandler(log_handler)
