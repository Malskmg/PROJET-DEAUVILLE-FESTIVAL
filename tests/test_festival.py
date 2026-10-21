"""Tests du festival et des contraintes de programmation."""

from dataclasses import replace
from datetime import date, datetime

import pytest

from festival.domain.entities import Artist, Venue
from festival.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from festival.domain.festival import Festival
from festival.domain.performances import Lineup, Solo, Workshop


@pytest.fixture
def festival() -> Festival:
    result = Festival(
        name="Deauville Festival du Rire 2027",
        first_day=date(2027, 6, 10),
        last_day=date(2027, 6, 13),
    )

    result.add_venue(
        Venue(
            name="Le Kiosque",
            capacity=120,
            address="Beach promenade",
        )
    )
    result.add_venue(
        Venue(
            name="Grand Casino",
            capacity=650,
            address="Seafront",
        )
    )

    for name in [
        "Nora Lebrun",
        "Paul Kerbrat",
        "Max Pellerin",
        "Élodie Marchal",
    ]:
        result.add_artist(Artist(name=name))

    return result


def make_solo(
    festival: Festival,
    *,
    title: str = "Premier spectacle",
    venue: str = "le-kiosque",
    artist: str = "nora-lebrun",
    start: datetime = datetime(2027, 6, 11, 18),
    duration: int = 60,
) -> Solo:
    return Solo(
        title=title,
        venue=festival.get_venue(venue),
        start=start,
        duration_minutes=duration,
        artist=festival.get_artist(artist),
    )


def test_days_include_both_boundaries(festival: Festival) -> None:
    assert festival.days == (
        date(2027, 6, 10),
        date(2027, 6, 11),
        date(2027, 6, 12),
        date(2027, 6, 13),
    )


def test_invalid_festival_dates_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Festival(
            name="Festival",
            first_day=date(2027, 6, 13),
            last_day=date(2027, 6, 10),
        )


def test_artists_are_sorted_by_slug(festival: Festival) -> None:
    assert [artist.slug for artist in festival.artists] == [
        "elodie-marchal",
        "max-pellerin",
        "nora-lebrun",
        "paul-kerbrat",
    ]


def test_venues_keep_insertion_order(festival: Festival) -> None:
    assert [venue.slug for venue in festival.venues] == [
        "le-kiosque",
        "grand-casino",
    ]


def test_duplicate_artist_slug_is_rejected(festival: Festival) -> None:
    before = festival.artists

    with pytest.raises(ConflictError):
        festival.add_artist(Artist(name="Elodie Marchal"))

    assert festival.artists == before


def test_duplicate_venue_slug_is_rejected(festival: Festival) -> None:
    with pytest.raises(ConflictError):
        festival.add_venue(
            Venue(
                name="Le Kiosque",
                capacity=999,
                address="Another address",
            )
        )


def test_schedule_valid_performance(festival: Festival) -> None:
    show = make_solo(festival)

    assert festival.schedule(show) == show
    assert festival.get_performance(show.id) == show


def test_unknown_artist_is_rejected(festival: Festival) -> None:
    show = replace(
        make_solo(festival),
        artist=Artist(name="Artiste inconnu"),
    )

    with pytest.raises(NotFoundError):
        festival.schedule(show)

    assert festival.performances == ()


def test_unknown_venue_is_rejected(festival: Festival) -> None:
    show = replace(
        make_solo(festival),
        venue=Venue(name="Lieu inconnu", capacity=10, address="Beach"),
    )

    with pytest.raises(NotFoundError):
        festival.schedule(show)


def test_inconsistent_venue_copy_is_rejected(festival: Festival) -> None:
    show = replace(
        make_solo(festival),
        venue=Venue(name="Le Kiosque", capacity=999, address="Beach"),
    )

    with pytest.raises(ValidationError):
        festival.schedule(show)


def test_duplicate_performance_id_is_rejected(festival: Festival) -> None:
    show = make_solo(festival)
    festival.schedule(show)

    with pytest.raises(ConflictError):
        festival.schedule(show)

    assert festival.performances == (show,)


