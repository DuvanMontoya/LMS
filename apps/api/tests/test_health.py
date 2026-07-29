from __future__ import annotations

from unittest.mock import patch

from django.db import DatabaseError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext


class HealthEndpointTests(TestCase):
    @patch("config.health.checks.connection.cursor", side_effect=DatabaseError)
    def test_database_check_handles_connection_failures(self, _: object) -> None:
        from config.health.checks import is_database_ready

        self.assertFalse(is_database_ready())

    def test_liveness_is_database_independent_and_cache_safe(self) -> None:
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(len(queries), 0)
        self.assertNotIn("sessionid", response.cookies)

    def test_liveness_head_and_method_rejection(self) -> None:
        head = self.client.head("/health/live/")
        post = self.client.post("/health/live/")

        self.assertEqual(head.status_code, 200)
        self.assertEqual(head.content, b"")
        self.assertEqual(post.status_code, 405)
        self.assertEqual(post["Cache-Control"], "no-store")

    def test_readiness_checks_postgresql_and_is_cache_safe(self) -> None:
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(len(queries), 1)
        self.assertNotIn("sessionid", response.cookies)

    def test_readiness_head_and_method_rejection(self) -> None:
        self.assertEqual(self.client.head("/health/ready/").status_code, 200)
        self.assertEqual(self.client.post("/health/ready/").status_code, 405)

    @patch("config.health.views.is_database_ready", return_value=False)
    def test_readiness_returns_safe_503_when_database_is_unavailable(
        self, _: object
    ) -> None:
        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "unavailable"})
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotIn("exception", response.content.decode())

    @patch("config.health.views.is_cache_ready", return_value=False)
    def test_readiness_returns_safe_503_when_redis_is_unavailable(
        self, _: object
    ) -> None:
        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(response.content, {"status": "unavailable"})
        self.assertNotIn("redis", response.content.decode().lower())
