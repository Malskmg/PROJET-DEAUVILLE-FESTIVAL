"""Tests des artistes et des lieux."""

from dataclasses import FrozenInstanceError

import pytest

from festival.domain.entities import Artist, Venue
from festival.domain.errors import ValidationError


def test_artist_has_clean_name_and_slug() -> None:
    artist = Artist(name="  Élodie Marchal  ")

    assert artist.name == "Élodie Marchal"
    assert artist.slug == "elodie-marchal"
    assert artist.bio == ""
    assert artist.photo_url == ""


def test_venue_has_slug_and_capacity() -> None:
    venue = Venue(
        name="  Théâtre des Planches ",
        capacity=320,
        address="Town centre",
    )

    assert venue.name == "Théâtre des Planches"
    assert venue.slug == "theatre-des-planches"
    assert venue.capacity == 320


@pytest.mark.parametrize("capacity", [0, -1, True, 1.5])
def test_invalid_venue_capacity_is_rejected(capacity) -> None:
    with pytest.raises(ValidationError):
        Venue(name="Le Kiosque", capacity=capacity, address="Beach")


def test_artist_cannot_be_modified_directly() -> None:
    artist = Artist(name="Nora Lebrun")

    with pytest.raises(FrozenInstanceError):
        artist.name = "Autre nom"
