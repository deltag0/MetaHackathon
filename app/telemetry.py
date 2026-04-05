"""OpenTelemetry metrics instrumentation for the Flask app.

Exports the four Golden Signals to an OTel Collector via OTLP/HTTP:
  - Latency:    http_request_duration_seconds (histogram)
  - Traffic:    http_requests_total (counter)
  - Errors:     http_errors_total (counter)
  - Saturation: http_requests_in_flight (gauge)
"""

import os
import time

from flask import Flask, g, request
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter


def init_telemetry(app: Flask) -> None:
    """Set up OTel metrics and register before/after request hooks."""

    otel_endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel:4318"
    )

    instance_name = os.environ.get("LOG_FILE_PATH", "app")
    # Extract instance identifier like "app-1" from "/app/logs/app-1.log"
    instance_name = instance_name.rsplit("/", 1)[-1].replace(".log", "")

    resource = Resource.create({
        "service.name": "url-shortener-api",
        "service.instance.id": instance_name,
    })

    exporter = OTLPMetricExporter(
        endpoint=f"{otel_endpoint}/v1/metrics",
    )

    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=10_000,
    )

    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter("url-shortener-api", "1.0.0")

    # ── Golden Signal metrics ─────────────────────────────────────────

    # Latency
    request_duration = meter.create_histogram(
        name="http_request_duration_seconds",
        description="HTTP request latency in seconds",
        unit="s",
    )

    # Traffic
    request_counter = meter.create_counter(
        name="http_requests_total",
        description="Total HTTP requests",
    )

    # Errors
    error_counter = meter.create_counter(
        name="http_errors_total",
        description="Total HTTP error responses (4xx and 5xx)",
    )

    # Saturation
    in_flight_gauge = meter.create_up_down_counter(
        name="http_requests_in_flight",
        description="Number of HTTP requests currently being processed",
    )

    @app.before_request
    def _otel_before():
        g.otel_start = time.perf_counter()
        in_flight_gauge.add(1, {"instance": instance_name})

    @app.after_request
    def _otel_after(response):
        start = getattr(g, "otel_start", None)
        duration = time.perf_counter() - start if start else 0

        route = request.url_rule.rule if request.url_rule else "unknown"
        method = request.method
        status = str(response.status_code)

        attrs = {
            "http_method": method,
            "http_route": route,
            "http_status_code": status,
            "app_instance": instance_name,
        }

        request_duration.record(duration, attrs)
        request_counter.add(1, attrs)

        if response.status_code >= 400:
            error_counter.add(1, attrs)

        in_flight_gauge.add(-1, {"instance": instance_name})
        return response
