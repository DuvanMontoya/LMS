from __future__ import annotations

import uuid

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView


class FailingApiView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        del request
        raise RuntimeError("sensitive database implementation detail")


def test_unexpected_api_error_is_always_structured_json() -> None:
    request_id = uuid.uuid4()
    request = APIRequestFactory().get("/api/v1/failing/")
    request.request_id = request_id

    response = FailingApiView.as_view()(request)
    response.render()

    assert response.status_code == 500
    assert response.data == {
        "code": "internal_error",
        "detail": "No fue posible completar la operación.",
        "request_id": str(request_id),
    }
    assert response["Content-Type"].startswith("application/json")
    assert b"sensitive database implementation detail" not in response.content
