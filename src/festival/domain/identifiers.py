"""Nettoyage des noms et génération des slugs."""

import re
import unicodedata

from festival.domain.errors import ValidationError


def normalize_name(value: str) -> str:
    """Nettoyer les espaces autour d'un nom et refuser un nom vide."""
    if not isinstance(value, str):
        raise ValidationError("Le nom doit être une chaîne de caractères.")

    normalized = value.strip()

    if not normalized:
        raise ValidationError("Le nom ne peut pas être vide.")

    return normalized


def make_slug(value: str) -> str:
    """Transformer un nom en identifiant ASCII avec tirets."""
    normalized = normalize_name(value)

    replacements = {
        "œ": "oe",
        "Œ": "OE",
        "æ": "ae",
        "Æ": "AE",
        "ß": "ss",
    }

    for character, replacement in replacements.items():
        normalized = normalized.replace(character, replacement)

    decomposed = unicodedata.normalize("NFKD", normalized)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    lowercase = ascii_text.lower()

    spaced = re.sub(r"\s+", "-", lowercase)
    cleaned = re.sub(r"[^a-z0-9-]", "", spaced)
    slug = re.sub(r"-+", "-", cleaned).strip("-")

    if not slug:
        raise ValidationError("Ce nom ne permet pas de créer un identifiant valide.")

    return slug
