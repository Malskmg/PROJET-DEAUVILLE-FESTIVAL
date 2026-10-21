"""Tests des modifications avec persistance."""

from copy import deepcopy
from pathlib import Path

import pytest

from festival.application.ports import FestivalRepository
from festival.application.services import FestivalService
from festival.domain.entities import Artist
from festival.domain.errors import ConflictError, StorageError
from festival.domain.festival import Festival
from festival.infrastructure.json_repository import JsonFestivalRepository


class FailingRepository(FestivalRepository):
    """Dépôt simulant un échec de sauvegarde."""

    def __init__(self, festival: Festival) -> None:
        self._festival = deepcopy(festival)

    def load(self) -> Festival:
        return deepcopy(self._festival)

    def save(self, festival: Festival) -> None:
        raise StorageError("Sauvegarde refusée pour le test.")


def test_artist_creation_is_saved(
    festival_data_path: Path,
    tmp_path: Path,
) -> None:
    original = JsonFestivalRepository(festival_data_path).load()
    repository = JsonFestivalRepository(tmp_path / "festival.json")
    repository.save(original)
    service = FestivalService(repository)

    created = service.add_artist(Artist(name="Malik Test"))

    assert service.festival.get_artist(created.slug) == created
    assert repository.load().get_artist(created.slug) == created


def test_failed_save_keeps_current_state(
    festival_data_path: Path,
) -> None:
    original = JsonFestivalRepository(festival_data_path).load()
    service = FestivalService(FailingRepository(original))
    before = service.festival.artists

    with pytest.raises(StorageError):
        service.add_artist(Artist(name="Malik Test"))

    assert service.festival.artists == before


def test_rejected_change_keeps_file_unchanged(
    festival_data_path: Path,
    tmp_path: Path,
) -> None:
    original = JsonFestivalRepository(festival_data_path).load()
    repository = JsonFestivalRepository(tmp_path / "festival.json")
    repository.save(original)
    service = FestivalService(repository)
    before = repository.path.read_bytes()

    with pytest.raises(ConflictError):
        service.add_artist(Artist(name="Nora Lebrun"))

    assert repository.path.read_bytes() == before


def test_snapshot_cannot_change_service_state(
    festival_data_path: Path,
) -> None:
    repository = JsonFestivalRepository(festival_data_path)
    service = FestivalService(repository)

    snapshot = service.festival
    snapshot.add_artist(Artist(name="Artiste temporaire"))

    assert len(snapshot.artists) == 13
    assert len(service.festival.artists) == 12
