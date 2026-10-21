"""Conversion des objets métier vers les réponses HTTP."""

from typing import Any

from festival.domain.entities import Artist, Venue
from festival.domain.festival import Festival
from festival.domain.performances import Performance, Workshop
from festival.infrastructure.serialization import performance_to_data


def artist_response(artist: Artist) -> dict[str, Any]:
    return {
        "slug": artist.slug,
        "name": artist.name,
        "bio": artist.bio,
        "photo_url": artist.photo_url,
    }


def venue_response(venue: Venue) -> dict[str, Any]:
    return {
        "slug": venue.slug,
        "name": venue.name,
        "capacity": venue.capacity,
        "address": venue.address,
    }


def performance_response(performance: Performance) -> dict[str, Any]:
    data = performance_to_data(performance)

    data.update(
        {
            "id": performance.id,
            "venue_name": performance.venue.name,
            "end": performance.end.isoformat(),
            "festival_day": performance.festival_day.isoformat(),
            "summary": performance.summary,
            "capacity": performance.capacity,
            "artists": [
                {
                    "slug": artist.slug,
                    "name": artist.name,
                }
                for artist in performance.artists
            ],
        }
    )

    if isinstance(performance, Workshop):
        data["places_left"] = performance.places_left

    return data


def festival_response(festival: Festival) -> dict[str, Any]:
    return {
        "name": festival.name,
        "first_day": festival.first_day.isoformat(),
        "last_day": festival.last_day.isoformat(),
        "days": [day.isoformat() for day in festival.days],
    }
