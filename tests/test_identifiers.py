"""Tests des noms et des slugs."""

import pytest

from festival.domain.errors import ValidationError
from festival.domain.identifiers import make_slug, normalize_name


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Théâtre des Planches", "theatre-des-planches"),
        ("Élodie  Marchal !", "elodie-marchal"),
        ("Grand Casino", "grand-casino"),
        ("  Le Kiosque  ", "le-kiosque"),
        ("Cœur de scène", "coeur-de-scene"),
    ],
)
def test_make_slug(value: str, expected: str) -> None:
    assert make_slug(value) == expected


def test_normalize_name_removes_surrounding_spaces() -> None:
    assert normalize_name("  Nora Lebrun  ") == "Nora Lebrun"


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_empty_name_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        normalize_name(value)


def test_unusable_slug_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_slug("!!!")
