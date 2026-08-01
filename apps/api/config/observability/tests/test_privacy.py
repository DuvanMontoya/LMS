from __future__ import annotations

import io
import json
import uuid
from contextlib import redirect_stdout

import structlog
from django.test import SimpleTestCase

from config.observability.context import bind_context, current_context, reset_context
from config.observability.logging import REDACTED, configure_structured_logging, redact
from config.observability.metrics import safe_attributes
from config.observability.sentry import before_send


class TelemetryPrivacyTests(SimpleTestCase):
    def test_recursive_redaction_and_sentry_request_minimization(self) -> None:
        event = {
            "request": {
                "url": "https://lms.test/buscar?q=private",
                "query_string": "q=private",
                "cookies": {"sessionid": "secret"},
                "data": {"grading_payload": "answer-key"},
                "headers": {"authorization": "Bearer secret"},
            },
            "user": {"id": str(uuid.uuid4()), "email": "person@example.test"},
            "extra": {
                "nested": {"password": "secret", "query": "private"},
                "signed": "https://s3.test/key?X-Amz-Signature=secret",
            },
        }
        cleaned = before_send(event, {})
        assert cleaned is not None
        serialized = json.dumps(cleaned)
        self.assertNotIn("private", serialized)
        self.assertNotIn("answer-key", serialized)
        self.assertNotIn("person@example.test", serialized)
        self.assertNotIn("X-Amz-Signature", serialized)
        self.assertEqual(cleaned["request"]["url"], "https://lms.test/buscar")
        self.assertEqual(cleaned["user"]["id"], event["user"]["id"])

    def test_json_log_context_and_cleanup(self) -> None:
        request_id = uuid.uuid4()
        tokens = bind_context(request_id=request_id, task_id=uuid.uuid4())
        stream = io.StringIO()
        configure_structured_logging(environment="test")
        with redirect_stdout(stream):
            structlog.get_logger("privacy-test").info(
                "safe_event",
                nested={"password": "secret", "email": "person@example.test"},
            )
        reset_context(tokens)
        rendered = json.loads(stream.getvalue())
        self.assertEqual(rendered["request_id"], str(request_id))
        self.assertEqual(rendered["nested"]["password"], REDACTED)
        self.assertEqual(rendered["nested"]["email"], REDACTED)
        self.assertEqual(current_context(), {})

    def test_metric_labels_are_strictly_allowlisted(self) -> None:
        for forbidden in (
            "user_id",
            "organization_id",
            "course_id",
            "query",
            "event_id",
            "job_id",
        ):
            with self.assertRaises(ValueError):
                safe_attributes({forbidden: "many-values"})
        self.assertEqual(
            safe_attributes({"outcome": "completed", "queue": "events"}),
            {"outcome": "completed", "queue": "events"},
        )

    def test_redact_handles_nested_values_and_presigned_urls(self) -> None:
        value = redact(
            {
                "payload": {"answer": "forbidden"},
                "note": "person@example.test",
                "url": "https://s3.test/key?x-amz-signature=secret",
            }
        )
        self.assertEqual(value["payload"], REDACTED)
        self.assertEqual(value["note"], REDACTED)
        self.assertEqual(value["url"], "https://s3.test/key")
