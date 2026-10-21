"""Corps des requêtes HTTP de l'API."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class RequestModel(BaseModel):
    """Refuser les champs inattendus dans les requêtes."""

    model_config = ConfigDict(extra="forbid")


class ArtistCreate(RequestModel):
    name: str
    bio: str = ""
    photo_url: str = ""


class ParticipantCreate(RequestModel):
    name: str


class PerformanceBase(RequestModel):
    title: str
    venue: str
    start: datetime
    duration_minutes: StrictInt
    description: str = ""


class SoloCreate(PerformanceBase):
    kind: Literal["solo"]
    artist: str
    min_age: StrictInt = 0


class LineupCreate(PerformanceBase):
    kind: Literal["lineup"]
    host: str
    acts: list[str]


class WorkshopCreate(PerformanceBase):
    kind: Literal["workshop"]
    teacher: str
    max_participants: StrictInt
    participants: list[str] = Field(default_factory=list)


PerformanceCreate = Annotated[
    SoloCreate | LineupCreate | WorkshopCreate,
    Field(discriminator="kind"),
]
