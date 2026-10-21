"""Tests du dépôt JSON."""

import json
from pathlib import Path

import pytest

from festival.domain.errors import StorageError
from festival.infrastructure.json_repository import JsonFestivalRepository
from festival.infrastructure.serialization import festival_to_data


def test_load_real_data(festival_data_path: Path) -> None:
    festival = JsonFestivalRepository(festival_data_path).load()

    assert festival.name == "Deauville Festival du Rire 2027"
    assert len(festival.venues) == 4
    assert len(festival.artists) == 12
    assert len(festival.performances) == 23


def test_round_trip_preserves_data(
    festival_data_path: Path,
    tmp_path: Path,
) -> None:
    original = JsonFestivalRepository(festival_data_path).load()
    repository = JsonFestivalRepository(tmp_path / "festival.json")

    repository.save(original)
    reloaded = repository.load()

    assert festival_to_data(reloaded) == festival_to_data(original)


def test_invalid_json_has_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text('{"name":', encoding="utf-8")

    with pytest.raises(StorageError, match="JSON invalide"):
        JsonFestivalRepository(path).load()


def test_missing_file_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(StorageError, match="Impossible de lire"):
        JsonFestivalRepository(tmp_path / "missing.json").load()


def test_missing_field_has_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "incomplete.json"
    path.write_text('{"name": "Festival"}', encoding="utf-8")

    with pytest.raises(StorageError, match="champ obligatoire absent"):
        JsonFestivalRepository(path).load()


def test_loading_rechecks_schedule(
    festival_data_path: Path,
    tmp_path: Path,
) -> None:
    original = JsonFestivalRepository(festival_data_path).load()
    data = festival_to_data(original)
    data["performances"].append(dict(data["performances"][0]))

    path = tmp_path / "conflicting.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(StorageError, match="existe déjà"):
        JsonFestivalRepository(path).load()


def test_failed_replace_preserves_original_file(
    festival_data_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    festival = JsonFestivalRepository(festival_data_path).load()
    path = tmp_path / "festival.json"
    repository = JsonFestivalRepository(path)
    repository.save(festival)
    before = path.read_bytes()

    def fail_replace(*args, **kwargs) -> None:
        raise PermissionError("Écriture refusée pour le test.")

    monkeypatch.setattr(
        "festival.infrastructure.json_repository.os.replace",
        fail_replace,
    )

    with pytest.raises(StorageError, match="Impossible de sauvegarder"):
        repository.save(festival)

    assert path.read_bytes() == before
    assert list(tmp_path.glob("*.tmp")) == []
