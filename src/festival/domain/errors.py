"""Erreurs métier compréhensibles par les organisateurs."""


class FestivalError(Exception):
    """Erreur métier de base."""


class NotFoundError(FestivalError):
    """Une ressource demandée n'existe pas."""


class ConflictError(FestivalError):
    """Une opération entre en conflit avec l'état du festival."""


class ValidationError(FestivalError, ValueError):
    """Une valeur ne respecte pas les règles du domaine."""


class StorageError(FestivalError):
    """Les données ne peuvent pas être lues ou sauvegardées."""
