"""Routes HTTP publiques et administratives."""

from datetime import date, datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request, Response, status

from festival.api.presenters import (
    artist_response,
    festival_response,
    performance_response,
    venue_response,
)
from festival.api.schemas import (
    ArtistCreate,
    ParticipantCreate,
    PerformanceCreate,
)
from festival.application.services import FestivalService
from festival.domain.entities import Artist
from festival.infrastructure.json_repository import JsonFestivalRepository
from festival.infrastructure.serialization import performance_from_data

router = APIRouter(prefix="/api")
FESTIVAL_TIMEZONE = ZoneInfo("Europe/Paris")


def get_service(request: Request) -> FestivalService:
    """Charger une seule instance du service pour cette application."""
    with request.app.state.service_lock:
        if request.app.state.service is None:
            repository = JsonFestivalRepository(request.app.state.data_path)
            request.app.state.service = FestivalService(repository)

        return request.app.state.service


ServiceDependency = Annotated[
    FestivalService,
    Depends(get_service),
]


@router.get("/festival", tags=["Lecture"])
def read_festival(service: ServiceDependency) -> dict[str, Any]:
    return festival_response(service.festival)


@router.get("/venues", tags=["Lecture"])
def read_venues(service: ServiceDependency) -> list[dict[str, Any]]:
    return [venue_response(venue) for venue in service.festival.venues]


@router.get("/artists", tags=["Lecture"])
def read_artists(service: ServiceDependency) -> list[dict[str, Any]]:
    return [artist_response(artist) for artist in service.festival.artists]


@router.get("/artists/{slug}", tags=["Lecture"])
def read_artist(
    slug: str,
    service: ServiceDependency,
) -> dict[str, Any]:
    festival = service.festival
    artist = festival.get_artist(slug)

    data = artist_response(artist)
    data["performances"] = [
        performance_response(performance) for performance in festival.performances_for_artist(slug)
    ]

    return data


@router.get("/programme", tags=["Lecture"])
def read_programme(
    service: ServiceDependency,
    day: date | None = None,
    venue: str | None = None,
) -> list[dict[str, Any]]:
    festival = service.festival

    return [
        performance_response(performance)
        for performance in festival.programme(day=day, venue=venue)
    ]


@router.get("/performances/{performance_id}", tags=["Lecture"])
def read_performance(
    performance_id: str,
    service: ServiceDependency,
) -> dict[str, Any]:
    performance = service.festival.get_performance(performance_id)

    return performance_response(performance)


@router.get("/now", tags=["Lecture"])
def read_now(
    service: ServiceDependency,
    at: datetime | None = None,
) -> dict[str, Any]:
    festival = service.festival
    moment = at

    if moment is None:
        moment = datetime.now(FESTIVAL_TIMEZONE).replace(tzinfo=None)

    return {
        "at": moment.isoformat(),
        "now_playing": [
            performance_response(performance) for performance in festival.now_playing(moment)
        ],
        "up_next": [performance_response(performance) for performance in festival.up_next(moment)],
    }


@router.post(
    "/artists",
    status_code=status.HTTP_201_CREATED,
    tags=["Administration"],
)
def create_artist(
    body: ArtistCreate,
    service: ServiceDependency,
) -> dict[str, Any]:
    artist = Artist(**body.model_dump())
    created = service.add_artist(artist)

    return artist_response(created)


@router.post(
    "/performances",
    status_code=status.HTTP_201_CREATED,
    tags=["Administration"],
)
def create_performance(
    body: PerformanceCreate,
    service: ServiceDependency,
) -> dict[str, Any]:
    snapshot = service.festival

    performance = performance_from_data(
        snapshot,
        body.model_dump(mode="json"),
    )
    created = service.schedule(performance)

    return performance_response(created)


@router.put(
    "/performances/{performance_id}",
    tags=["Administration"],
)
def update_performance(
    performance_id: str,
    body: PerformanceCreate,
    service: ServiceDependency,
) -> dict[str, Any]:
    snapshot = service.festival

    # Signaler d'abord un identifiant de spectacle inconnu.
    snapshot.get_performance(performance_id)

    replacement = performance_from_data(
        snapshot,
        body.model_dump(mode="json"),
    )

    updated = service.update_performance(
        performance_id,
        replacement,
    )

    return performance_response(updated)


@router.delete(
    "/performances/{performance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    tags=["Administration"],
)
def delete_performance(
    performance_id: str,
    service: ServiceDependency,
) -> Response:
    service.cancel(performance_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/performances/{performance_id}/participants",
    status_code=status.HTTP_201_CREATED,
    tags=["Administration"],
)
def register_participant(
    performance_id: str,
    body: ParticipantCreate,
    service: ServiceDependency,
) -> dict[str, Any]:
    workshop = service.register_participant(
        performance_id,
        body.name,
    )

    return performance_response(workshop)
