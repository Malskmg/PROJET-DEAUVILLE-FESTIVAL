"""Tests HTTP sur une copie temporaire des données."""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from festival.api.app import create_app
from festival.infrastructure.json_repository import JsonFestivalRepository


@pytest.fixture
def api_data_path(
    festival_data_path: Path,
    tmp_path: Path,
) -> Path:
    path = tmp_path / "festival.json"
    shutil.copyfile(festival_data_path, path)
    return path


@pytest.fixture
def client(
    api_data_path: Path,
    tmp_path: Path,
) -> Iterator[TestClient]:
    application = create_app(
        data_path=api_data_path,
        web_root=tmp_path / "missing-web",
    )

    with TestClient(application) as test_client:
        yield test_client


def solo_body() -> dict:
    return {
        "kind": "solo",
        "title": "API Test Show",
        "venue": "la-cabane",
        "start": "2027-06-10T10:00",
        "duration_minutes": 60,
        "artist": "nora-lebrun",
        "min_age": 0,
    }


def test_festival_information(client: TestClient) -> None:
    response = client.get("/api/festival")

    assert response.status_code == 200
    assert response.json()["first_day"] == "2027-06-10"
    assert len(response.json()["days"]) == 4


def test_venues_and_artists(client: TestClient) -> None:
    venues = client.get("/api/venues")
    artists = client.get("/api/artists")

    assert venues.status_code == 200
    assert len(venues.json()) == 4
    assert venues.json()[0]["slug"] == "grand-casino"

    assert artists.status_code == 200
    assert len(artists.json()) == 12
    assert artists.json()[0]["slug"] == "elodie-marchal"


def test_artist_detail(client: TestClient) -> None:
    response = client.get("/api/artists/nora-lebrun")

    assert response.status_code == 200
    assert len(response.json()["performances"]) == 4


def test_programme_filters(client: TestClient) -> None:
    response = client.get(
        "/api/programme",
        params={
            "day": "2027-06-11",
            "venue": "le-kiosque",
        },
    )

    assert response.status_code == 200
    assert [show["title"] for show in response.json()] == [
        "Writing a Punchline",
        "Late Laughs",
        "After Hours",
    ]


def test_performance_computed_fields(client: TestClient) -> None:
    response = client.get("/api/performances/le-kiosque-2027-06-12-0100")

    assert response.status_code == 200
    data = response.json()

    assert data["festival_day"] == "2027-06-11"
    assert data["capacity"] == 120
    assert data["venue_name"] == "Le Kiosque"
    assert len(data["artists"]) == 3
    assert "end" in data
    assert "summary" in data


def test_now_and_up_next(client: TestClient) -> None:
    response = client.get(
        "/api/now",
        params={"at": "2027-06-11T21:00"},
    )

    assert response.status_code == 200
    data = response.json()

    assert [show["title"] for show in data["now_playing"]] == ["Tall Tales"]
    assert [show["title"] for show in data["up_next"]] == [
        "Straight Face",
        "Late Laughs",
        "After Hours",
    ]