@pytest.mark.parametrize(
    "start",
    [
        datetime(2027, 6, 10, 5, 59),
        datetime(2027, 6, 14, 6, 0),
    ],
)
def test_outside_festival_day_is_rejected(
    festival: Festival,
    start: datetime,
) -> None:
    with pytest.raises(ConflictError):
        festival.schedule(make_solo(festival, start=start))


def test_last_night_belongs_to_last_festival_day(
    festival: Festival,
) -> None:
    show = make_solo(
        festival,
        start=datetime(2027, 6, 14, 1),
    )

    festival.schedule(show)

    assert show.festival_day == date(2027, 6, 13)


@pytest.mark.parametrize("minute", [0, 29])
def test_insufficient_venue_break_is_rejected(
    festival: Festival,
    minute: int,
) -> None:
    festival.schedule(make_solo(festival))

    second = make_solo(
        festival,
        artist="max-pellerin",
        start=datetime(2027, 6, 11, 19, minute),
    )

    with pytest.raises(ConflictError, match="30 minutes"):
        festival.schedule(second)

    assert len(festival.performances) == 1


def test_exactly_thirty_minutes_is_allowed(festival: Festival) -> None:
    festival.schedule(make_solo(festival))

    second = make_solo(
        festival,
        start=datetime(2027, 6, 11, 19, 30),
    )

    festival.schedule(second)

    assert len(festival.performances) == 2


def test_earlier_show_also_requires_a_break(festival: Festival) -> None:
    festival.schedule(make_solo(festival, start=datetime(2027, 6, 11, 20)))

    earlier = make_solo(
        festival,
        artist="max-pellerin",
        start=datetime(2027, 6, 11, 18, 31),
    )

    with pytest.raises(ConflictError):
        festival.schedule(earlier)


def test_artist_cannot_overlap_between_venues(festival: Festival) -> None:
    festival.schedule(make_solo(festival))

    second = make_solo(
        festival,
        venue="grand-casino",
        start=datetime(2027, 6, 11, 18, 30),
    )

    with pytest.raises(ConflictError, match="Nora Lebrun"):
        festival.schedule(second)


@pytest.mark.parametrize("role", ["host", "act", "teacher"])
def test_artist_break_applies_to_every_role(
    festival: Festival,
    role: str,
) -> None:
    festival.schedule(make_solo(festival))

    common = {
        "title": "Autre représentation",
        "venue": festival.get_venue("grand-casino"),
        "start": datetime(2027, 6, 11, 19, 29),
        "duration_minutes": 60,
    }

    nora = festival.get_artist("nora-lebrun")
    paul = festival.get_artist("paul-kerbrat")
    max_artist = festival.get_artist("max-pellerin")

    if role == "teacher":
        second = Workshop(
            **common,
            teacher=nora,
            max_participants=10,
        )
    elif role == "host":
        second = Lineup(
            **common,
            host=nora,
            acts=(paul, max_artist),
        )
    else:
        second = Lineup(
            **common,
            host=paul,
            acts=(nora, max_artist),
        )

    with pytest.raises(ConflictError, match="Nora Lebrun"):
        festival.schedule(second)


def test_simultaneous_independent_shows_are_allowed(
    festival: Festival,
) -> None:
    first = make_solo(festival)
    second = make_solo(
        festival,
        venue="grand-casino",
        artist="max-pellerin",
    )

    festival.schedule(first)
    festival.schedule(second)

    assert len(festival.performances) == 2


def test_successful_move_changes_id(festival: Festival) -> None:
    original = make_solo(festival)
    festival.schedule(original)

    replacement = replace(
        original,
        start=datetime(2027, 6, 11, 20),
    )

    result = festival.update_performance(original.id, replacement)

    assert result.id != original.id
    assert festival.get_performance(result.id) == replacement

    with pytest.raises(NotFoundError):
        festival.get_performance(original.id)


