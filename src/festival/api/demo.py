"""Application de démonstration utilisant une copie des données."""

from fastapi import FastAPI

from festival.api.app import PROJECT_ROOT, create_app


def create_demo_app() -> FastAPI:
    return create_app(data_path=PROJECT_ROOT / "data" / "festival.demo.json")
