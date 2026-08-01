from typing import Protocol, cast

from django.core.management.base import BaseCommand, CommandError
from opentelemetry import metrics, trace

from config.observability.telemetry import initialize_telemetry


class Flushable(Protocol):
    def force_flush(self, timeout_millis: int = 30_000) -> bool: ...


class Command(BaseCommand):
    help = "Emite una traza y métrica OTLP sintéticas sin datos de usuario."

    def handle(self, *args: object, **options: object) -> None:
        initialize_telemetry()
        tracer = trace.get_tracer("lms.observability.smoke")
        with tracer.start_as_current_span("lms.observability.smoke") as span:
            span.set_attribute("smoke.outcome", "pass")
        counter = metrics.get_meter("lms.observability.smoke").create_counter(
            "lms_observability_smoke"
        )
        counter.add(1, {"outcome": "pass"})
        trace_provider = trace.get_tracer_provider()
        meter_provider = metrics.get_meter_provider()
        trace_ok = cast("Flushable", trace_provider).force_flush(timeout_millis=10_000)
        metric_ok = cast("Flushable", meter_provider).force_flush(timeout_millis=10_000)
        if trace_ok is False or metric_ok is False:
            raise CommandError("No fue posible completar el flush OTLP.")
        self.stdout.write(self.style.SUCCESS("OTLP trace and metric emitted."))
