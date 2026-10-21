"""Tests de navigation Streamlit avec une API isolée."""

import importlib
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from festival.api.app import create_app


@pytest.fixture
def ui_environment(
    festival_data_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    project_root = Path(__file__).resolve().parent.parent
    monkeypatch.syspath_prepend(str(project_root))

    client_module = importlib.import_module("streamlit_app.api_client")

    data_path = tmp_path / "festival.json"
    shutil.copyfile(festival_data_path, data_path)

    application = create_app(
        data_path=data_path,
        web_root=tmp_path / "web",
    )

    with TestClient(application) as api_client:

        def local_request(
            self,
            method,
            path,
            *,
            params=None,
            body=None,
        ):
            response = api_client.request(
                method,
                path,
                params=params,
                json=body,
            )

            if response.is_error:
                raise client_module.APIError(client_module.error_message(response))

            if response.status_code == 204:
                return None

            return response.json()

        monkeypatch.setattr(
            client_module.FestivalAPI,
            "request",
            local_request,
        )

        yield project_root / "streamlit_app" / "app.py"


def test_dashboard_loads(ui_environment: Path) -> None:
    app = AppTest.from_file(
        str(ui_environment),
        default_timeout=20,
    ).run()

    assert not app.exception
    assert not app.error
    assert len(app.metric) == 4
    assert app.metric[0].value == "23"


@pytest.mark.parametrize(
    "page",
    [
        "Programme",
        "Artistes",
        "Lieux",
        "Administration",
    ],
)
def test_navigation_pages_load(
    ui_environment: Path,
    page: str,
) -> None:
    app = AppTest.from_file(
        str(ui_environment),
        default_timeout=20,
    ).run()

    app.sidebar.radio[0].set_value(page).run()

    assert not app.exception
    assert not app.error
    assert app.sidebar.radio[0].value == page


def test_programme_search(
    ui_environment: Path,
) -> None:
    app = AppTest.from_file(
        str(ui_environment),
        default_timeout=20,
    ).run()

    app.sidebar.radio[0].set_value("Programme").run()
    app.text_input[0].set_value("After Hours").run()

    assert not app.exception
    assert not app.error
    assert any("1 représentation(s)" in caption.value for caption in app.caption)


def test_api_failure_is_displayed(
    ui_environment: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_module = importlib.import_module("streamlit_app.api_client")

    def fail_request(self, *args, **kwargs):
        raise client_module.APIError("API de test indisponible.")

    monkeypatch.setattr(
        client_module.FestivalAPI,
        "request",
        fail_request,
    )

    app = AppTest.from_file(
        str(ui_environment),
        default_timeout=20,
    ).run()

    assert not app.exception
    assert app.error[0].value == "API de test indisponible."