def test_failed_move_keeps_original_schedule(festival: Festival) -> None:
    original = make_solo(festival)
    occupied = make_solo(
        festival,
        title="Créneau occupé",
        artist="max-pellerin",
        start=datetime(2027, 6, 11, 20),
    )

    festival.schedule(original)
    festival.schedule(occupied)
    before = festival.performances

    replacement = replace(
        original,
        start=datetime(2027, 6, 11, 20, 15),
    )

    with pytest.raises(ConflictError):
        festival.update_performance(original.id, replacement)

    assert festival.performances == before
    assert festival.get_performance(original.id) == original


def test_update_does_not_conflict_with_itself(festival: Festival) -> None:
    original = make_solo(festival)
    festival.schedule(original)

    replacement = replace(original, title="Nouveau titre")

    festival.update_performance(original.id, replacement)

    assert festival.get_performance(original.id).title == "Nouveau titre"


def test_cancel_removes_performance(festival: Festival) -> None:
    show = make_solo(festival)
    festival.schedule(show)

    assert festival.cancel(show.id) == show
    assert festival.performances == ()

    with pytest.raises(NotFoundError):
        festival.cancel(show.id)


def test_workshop_registration_updates_festival(festival: Festival) -> None:
    workshop = Workshop(
        title="Atelier",
        venue=festival.get_venue("le-kiosque"),
        start=datetime(2027, 6, 11, 10),
        duration_minutes=60,
        teacher=festival.get_artist("nora-lebrun"),
        max_participants=1,
    )

    festival.schedule(workshop)
    updated = festival.register_participant(workshop.id, " Camille R. ")

    assert updated.participants == ("Camille R.",)
    assert festival.get_performance(workshop.id) == updated

    with pytest.raises(ConflictError):
        festival.register_participant(workshop.id, "Yanis B.")

    assert festival.get_performance(workshop.id) == updated


def test_registration_on_solo_is_rejected(festival: Festival) -> None:
    show = make_solo(festival)
    festival.schedule(show)

    with pytest.raises(ValidationError):
        festival.register_participant(show.id, "Camille R.")


def test_programme_uses_festival_day(festival: Festival) -> None:
    night_show = make_solo(
        festival,
        start=datetime(2027, 6, 12, 1),
    )
    festival.schedule(night_show)

    assert festival.programme(day=date(2027, 6, 11)) == (night_show,)
    assert festival.programme(day=date(2027, 6, 12)) == ()


def test_programme_filters_by_venue(festival: Festival) -> None:
    first = make_solo(festival)
    second = make_solo(
        festival,
        venue="grand-casino",
        artist="max-pellerin",
    )

    festival.schedule(first)
    festival.schedule(second)

    assert festival.programme(venue="le-kiosque") == (first,)


def test_programme_sorts_equal_times_by_venue_name(
    festival: Festival,
) -> None:
    kiosque_show = make_solo(festival)
    casino_show = make_solo(
        festival,
        venue="grand-casino",
        artist="max-pellerin",
    )

    festival.schedule(kiosque_show)
    festival.schedule(casino_show)

    assert festival.performances == (casino_show, kiosque_show)


def test_artist_programme_contains_their_shows(festival: Festival) -> None:
    show = make_solo(festival)
    festival.schedule(show)

    assert festival.performances_for_artist("nora-lebrun") == (show,)
    assert festival.performances_for_artist("paul-kerbrat") == ()


def test_now_playing_excludes_exact_end(festival: Festival) -> None:
    show = make_solo(festival)
    festival.schedule(show)

    assert festival.now_playing(show.start) == (show,)
    assert festival.now_playing(show.end) == ()


def test_up_next_returns_three_at_most(festival: Festival) -> None:
    shows = []

    for hour in [10, 12, 14, 16]:
        show = make_solo(
            festival,
            start=datetime(2027, 6, 11, hour),
        )
        festival.schedule(show)
        shows.append(show)

    assert festival.up_next(datetime(2027, 6, 11, 9)) == tuple(shows[:3])


def test_unknown_performance_has_readable_error(
    festival: Festival,
) -> None:
    with pytest.raises(NotFoundError, match="Aucun spectacle"):
        festival.get_performance("inconnu")
