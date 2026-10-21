"""Représentations du festival et contraintes propres à chaque type."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from festival.domain.entities import (
    Artist,
    Venue,
    validate_integer,
    validate_text,
)
from festival.domain.errors import ConflictError, ValidationError
from festival.domain.identifiers import normalize_name


@dataclass(frozen=True, slots=True, kw_only=True)
class Performance(ABC):
    """Propriétés communes à toutes les représentations."""

    title: str
    venue: Venue
    start: datetime
    duration_minutes: int
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", normalize_name(self.title))

        if not isinstance(self.venue, Venue):
            raise ValidationError("Le lieu doit être un lieu valide du festival.")

        if not isinstance(self.start, datetime):
            raise ValidationError("Le début du spectacle doit être une date avec une heure.")

        if self.start.tzinfo is not None:
            raise ValidationError("L'heure du spectacle doit être locale, sans fuseau horaire.")

        validate_integer(
            self.duration_minutes,
            "La durée du spectacle",
            minimum=1,
            maximum=360,
        )
        validate_text(self.description, "La description")

        try:
            self.start + timedelta(minutes=self.duration_minutes)
        except OverflowError as error:
            raise ValidationError(
                "La date de fin du spectacle dépasse les dates acceptées."
            ) from error

    @property
    def id(self) -> str:
        """Identifiant construit avec le lieu et le début du spectacle."""
        return f"{self.venue.slug}-{self.start:%Y-%m-%d-%H%M}"

    @property
    def end(self) -> datetime:
        """Date et heure de fin."""
        return self.start + timedelta(minutes=self.duration_minutes)

    @property
    def festival_day(self) -> date:
        """Journée du festival, avec une bascule à 06 h."""
        if self.start.hour < 6:
            try:
                return self.start.date() - timedelta(days=1)
            except OverflowError as error:
                raise ValidationError(
                    "Impossible de déterminer la journée de ce spectacle."
                ) from error

        return self.start.date()

    @property
    def capacity(self) -> int:
        """Capacité publique du spectacle."""
        return self.venue.capacity

    @property
    @abstractmethod
    def kind(self) -> str:
        """Type de représentation."""

    @property
    @abstractmethod
    def artists(self) -> tuple[Artist, ...]:
        """Artistes présents, dans leur ordre d'apparition."""

    @property
    @abstractmethod
    def summary(self) -> str:
        """Résumé sur une ligne pour le programme."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Solo(Performance):
    """Spectacle d'un seul artiste."""

    artist: Artist
    min_age: int = 0

    def __post_init__(self) -> None:
        Performance.__post_init__(self)

        if not isinstance(self.artist, Artist):
            raise ValidationError("Le solo doit avoir un artiste valide.")

        validate_integer(
            self.min_age,
            "L'âge minimum",
            minimum=0,
            maximum=18,
        )

    @property
    def kind(self) -> str:
        return "solo"

    @property
    def artists(self) -> tuple[Artist, ...]:
        return (self.artist,)

    @property
    def summary(self) -> str:
        return f"Solo de {self.artist.name}"


@dataclass(frozen=True, slots=True, kw_only=True)
class Lineup(Performance):
    """Plateau avec un présentateur et plusieurs artistes."""

    host: Artist
    acts: tuple[Artist, ...]

    def __post_init__(self) -> None:
        Performance.__post_init__(self)

        if not isinstance(self.host, Artist):
            raise ValidationError("Le plateau doit avoir un présentateur valide.")

        if not isinstance(self.acts, (list, tuple)):
            raise ValidationError("Les artistes du plateau doivent être fournis dans une liste.")

        acts = tuple(self.acts)

        if len(acts) < 2:
            raise ValidationError("Un plateau doit contenir au moins deux artistes.")

        if any(not isinstance(artist, Artist) for artist in acts):
            raise ValidationError("Tous les artistes du plateau doivent être valides.")

        slugs = [artist.slug for artist in acts]

        if len(slugs) != len(set(slugs)):
            raise ValidationError("Un artiste ne peut apparaître qu'une fois dans un plateau.")

        if self.host.slug in slugs:
            raise ValidationError("Le présentateur ne peut pas être aussi un artiste du plateau.")

        minimum_duration = len(acts) * 10 + (len(acts) - 1) * 3

        if self.duration_minutes < minimum_duration:
            raise ValidationError(f"Ce plateau nécessite au moins {minimum_duration} minutes.")

        object.__setattr__(self, "acts", acts)

    @property
    def kind(self) -> str:
        return "lineup"

    @property
    def artists(self) -> tuple[Artist, ...]:
        return (self.host, *self.acts)

    @property
    def summary(self) -> str:
        names = ", ".join(artist.name for artist in self.acts)
        return f"Présenté par {self.host.name}, avec {names}"


@dataclass(frozen=True, slots=True, kw_only=True)
class Workshop(Performance):
    """Atelier animé par un artiste, avec inscriptions nominatives."""

    teacher: Artist
    max_participants: int
    participants: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        Performance.__post_init__(self)

        if not isinstance(self.teacher, Artist):
            raise ValidationError("L'atelier doit avoir un animateur valide.")

        validate_integer(
            self.max_participants,
            "Le nombre maximum de participants",
            minimum=1,
        )

        if not isinstance(self.participants, (list, tuple)):
            raise ValidationError("Les participants doivent être fournis dans une liste.")

        cleaned_names = tuple(normalize_name(name) for name in self.participants)
        compared_names = [name.casefold() for name in cleaned_names]

        if len(compared_names) != len(set(compared_names)):
            raise ConflictError("Une personne est inscrite plusieurs fois à cet atelier.")

        if len(cleaned_names) > self.capacity:
            raise ConflictError(f"L'atelier ne peut accueillir que {self.capacity} participants.")

        object.__setattr__(self, "participants", cleaned_names)

    @property
    def kind(self) -> str:
        return "workshop"

    @property
    def artists(self) -> tuple[Artist, ...]:
        return (self.teacher,)

    @property
    def capacity(self) -> int:
        return min(self.max_participants, self.venue.capacity)

    @property
    def places_left(self) -> int:
        """Nombre de places restantes."""
        return self.capacity - len(self.participants)

    @property
    def summary(self) -> str:
        return f"Atelier animé par {self.teacher.name}"

    def register(self, name: str) -> "Workshop":
        """Produire une nouvelle version de l'atelier avec une inscription."""
        cleaned_name = normalize_name(name)
        existing_names = {participant.casefold() for participant in self.participants}

        if cleaned_name.casefold() in existing_names:
            raise ConflictError(f"{cleaned_name} est déjà inscrit à cet atelier.")

        if self.places_left == 0:
            raise ConflictError("Cet atelier est complet.")

        return replace(
            self,
            participants=(*self.participants, cleaned_name),
        )
