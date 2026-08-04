from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase


class OpenApiDocumentationTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="openapi-docs@example.test",
            password="test-only-documentation-password",
        )

    def test_interactive_openapi_routes_require_a_session(self) -> None:
        for path in ("/api/v1/schema/", "/api/v1/docs/", "/api/v1/redoc/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_authenticated_user_can_load_schema_swagger_and_redoc(self) -> None:
        self.client.force_login(self.user)

        schema = self.client.get("/api/v1/schema/")
        swagger = self.client.get("/api/v1/docs/")
        redoc = self.client.get("/api/v1/redoc/")

        self.assertEqual(schema.status_code, 200)
        self.assertIn(b"openapi", schema.content.lower())
        self.assertEqual(swagger.status_code, 200)
        self.assertIn(b"swagger-ui", swagger.content.lower())
        self.assertEqual(redoc.status_code, 200)
        self.assertIn(b"redoc", redoc.content.lower())
