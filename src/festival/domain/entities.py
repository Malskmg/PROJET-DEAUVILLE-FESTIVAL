"""Artistes et lieux du festival."""

from dataclasses import dataclass

from festival.domain.errors import ValidationError
from festival.domain.identifiers import make_slug, normalize_name


def validate_text(value: str, label: str) -> str:
    """Vérifier un texte pouvant être vide."""
    if not isinstance(value, str):
        raise ValidationError(f"{label} doit être une chaîne de caractères.")

    return value


def validate_integer(
    value: int,
    label: str,
    minimum: int,
    maximum: int | None = None,
) -> int:
    """Vérifier un entier en excluant explicitement les booléens."""
    if type(value) is not int:
        raise ValidationError(f"{label} doit être un nombre entier.")

    if value < minimum:
        raise ValidationError(f"{label} doit être au moins égal à {minimum}.")

    if maximum is not None and value > maximum:
        raise ValidationError(f"{label} doit être au maximum égal à {maximum}.")

    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class Artist:
    """Artiste identifié par le slug de son nom."""

    name: str
    bio: str = ""
    photo_url: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", normalize_name(self.name))
        validate_text(self.bio, "La biographie")
        validate_text(self.photo_url, "L'adresse de la photo")
        make_slug(self.name)

    @property
    def slug(self) -> str:
        """Identifiant de l'artiste."""
        return make_slug(self.name)


@dataclass(frozen=True, slots=True, kw_only=True)
class Venue:
    """Lieu de représentation et nombre de places disponibles."""

    name: str
    capacity: int
    address: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", normalize_name(self.name))
        validate_integer(self.capacity, "La capacité du lieu", minimum=1)
        validate_text(self.address, "L'adresse")
        make_slug(self.name)

    @property
    def slug(self) -> str:
        """Identifiant du lieu."""
        return make_slug(self.name)
