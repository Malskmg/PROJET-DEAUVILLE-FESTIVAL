"""Gestion du festival, de ses références et de sa programmation."""

from datetime import date, datetime, timedelta

from festival.domain.entities import Artist, Venue
from festival.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from festival.domain.identifiers import normalize_name
from festival.domain.performances import (
    Lineup,
    Performance,
    Solo,
    Workshop,
)

BREAK_TIME = timedelta(minutes=30)


class Festival:
    """Point d'entrée des opérations métier sur le festival."""

    def __init__(
        self,
        *,
        name: str,
        first_day: date,
        last_day: date,
    ) -> None:
        self._name = normalize_name(name)

        if type(first_day) is not date or type(last_day) is not date:
            raise ValidationError("Les dates du festival doivent être des dates sans heure.")

        if first_day > last_day:
            raise ValidationError("Le premier jour doit précéder ou être égal au dernier jour.")

        self._first_day = first_day
        self._last_day = last_day
        self._artists: dict[str, Artist] = {}
        self._venues: dict[str, Venue] = {}
        self._performances: dict[str, Performance] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def first_day(self) -> date:
        return self._first_day

    @property
    def last_day(self) -> date:
        return self._last_day

    @property
    def days(self) -> tuple[date, ...]:
        """Journées du festival, bornes incluses."""
        number_of_days = (self.last_day - self.first_day).days + 1

        return tuple(self.first_day + timedelta(days=offset) for offset in range(number_of_days))

    @property
    def artists(self) -> tuple[Artist, ...]:
        """Artistes triés par slug."""
        return tuple(self._artists[slug] for slug in sorted(self._artists))

    @property
    def venues(self) -> tuple[Venue, ...]:
        """Lieux dans leur ordre d'ajout."""
        return tuple(self._venues.values())

    @property
    def performances(self) -> tuple[Performance, ...]:
        """Spectacles triés par début, puis par nom de lieu."""
        return tuple(
            sorted(
                self._performances.values(),
                key=lambda performance: (
                    performance.start,
                    performance.venue.name,
                ),
            )
        )

    def add_artist(self, artist: Artist) -> Artist:
        """Ajouter un artiste sans dupliquer son slug."""
        if not isinstance(artist, Artist):
            raise ValidationError("L'artiste fourni n'est pas valide.")

        if artist.slug in self._artists:
            raise ConflictError(f"L'artiste {artist.name} existe déjà dans le festival.")

        self._artists[artist.slug] = artist
        return artist

    def add_venue(self, venue: Venue) -> Venue:
        """Ajouter un lieu sans dupliquer son slug."""
        if not isinstance(venue, Venue):
            raise ValidationError("Le lieu fourni n'est pas valide.")

        if venue.slug in self._venues:
            raise ConflictError(f"Le lieu {venue.name} existe déjà dans le festival.")

        self._venues[venue.slug] = venue
        return venue

    def get_artist(self, slug: str) -> Artist:
        """Rechercher un artiste par son slug."""
        try:
            return self._artists[slug]
        except KeyError:
            raise NotFoundError(f"Aucun artiste ne correspond à l'identifiant '{slug}'.") from None

    def get_venue(self, slug: str) -> Venue:
        """Rechercher un lieu par son slug."""
        try:
            return self._venues[slug]
        except KeyError:
            raise NotFoundError(f"Aucun lieu ne correspond à l'identifiant '{slug}'.") from None

    def get_performance(self, performance_id: str) -> Performance:
        """Rechercher un spectacle par son identifiant."""
        try:
            return self._performances[performance_id]
        except KeyError:
            raise NotFoundError(f"Aucun spectacle ne correspond à '{performance_id}'.") from None

    def schedule(self, performance: Performance) -> Performance:
        """Programmer un spectacle après toutes les validations."""
        self._validate_candidate(performance)

        self._performances[performance.id] = performance
        return performance

    def update_performance(
        self,
        performance_id: str,
        replacement: Performance,
    ) -> Performance:
        """Remplacer un spectacle sans supprimer l'ancien avant validation."""
        self.get_performance(performance_id)

        self._validate_candidate(
            replacement,
            ignored_id=performance_id,
        )

        updated = dict(self._performances)
        del updated[performance_id]
        updated[replacement.id] = replacement

        self._performances = updated
        return replacement

    def cancel(self, performance_id: str) -> Performance:
        """Annuler un spectacle existant."""
        performance = self.get_performance(performance_id)
        del self._performances[performance_id]
        return performance

    def register_participant(
        self,
        performance_id: str,
        name: str,
    ) -> Workshop:
        """Inscrire une personne dans un atelier existant."""
        performance = self.get_performance(performance_id)

        if not isinstance(performance, Workshop):
            raise ValidationError("Les inscriptions sont réservées aux ateliers.")

        replacement = performance.register(name)
        self.update_performance(performance_id, replacement)

        return replacement

    def programme(
        self,
        *,
        day: date | None = None,
        venue: str | None = None,
    ) -> tuple[Performance, ...]:
        """Consulter le programme avec des filtres facultatifs."""
        if day is not None and type(day) is not date:
            raise ValidationError("La journée demandée doit être une date sans heure.")

        if venue is not None:
            self.get_venue(venue)

        return tuple(
            performance
            for performance in self.performances
            if (day is None or performance.festival_day == day)
            and (venue is None or performance.venue.slug == venue)
        )

    def performances_for_artist(
        self,
        slug: str,
    ) -> tuple[Performance, ...]:
        """Consulter tous les spectacles d'un artiste, tous rôles confondus."""
        self.get_artist(slug)

        return tuple(
            performance
            for performance in self.performances
            if any(artist.slug == slug for artist in performance.artists)
        )

    def now_playing(self, at: datetime) -> tuple[Performance, ...]:
        """Spectacles commencés et non terminés au moment demandé."""
        self._validate_moment(at)

        return tuple(
            performance
            for performance in self.performances
            if performance.start <= at < performance.end
        )

    def up_next(self, at: datetime) -> tuple[Performance, ...]:
        """Au maximum les trois prochains spectacles."""
        self._validate_moment(at)

        upcoming = (performance for performance in self.performances if performance.start > at)

        return tuple(upcoming)[:3]

    @staticmethod
    def _validate_moment(at: datetime) -> None:
        if not isinstance(at, datetime) or at.tzinfo is not None:
            raise ValidationError(
                "Le moment demandé doit être une date et une heure locales, sans fuseau horaire."
            )

    def _validate_candidate(
        self,
        candidate: Performance,
        *,
        ignored_id: str | None = None,
    ) -> None:
        """Contrôler entièrement un ajout ou un remplacement."""
        if not isinstance(candidate, (Solo, Lineup, Workshop)):
            raise ValidationError("Le spectacle doit être un solo, un plateau ou un atelier.")

        self._validate_references(candidate)

        if not self.first_day <= candidate.festival_day <= self.last_day:
            raise ConflictError(
                f"Le spectacle '{candidate.title}' appartient à la journée "
                f"du {candidate.festival_day:%d/%m/%Y}, hors du festival "
                f"({self.first_day:%d/%m/%Y} au {self.last_day:%d/%m/%Y})."
            )

        if candidate.id in self._performances and candidate.id != ignored_id:
            raise ConflictError("Un spectacle existe déjà dans ce lieu à cette heure.")

        candidate_artists = {artist.slug: artist for artist in candidate.artists}

        for existing in self.performances:
            if existing.id == ignored_id:
                continue

            if not self._too_close(candidate, existing):
                continue

            if candidate.venue.slug == existing.venue.slug:
                raise ConflictError(
                    f"{candidate.venue.name} est occupé par "
                    f"{self._describe(existing)}. "
                    "Laissez 30 minutes entre deux spectacles."
                )

            for artist in existing.artists:
                if artist.slug in candidate_artists:
                    raise ConflictError(
                        f"{artist.name} participe déjà à "
                        f"{self._describe(existing)}. "
                        "Laissez 30 minutes entre deux spectacles "
                        "pour un même artiste."
                    )

    def _validate_references(self, performance: Performance) -> None:
        """Refuser les références inconnues ou les copies incohérentes."""
        registered_venue = self.get_venue(performance.venue.slug)

        if performance.venue != registered_venue:
            raise ValidationError(
                "Les informations du lieu ne correspondent pas "
                "à celles enregistrées dans le festival."
            )

        for artist in performance.artists:
            registered_artist = self.get_artist(artist.slug)

            if artist != registered_artist:
                raise ValidationError(
                    f"Les informations de {artist.name} ne correspondent pas "
                    "à celles enregistrées dans le festival."
                )

    @staticmethod
    def _too_close(
        first: Performance,
        second: Performance,
    ) -> bool:
        """Vérifier le chevauchement ou une pause inférieure à 30 minutes."""
        if first.end <= second.start:
            return second.start - first.end < BREAK_TIME

        if second.end <= first.start:
            return first.start - second.end < BREAK_TIME

        return True

    @staticmethod
    def _describe(performance: Performance) -> str:
        return (
            f"'{performance.title}' "
            f"({performance.start:%d/%m/%Y %H:%M} - "
            f"{performance.end:%d/%m/%Y %H:%M})"
        )