def test_unknown_resource_returns_404(client: TestClient) -> None:
    response = client.get("/api/artists/inconnu")

    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_invalid_day_returns_validation_list(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/programme",
        params={"day": "June 11"},
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_empty_name_returns_business_error(client: TestClient) -> None:
    response = client.post(
        "/api/artists",
        json={"name": "   "},
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_missing_field_returns_validation_list(
    client: TestClient,
) -> None:
    response = client.post("/api/artists", json={})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_create_artist_is_saved(
    client: TestClient,
    api_data_path: Path,
) -> None:
    response = client.post(
        "/api/artists",
        json={"name": "Malik API Test"},
    )

    assert response.status_code == 201

    slug = response.json()["slug"]
    reloaded = JsonFestivalRepository(api_data_path).load()

    assert reloaded.get_artist(slug).name == "Malik API Test"


def test_duplicate_artist_returns_409(client: TestClient) -> None:
    response = client.post(
        "/api/artists",
        json={"name": "Nora Lebrun"},
    )

    assert response.status_code == 409


def test_create_move_and_delete_performance(
    client: TestClient,
    api_data_path: Path,
) -> None:
    body = solo_body()

    created = client.post("/api/performances", json=body)
    assert created.status_code == 201
    old_id = created.json()["id"]

    body["start"] = "2027-06-10T12:00"

    moved = client.put(
        f"/api/performances/{old_id}",
        json=body,
    )

    assert moved.status_code == 200
    new_id = moved.json()["id"]
    assert new_id != old_id

    assert client.get(f"/api/performances/{old_id}").status_code == 404

    reloaded = JsonFestivalRepository(api_data_path).load()
    assert reloaded.get_performance(new_id).title == "API Test Show"

    deleted = client.delete(f"/api/performances/{new_id}")

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"/api/performances/{new_id}").status_code == 404


def test_failed_move_changes_nothing(
    client: TestClient,
    api_data_path: Path,
) -> None:
    body = solo_body()
    created = client.post("/api/performances", json=body)
    assert created.status_code == 201
    performance_id = created.json()["id"]

    before = api_data_path.read_bytes()

    body["venue"] = "grand-casino"
    body["start"] = "2027-06-10T20:30"

    response = client.put(
        f"/api/performances/{performance_id}",
        json=body,
    )

    assert response.status_code == 409
    assert api_data_path.read_bytes() == before

    unchanged = client.get(f"/api/performances/{performance_id}")
    assert unchanged.json()["venue"] == "la-cabane"


def test_workshop_registration(client: TestClient) -> None:
    workshop_id = "la-cabane-2027-06-11-1030"

    response = client.post(
        f"/api/performances/{workshop_id}/participants",
        json={"name": "Malik API Test"},
    )

    assert response.status_code == 201
    assert "Malik API Test" in response.json()["participants"]
    assert response.json()["places_left"] == 8

    duplicate = client.post(
        f"/api/performances/{workshop_id}/participants",
        json={"name": "malik api test"},
    )

    assert duplicate.status_code == 409


def test_non_workshop_registration_returns_422(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/performances/theatre-des-planches-2027-06-10-2100/participants",
        json={"name": "Malik"},
    )

    assert response.status_code == 422


def test_unknown_venue_on_creation_returns_404(
    client: TestClient,
) -> None:
    body = solo_body()
    body["venue"] = "lieu-inconnu"

    response = client.post("/api/performances", json=body)

    assert response.status_code == 404


def test_missing_data_returns_500(tmp_path: Path) -> None:
    application = create_app(
        data_path=tmp_path / "missing.json",
        web_root=tmp_path / "web",
    )

    with TestClient(application) as test_client:
        response = test_client.get("/api/festival")

    assert response.status_code == 500
    assert isinstance(response.json()["detail"], str)


def test_home_and_docs_are_available(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200


def test_static_interfaces_are_served(
    api_data_path: Path,
    tmp_path: Path,
) -> None:
    web_root = tmp_path / "web"

    for folder, title in [
        ("public", "Site public test"),
        ("admin", "Administration test"),
    ]:
        directory = web_root / folder
        directory.mkdir(parents=True)
        (directory / "index.html").write_text(
            f"<h1>{title}</h1>",
            encoding="utf-8",
        )

    application = create_app(
        data_path=api_data_path,
        web_root=web_root,
    )

    with TestClient(application) as test_client:
        assert "Site public test" in test_client.get("/").text
        assert "Administration test" in test_client.get("/admin/").text
        assert test_client.get("/api/festival").status_code == 200


def test_changes_survive_application_restart(
    client: TestClient,
    api_data_path: Path,
    tmp_path: Path,
) -> None:
    response = client.post(
        "/api/artists",
        json={"name": "Artiste Persistance"},
    )

    assert response.status_code == 201
    slug = response.json()["slug"]

    restarted_app = create_app(
        data_path=api_data_path,
        web_root=tmp_path / "another-web",
    )

    with TestClient(restarted_app) as restarted_client:
        reloaded = restarted_client.get(f"/api/artists/{slug}")

    assert reloaded.status_code == 200
    assert reloaded.json()["name"] == "Artiste Persistance"


def test_save_failure_returns_500_without_publishing_change(
    client: TestClient,
    api_data_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from festival.domain.errors import StorageError

    # Initialiser le service avant de simuler l'échec.
    before_response = client.get("/api/artists")
    assert before_response.status_code == 200

    before_artists = before_response.json()
    before_file = api_data_path.read_bytes()

    def fail_save(self, festival) -> None:
        raise StorageError("Échec de sauvegarde simulé.")

    monkeypatch.setattr(
        JsonFestivalRepository,
        "save",
        fail_save,
    )

    response = client.post(
        "/api/artists",
        json={"name": "Artiste Non Sauvegardé"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Échec de sauvegarde simulé."

    after_response = client.get("/api/artists")

    assert after_response.json() == before_artists
    assert api_data_path.read_bytes() == before_file
