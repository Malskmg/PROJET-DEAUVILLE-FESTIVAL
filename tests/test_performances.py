"""Tests des solos, plateaux et ateliers."""

from datetime import UTC, date, datetime

import pytest

from festival.domain.entities import Artist, Venue
from festival.domain.errors import ConflictError, ValidationError
from festival.domain.performances import Lineup, Solo, Workshop


@pytest.fixture
def venue() -> Venue:
    return Venue(
        name="Le Kiosque",
        capacity=120,
        address="Beach promenade",
    )


@pytest.fixture
def artist() -> Artist:
    return Artist(name="Nora Lebrun")


def test_solo_computed_properties(venue: Venue, artist: Artist) -> None:
    show = Solo(
        title="  Nothing Serious  ",
        venue=venue,
        start=datetime(2027, 6, 11, 18, 0),
        duration_minutes=75,
        artist=artist,
    )

    assert show.title == "Nothing Serious"
    assert show.kind == "solo"
    assert show.id == "le-kiosque-2027-06-11-1800"
    assert show.end == datetime(2027, 6, 11, 19, 15)
    assert show.capacity == 120
    assert show.artists == (artist,)
    assert show.summary == "Solo de Nora Lebrun"


@pytest.mark.parametrize(
    ("start", "expected_day"),
    [
        (datetime(2027, 6, 12, 0, 30), date(2027, 6, 11)),
        (datetime(2027, 6, 12, 5, 59), date(2027, 6, 11)),
        (datetime(2027, 6, 12, 6, 0), date(2027, 6, 12)),
    ],
)
def test_festival_day_boundary(
    venue: Venue,
    artist: Artist,
    start: datetime,
    expected_day: date,
) -> None:
    show = Solo(
        title="Night Show",
        venue=venue,
        start=start,
        duration_minutes=60,
        artist=artist,
    )

    assert show.festival_day == expected_day


@pytest.mark.parametrize("duration", [0, 361, -10, True])
def test_invalid_duration_is_rejected(
    venue: Venue,
    artist: Artist,
    duration,
) -> None:
    with pytest.raises(ValidationError):
        Solo(
            title="Show",
            venue=venue,
            start=datetime(2027, 6, 11, 18),
            duration_minutes=duration,
            artist=artist,
        )


@pytest.mark.parametrize("min_age", [-1, 19, True])
def test_invalid_min_age_is_rejected(
    venue: Venue,
    artist: Artist,
    min_age,
) -> None:
    with pytest.raises(ValidationError):
        Solo(
            title="Show",
            venue=venue,
            start=datetime(2027, 6, 11, 18),
            duration_minutes=60,
            artist=artist,
            min_age=min_age,
        )


def test_timezone_is_rejected(venue: Venue, artist: Artist) -> None:
    with pytest.raises(ValidationError):
        Solo(
            title="Show",
            venue=venue,
            start=datetime(2027, 6, 11, 18, tzinfo=UTC),
            duration_minutes=60,
            artist=artist,
        )


def test_lineup_artist_order(venue: Venue) -> None:
    host = Artist(name="Paul Kerbrat")
    nora = Artist(name="Nora Lebrun")
    max_artist = Artist(name="Max Pellerin")

    show = Lineup(
        title="Gala",
        venue=venue,
        start=datetime(2027, 6, 10, 20, 30),
        duration_minutes=60,
        host=host,
        acts=(nora, max_artist),
    )

    assert show.kind == "lineup"
    assert show.artists == (host, nora, max_artist)
    assert show.capacity == 120


def test_lineup_needs_two_acts(venue: Venue) -> None:
    with pytest.raises(ValidationError):
        Lineup(
            title="Gala",
            venue=venue,
            start=datetime(2027, 6, 10, 20, 30),
            duration_minutes=60,
            host=Artist(name="Paul Kerbrat"),
            acts=(Artist(name="Nora Lebrun"),),
        )


def test_lineup_rejects_duplicate_artist_slugs(venue: Venue) -> None:
    with pytest.raises(ValidationError):
        Lineup(
            title="Gala",
            venue=venue,
            start=datetime(2027, 6, 10, 20, 30),
            duration_minutes=60,
            host=Artist(name="Paul Kerbrat"),
            acts=(
                Artist(name="Élodie Marchal"),
                Artist(name="Elodie Marchal"),
            ),
        )


