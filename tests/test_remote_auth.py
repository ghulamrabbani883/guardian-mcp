from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.remote.server import BearerTokenMiddleware


def create_app():
    async def endpoint(request):
        return PlainTextResponse("ok")

    return Starlette(
        routes=[Route("/mcp", endpoint, methods=["POST"])],
        middleware=[
            Middleware(
                BearerTokenMiddleware,
                bearer_token="0123456789abcdef",
            )
        ],
    )


def test_remote_gateway_rejects_missing_bearer_token():
    with TestClient(create_app()) as client:
        response = client.post("/mcp")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_remote_gateway_accepts_valid_bearer_token():
    with TestClient(create_app()) as client:
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer 0123456789abcdef"},
        )

    assert response.status_code == 200
    assert response.text == "ok"
