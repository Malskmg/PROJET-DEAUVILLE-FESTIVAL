"""Consultation du festival depuis le terminal."""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from festival.application.services import FestivalService
from festival.domain.errors import FestivalError
from festival.domain.performances import Performance
from festival.infrastructure.json_repository import JsonFestivalRepository


def parse_day_argument(value: str) -> date:
    """Convertir un argument en date."""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Utilisez une date comme 2027-06-11.") from error


def parse_moment_argument(value: str) -> datetime:
    """Convertir un argument en moment local."""
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Utilisez une date et une heure comme 2027-06-11T21:00."
        ) from error

    if "T" not in value or moment.tzinfo is not None:
        raise argparse.ArgumentTypeError(
            "Utilisez une date et une heure locales sans fuseau horaire."
        )

    return moment


def print_performances(
    performances: tuple[Performance, ...],
) -> None:
    """Afficher une liste ordonnée de spectacles."""
    if not performances:
        print("Aucun spectacle.")
        return

    for performance in performances:
        print(
            f"{performance.start:%d/%m %H:%M} -> "
            f"{performance.end:%d/%m %H:%M} | "
            f"{performance.venue.name} | "
            f"{performance.title} [{performance.kind}]"
        )
        print(f"    {performance.summary}")


def build_parser(default_data_path: Path) -> argparse.ArgumentParser:
    """Définir les commandes et leurs arguments."""
    parser = argparse.ArgumentParser(description="Gestion du Festival du Rire de Deauville.")
    parser.add_argument(
        "--data",
        type=Path,
        default=default_data_path,
        help="Chemin du fichier JSON.",
    )

    commands = parser.add_subparsers(dest="command")

    commands.add_parser("summary", help="Résumé du festival.")

    programme = commands.add_parser(
        "programme",
        help="Programme d'une journée.",
    )
    programme.add_argument(
        "--day",
        required=True,
        type=parse_day_argument,
    )
    programme.add_argument(
        "--venue",
        help="Slug d'un lieu, par exemple le-kiosque.",
    )

    commands.add_parser(
        "artists",
        help="Artistes et nombre de spectacles.",
    )

    now = commands.add_parser(
        "now",
        help="Sur scène et trois prochains spectacles.",
    )
    now.add_argument(
        "--at",
        type=parse_moment_argument,
        help="Moment local, par exemple 2027-06-11T21:00.",
    )

    return parser


def main(
    argv: list[str] | None = None,
    *,
    default_data_path: Path,
) -> int:
    """Exécuter la commande et retourner un code de sortie."""
    parser = build_parser(default_data_path)
    arguments = parser.parse_args(argv)

    try:
        repository = JsonFestivalRepository(arguments.data)
        service = FestivalService(repository)
        festival = service.festival

        if arguments.command in (None, "summary"):
            print(festival.name)
            print(f"Du {festival.first_day:%d/%m/%Y} au {festival.last_day:%d/%m/%Y}")
            print(
                f"{len(festival.venues)} lieux | "
                f"{len(festival.artists)} artistes | "
                f"{len(festival.performances)} représentations"
            )

        elif arguments.command == "programme":
            print(f"Programme de la journée du {arguments.day:%d/%m/%Y}")
            print_performances(
                festival.programme(
                    day=arguments.day,
                    venue=arguments.venue,
                )
            )

        elif arguments.command == "artists":
            for artist in festival.artists:
                count = len(festival.performances_for_artist(artist.slug))
                print(f"{artist.name} : {count} représentation(s)")

        elif arguments.command == "now":
            moment = arguments.at or datetime.now()

            print(f"Situation au {moment:%d/%m/%Y %H:%M}")
            print("\nSUR SCÈNE")
            print_performances(festival.now_playing(moment))

            print("\nÀ SUIVRE")
            print_performances(festival.up_next(moment))

    except FestivalError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1

    return 0