def test_host_cannot_be_an_act(venue: Venue) -> None:
    host = Artist(name="Paul Kerbrat")

    with pytest.raises(ValidationError):
        Lineup(
            title="Gala",
            venue=venue,
            start=datetime(2027, 6, 10, 20, 30),
            duration_minutes=60,
            host=host,
            acts=(host, Artist(name="Nora Lebrun")),
        )


@pytest.mark.parametrize(
    ("duration", "is_valid"),
    [(35, False), (36, True)],
)
def test_three_act_minimum_duration(
    venue: Venue,
    duration: int,
    is_valid: bool,
) -> None:
    arguments = {
        "title": "Gala",
        "venue": venue,
        "start": datetime(2027, 6, 10, 20, 30),
        "duration_minutes": duration,
        "host": Artist(name="Paul Kerbrat"),
        "acts": (
            Artist(name="Nora Lebrun"),
            Artist(name="Max Pellerin"),
            Artist(name="Léa Fontaine"),
        ),
    }

    if is_valid:
        show = Lineup(**arguments)
        assert show.duration_minutes == 36
    else:
        with pytest.raises(ValidationError):
            Lineup(**arguments)


def test_workshop_capacity_uses_venue_limit(artist: Artist) -> None:
    small_venue = Venue(name="La Cabane", capacity=2, address="Beach")

    workshop = Workshop(
        title="Improv",
        venue=small_venue,
        start=datetime(2027, 6, 11, 10, 30),
        duration_minutes=120,
        teacher=artist,
        max_participants=12,
    )

    assert workshop.capacity == 2
    assert workshop.places_left == 2


def test_register_returns_new_workshop(
    venue: Venue,
    artist: Artist,
) -> None:
    workshop = Workshop(
        title="Improv",
        venue=venue,
        start=datetime(2027, 6, 11, 10, 30),
        duration_minutes=120,
        teacher=artist,
        max_participants=12,
    )

    updated = workshop.register("  Camille R.  ")

    assert workshop.participants == ()
    assert updated.participants == ("Camille R.",)
    assert updated.places_left == 11


def test_registration_is_case_insensitive(
    venue: Venue,
    artist: Artist,
) -> None:
    workshop = Workshop(
        title="Improv",
        venue=venue,
        start=datetime(2027, 6, 11, 10, 30),
        duration_minutes=120,
        teacher=artist,
        max_participants=12,
        participants=("Camille R.",),
    )

    with pytest.raises(ConflictError):
        workshop.register(" camille r. ")

    assert workshop.participants == ("Camille R.",)


def test_full_workshop_rejects_registration(
    venue: Venue,
    artist: Artist,
) -> None:
    workshop = Workshop(
        title="Improv",
        venue=venue,
        start=datetime(2027, 6, 11, 10, 30),
        duration_minutes=120,
        teacher=artist,
        max_participants=1,
        participants=("Camille R.",),
    )

    with pytest.raises(ConflictError):
        workshop.register("Yanis B.")

    assert workshop.participants == ("Camille R.",)


def test_loading_duplicate_participants_is_rejected(
    venue: Venue,
    artist: Artist,
) -> None:
    with pytest.raises(ConflictError):
        Workshop(
            title="Improv",
            venue=venue,
            start=datetime(2027, 6, 11, 10, 30),
            duration_minutes=120,
            teacher=artist,
            max_participants=12,
            participants=("Camille R.", "camille r."),
        )


def test_loading_overfilled_workshop_is_rejected(
    venue: Venue,
    artist: Artist,
) -> None:
    with pytest.raises(ConflictError):
        Workshop(
            title="Improv",
            venue=venue,
            start=datetime(2027, 6, 11, 10, 30),
            duration_minutes=120,
            teacher=artist,
            max_participants=1,
            participants=("Camille R.", "Yanis B."),
        )


def test_empty_participant_is_rejected(
    venue: Venue,
    artist: Artist,
) -> None:
    workshop = Workshop(
        title="Improv",
        venue=venue,
        start=datetime(2027, 6, 11, 10, 30),
        duration_minutes=120,
        teacher=artist,
        max_participants=12,
    )

    with pytest.raises(ValidationError):
        workshop.register("   ")


def test_zero_workshop_limit_is_rejected(
    venue: Venue,
    artist: Artist,
) -> None:
    with pytest.raises(ValidationError):
        Workshop(
            title="Improv",
            venue=venue,
            start=datetime(2027, 6, 11, 10, 30),
            duration_minutes=120,
            teacher=artist,
            max_participants=0,
        )
