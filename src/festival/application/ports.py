"""Contrat de stockage indépendant du format de persistance."""

from abc import ABC, abstractmethod

from festival.domain.festival import Festival


class FestivalRepository(ABC):
    """Interface des dépôts de données du festival."""

    @abstractmethod
    def load(self) -> Festival:
        """Charger un festival en revalidant toutes ses règles."""

    @abstractmethod
    def save(self, festival: Festival) -> None:
        """Sauvegarder un festival ou signaler un échec."""
