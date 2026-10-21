"""Point d'entrée du centre de contrôle Streamlit."""

import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run() -> None:
    """Configurer l'interface et afficher la page sélectionnée."""
    from streamlit_app.api_client import APIError, FestivalAPI
    from streamlit_app.components import show_hero
    from streamlit_app.views.administration import administration
    from streamlit_app.views.consultation import (
        artists_page,
        dashboard,
        programme,
        venues_page,
    )

    st.set_page_config(
        page_title="Festival OS · Deauville",
        page_icon="🎭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    css_path = Path(__file__).parent / "assets" / "styles.css"

    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        st.html(f"<style>{css}</style>")

    api_url = os.environ.get(
        "FESTIVAL_API_URL",
        "http://127.0.0.1:8000",
    )
    api = FestivalAPI(api_url)

    with st.sidebar:
        st.markdown("## 🎭 Festival OS")
        st.caption("Deauville · Centre de contrôle")
        st.divider()

        page = st.radio(
            "Navigation",
            [
                "Tableau de bord",
                "Programme",
                "Artistes",
                "Lieux",
                "Administration",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption(f"API : {api_url}")
        st.caption("Les heures affichées sont celles du festival.")

        if st.button("Actualiser les données"):
            st.rerun()

    try:
        festival = api.get("/api/festival")
        artists = api.get("/api/artists")
        venues = api.get("/api/venues")
        performances = api.get("/api/programme")

        show_hero(festival)

        message = st.session_state.pop("success_message", None)

        if message:
            st.success(message)

        if page == "Tableau de bord":
            dashboard(api, festival, artists, venues, performances)
        elif page == "Programme":
            programme(api, festival, venues)
        elif page == "Artistes":
            artists_page(api, artists)
        elif page == "Lieux":
            venues_page(venues, performances)
        else:
            administration(
                api,
                festival,
                artists,
                venues,
                performances,
            )

    except APIError as error:
        st.error(str(error))
        st.info(
            "Si FastAPI n'est pas démarré, ouvre un autre terminal à la racine du projet et lance :"
        )
        st.code(
            "uv run uvicorn festival.api.app:app --app-dir src --reload",
            language="powershell",
        )


if __name__ == "__main__":
    run()
