"""Tests du client HTTP, sans serveur réel."""

import importlib
from pathlib import Path

import httpx
import pytest


@pytest.fixture
def client_module(monkeypatch: pytest.MonkeyPatch):
    project_root = Path(__file__).resolve().parent.parent
    monkeypatch.syspath_prepend(str(project_root))

    return importlib.import_module("streamlit_app.api_client")


def test_successful_response(client_module) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"name": "Festival test"},
        )

    api = client_module.FestivalAPI(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    assert api.get("/api/festival") == {"name": "Festival test"}


def test_business_error(client_module) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"detail": "Cet atelier est complet."},
        )

    api = client_module.FestivalAPI(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        client_module.APIError,
        match="Cet atelier est complet",
    ):
        api.post(
            "/api/performances/test/participants",
            {"name": "Malik"},
        )


def test_validation_error_list(client_module) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={
                "detail": [
                    {
                        "loc": ["body", "name"],
                        "msg": "Field required",
                    }
                ]
            },
        )

    api = client_module.FestivalAPI(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        client_module.APIError,
        match="name : Field required",
    ):
        api.post("/api/artists", {})


def test_delete_without_response_body(client_module) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    api = client_module.FestivalAPI(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    assert api.delete("/api/performances/test") is None


def test_unreachable_server(client_module) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Connexion refusée",
            request=request,
        )

    api = client_module.FestivalAPI(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        client_module.APIError,
        match="Impossible de joindre FastAPI",
    ):
        api.get("/api/festival")
