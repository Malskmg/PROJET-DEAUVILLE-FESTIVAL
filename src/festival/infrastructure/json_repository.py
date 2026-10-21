"""Dépôt JSON avec revalidation et remplacement après écriture complète."""

import json
import os
import tempfile
from pathlib import Path

from festival.application.ports import FestivalRepository
from festival.domain.errors import FestivalError, StorageError
from festival.domain.festival import Festival
from festival.infrastructure.serialization import (
    festival_from_data,
    festival_to_data,
)


class JsonFestivalRepository(FestivalRepository):
    """Stocker un festival dans un fichier JSON."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> Festival:
        """Lire le fichier et revalider toutes les règles métier."""
        try:
            content = self.path.read_text(encoding="utf-8-sig")
            data = json.loads(content)
            return festival_from_data(data)

        except json.JSONDecodeError as error:
            raise StorageError(
                f"Le fichier '{self.path}' contient un JSON invalide "
                f"à la ligne {error.lineno}, colonne {error.colno}."
            ) from error

        except KeyError as error:
            raise StorageError(
                f"Le fichier '{self.path}' est incomplet : "
                f"champ obligatoire absent : {error.args[0]}."
            ) from error

        except FestivalError as error:
            raise StorageError(f"Les données de '{self.path}' sont invalides : {error}") from error

        except (TypeError, ValueError, OverflowError) as error:
            raise StorageError(
                f"Le fichier '{self.path}' contient une valeur invalide : {error}"
            ) from error

        except OSError as error:
            raise StorageError(
                f"Impossible de lire '{self.path}'. Vérifiez le chemin et les droits d'accès."
            ) from error

    def save(self, festival: Festival) -> None:
        """Écrire un état validé avant de remplacer le fichier cible."""
        temporary_path: Path | None = None

        try:
            data = festival_to_data(festival)

            # Revalider aussi avant l'écriture.
            festival_from_data(data)

            content = json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(content)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())

            os.replace(temporary_path, self.path)

        except (OSError, TypeError, ValueError, FestivalError) as error:
            raise StorageError(f"Impossible de sauvegarder '{self.path}' : {error}") from error

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
