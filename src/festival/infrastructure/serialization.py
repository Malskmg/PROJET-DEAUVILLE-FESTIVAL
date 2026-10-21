"""Conversion entre données JSON et objets métier."""

from datetime import date, datetime
from typing import Any

from festival.domain.entities import Artist, Venue
from festival.domain.errors import ValidationError
from festival.domain.festival import Festival
from festival.domain.performances import Lineup, Performance, Solo, Workshop


def require_object(value: Any, label: str) -> dict[str, Any]:
    """Vérifier qu'une valeur est un objet JSON."""
    if not isinstance(value, dict):
        raise ValidationError(f"{label} doit être un objet JSON.")

    return value


def require_list(value: Any, label: str) -> list[Any]:
    """Vérifier qu'une valeur est une liste JSON."""
    if not isinstance(value, list):
        raise ValidationError(f"{label} doit être une liste.")

    return value


def require_string(value: Any, label: str) -> str:
    """Vérifier un texte avant son utilisation comme référence."""
    if not isinstance(value, str):
        raise ValidationError(f"{label} doit être un texte.")

    return value


def parse_day(value: Any) -> date:
    """Lire une date au format ISO."""
    return date.fromisoformat(require_string(value, "La date"))


def parse_moment(value: Any) -> datetime:
    """Lire une date et une heure au format ISO."""
    text = require_string(value, "Le début du spectacle")

    if "T" not in text:
        raise ValidationError("Le début du spectacle doit contenir une date et une heure.")

    return datetime.fromisoformat(text)


def performance_from_data(
    festival: Festival,
    data: dict[str, Any],
) -> Performance:
    """Construire une représentation en résolvant ses références."""
    data = require_object(data, "Le spectacle")

    common = {
        "title": data["title"],
        "venue": festival.get_venue(require_string(data["venue"], "Le lieu")),
        "start": parse_moment(data["start"]),
        "duration_minutes": data["duration_minutes"],
        "description": data.get("description", ""),
    }

    kind = data["kind"]

    if kind == "solo":
        return Solo(
            **common,
            artist=festival.get_artist(require_string(data["artist"], "L'artiste")),
            min_age=data.get("min_age", 0),
        )

    if kind == "lineup":
        acts = require_list(data["acts"], "Les artistes du plateau")

        return Lineup(
            **common,
            host=festival.get_artist(require_string(data["host"], "Le présentateur")),
            acts=tuple(
                festival.get_artist(require_string(slug, "L'identifiant d'un artiste"))
                for slug in acts
            ),
        )

    if kind == "workshop":
        participants = require_list(
            data.get("participants", []),
            "Les participants",
        )

        return Workshop(
            **common,
            teacher=festival.get_artist(require_string(data["teacher"], "L'animateur")),
            max_participants=data["max_participants"],
            participants=tuple(participants),
        )

    raise ValidationError(
        f"Type de spectacle inconnu : {kind!r}. Utilisez solo, lineup ou workshop."
    )


def festival_from_data(data: dict[str, Any]) -> Festival:
    """Reconstruire le festival en passant par ses opérations validées."""
    data = require_object(data, "Le festival")

    festival = Festival(
        name=data["name"],
        first_day=parse_day(data["first_day"]),
        last_day=parse_day(data["last_day"]),
    )

    for item in require_list(data["venues"], "Les lieux"):
        venue = require_object(item, "Un lieu")
        festival.add_venue(
            Venue(
                name=venue["name"],
                capacity=venue["capacity"],
                address=venue["address"],
            )
        )

    for item in require_list(data["artists"], "Les artistes"):
        artist = require_object(item, "Un artiste")
        festival.add_artist(
            Artist(
                name=artist["name"],
                bio=artist.get("bio", ""),
                photo_url=artist.get("photo_url", ""),
            )
        )

    for index, item in enumerate(
        require_list(data["performances"], "Les spectacles"),
        start=1,
    ):
        try:
            performance = performance_from_data(festival, item)
            festival.schedule(performance)
        except KeyError as error:
            raise ValidationError(
                f"Spectacle n°{index} : champ obligatoire absent : {error.args[0]}."
            ) from error

    return festival


def performance_to_data(performance: Performance) -> dict[str, Any]:
    """Produire uniquement les champs destinés au fichier de données."""
    data: dict[str, Any] = {
        "kind": performance.kind,
        "title": performance.title,
        "venue": performance.venue.slug,
        "start": performance.start.isoformat(),
        "duration_minutes": performance.duration_minutes,
        "description": performance.description,
    }

    if isinstance(performance, Solo):
        data.update(
            artist=performance.artist.slug,
            min_age=performance.min_age,
        )
    elif isinstance(performance, Lineup):
        data.update(
            host=performance.host.slug,
            acts=[artist.slug for artist in performance.acts],
        )
    elif isinstance(performance, Workshop):
        data.update(
            teacher=performance.teacher.slug,
            max_participants=performance.max_participants,
            participants=list(performance.participants),
        )
    else:
        raise ValidationError("Type de spectacle non pris en charge.")

    return data


def festival_to_data(festival: Festival) -> dict[str, Any]:
    """Sérialiser un festival sans enregistrer ses champs calculés."""
    return {
        "name": festival.name,
        "first_day": festival.first_day.isoformat(),
        "last_day": festival.last_day.isoformat(),
        "venues": [
            {
                "name": venue.name,
                "capacity": venue.capacity,
                "address": venue.address,
            }
            for venue in festival.venues
        ],
        "artists": [
            {
                "name": artist.name,
                "bio": artist.bio,
                "photo_url": artist.photo_url,
            }
            for artist in festival.artists
        ],
        "performances": [performance_to_data(performance) for performance in festival.performances],
    }
