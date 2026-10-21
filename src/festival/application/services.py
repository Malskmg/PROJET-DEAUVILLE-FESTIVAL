"""Cas d'usage avec sauvegarde avant publication du nouvel état."""

from collections.abc import Callable
from copy import deepcopy
from threading import RLock
from typing import TypeVar

from festival.application.ports import FestivalRepository
from festival.domain.entities import Artist
from festival.domain.festival import Festival
from festival.domain.performances import Performance, Workshop

Result = TypeVar("Result")


class FestivalService:
    """Coordonner les modifications métier et la persistance."""

    def __init__(self, repository: FestivalRepository) -> None:
        self._repository = repository
        self._lock = RLock()
        self._festival = repository.load()

    @property
    def festival(self) -> Festival:
        """Fournir une copie indépendante pour la consultation."""
        with self._lock:
            return deepcopy(self._festival)

    def _commit(
        self,
        operation: Callable[[Festival], Result],
    ) -> Result:
        """Valider et sauvegarder une copie avant de la publier."""
        with self._lock:
            working_copy = deepcopy(self._festival)
            result = operation(working_copy)

            self._repository.save(working_copy)
            self._festival = working_copy

            return result

    def add_artist(self, artist: Artist) -> Artist:
        return self._commit(lambda festival: festival.add_artist(artist))

    def schedule(self, performance: Performance) -> Performance:
        return self._commit(lambda festival: festival.schedule(performance))

    def update_performance(
        self,
        performance_id: str,
        replacement: Performance,
    ) -> Performance:
        return self._commit(
            lambda festival: festival.update_performance(
                performance_id,
                replacement,
            )
        )

    def cancel(self, performance_id: str) -> Performance:
        return self._commit(lambda festival: festival.cancel(performance_id))

    def register_participant(
        self,
        performance_id: str,
        name: str,
    ) -> Workshop:
        return self._commit(
            lambda festival: festival.register_participant(
                performance_id,
                name,
            )
        )
