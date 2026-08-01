from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase
from opentelemetry import propagate, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from config.observability.tracing import domain_span


class TracingTests(SimpleTestCase):
    def test_domain_span_uses_in_memory_exporter_without_sensitive_attributes(
        self,
    ) -> None:
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        with patch(
            "config.observability.tracing.trace.get_tracer",
            return_value=provider.get_tracer("test"),
        ):
            with domain_span(
                "discovery.search",
                {"source_type": "course_unit", "query": "private"},
            ):
                pass
        span = exporter.get_finished_spans()[0]
        self.assertEqual(span.name, "discovery.search")
        self.assertEqual(span.attributes["source_type"], "course_unit")
        self.assertNotIn("query", span.attributes)

    def test_w3c_trace_context_round_trip(self) -> None:
        span_context = SpanContext(
            trace_id=0x0AF7651916CD43DD8448EB211C80319C,
            span_id=0xB7AD6B7169203331,
            is_remote=False,
            trace_flags=TraceFlags(1),
        )
        context = trace.set_span_in_context(NonRecordingSpan(span_context))
        carrier: dict[str, str] = {}
        propagate.inject(carrier, context=context)
        extracted = trace.get_current_span(
            propagate.extract(carrier)
        ).get_span_context()
        self.assertEqual(extracted.trace_id, span_context.trace_id)
        self.assertEqual(extracted.span_id, span_context.span_id)
