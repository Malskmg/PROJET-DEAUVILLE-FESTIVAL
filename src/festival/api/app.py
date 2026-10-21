"""Création et configuration de l'application FastAPI."""

from pathlib import Path
from threading import RLock

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from festival.api.routes import router
from festival.domain.errors import (
    ConflictError,
    FestivalError,
    NotFoundError,
    StorageError,
    ValidationError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def create_app(
    *,
    data_path: str | Path | None = None,
    web_root: str | Path | None = None,
) -> FastAPI:
    """Créer une application isolable pour les tests."""
    application = FastAPI(
        title="Deauville Festival du Rire",
        description="API de programmation du festival.",
        version="0.4.0",
    )

    application.state.data_path = Path(
        data_path if data_path is not None else PROJECT_ROOT / "data" / "festival.json"
    )
    application.state.service = None
    application.state.service_lock = RLock()

    @application.exception_handler(FestivalError)
    async def handle_festival_error(
        request: Request,
        error: FestivalError,
    ) -> JSONResponse:
        if isinstance(error, NotFoundError):
            status_code = 404
        elif isinstance(error, ConflictError):
            status_code = 409
        elif isinstance(error, ValidationError):
            status_code = 422
        elif isinstance(error, StorageError):
            status_code = 500
        else:
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content={"detail": str(error)},
        )

    # Toujours enregistrer les routes API avant le montage de "/".
    application.include_router(router)

    root = Path(web_root if web_root is not None else PROJECT_ROOT / "web")
    public_directory = root / "public"
    admin_directory = root / "admin"

    if (admin_directory / "index.html").is_file():
        application.mount(
            "/admin",
            StaticFiles(directory=admin_directory, html=True),
            name="admin",
        )
    else:

        @application.get(
            "/admin/",
            response_class=HTMLResponse,
            include_in_schema=False,
        )
        def missing_admin() -> str:
            return (
                "<h1>Administration HTML non installée</h1>"
                "<p>Placez les fichiers dans web/admin/.</p>"
                '<p><a href="/docs">Ouvrir la documentation API</a></p>'
            )

    if (public_directory / "index.html").is_file():
        application.mount(
            "/",
            StaticFiles(directory=public_directory, html=True),
            name="public",
        )
    else:

        @application.get(
            "/",
            response_class=HTMLResponse,
            include_in_schema=False,
        )
        def home() -> str:
            return (
                "<h1>Deauville Festival du Rire — API</h1>"
                "<p>Le serveur HTTP est démarré.</p>"
                '<p><a href="/docs">Documentation interactive</a></p>'
                '<p><a href="/api/festival">Informations du festival</a></p>'
                "<p>Le site public sera servi depuis web/public/.</p>"
            )

    return application


app = create_app()
