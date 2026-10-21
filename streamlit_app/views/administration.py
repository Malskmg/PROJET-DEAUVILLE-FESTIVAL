"""Formulaires administratifs utilisant uniquement l'API HTTP."""

from datetime import date, datetime, time
from typing import Any

import streamlit as st
from streamlit_app.api_client import FestivalAPI
from streamlit_app.components import (
    KIND_LABELS,
    performance_label,
    success_and_refresh,
)


def artist_form(api: FestivalAPI) -> None:
    st.markdown("### Ajouter un artiste")

    with st.form("create_artist", clear_on_submit=True):
        name = st.text_input("Nom")
        bio = st.text_area("Biographie")
        photo_url = st.text_input("URL de la photo — facultatif")

        submitted = st.form_submit_button("Créer l'artiste")

    if submitted:
        api.post(
            "/api/artists",
            {
                "name": name,
                "bio": bio,
                "photo_url": photo_url,
            },
        )
        success_and_refresh("L'artiste a été ajouté et sauvegardé.")


def performance_form(
    api: FestivalAPI,
    festival: dict[str, Any],
    artists: list[dict[str, Any]],
    venues: list[dict[str, Any]],
    existing: dict[str, Any] | None = None,
) -> None:
    if not artists or not venues:
        st.warning("Ajoutez d'abord des artistes et des lieux.")
        return

    artist_names = {artist["slug"]: artist["name"] for artist in artists}
    venue_names = {venue["slug"]: venue["name"] for venue in venues}

    artist_slugs = list(artist_names)
    venue_slugs = list(venue_names)
    kinds = list(KIND_LABELS)
    prefix = existing["id"] if existing else "new"

    kind = st.selectbox(
        "Type de représentation",
        kinds,
        index=kinds.index(existing["kind"]) if existing else 0,
        format_func=lambda value: KIND_LABELS[value],
        key=f"{prefix}_kind",
    )

    start = (
        datetime.fromisoformat(existing["start"])
        if existing
        else datetime.combine(
            date.fromisoformat(festival["first_day"]),
            time(18, 0),
        )
    )

    same_kind = existing is not None and existing["kind"] == kind
    current = existing or {}

    with st.form(f"performance_{prefix}_{kind}"):
        title = st.text_input(
            "Titre",
            value=current.get("title", ""),
        )

        selected_venue = st.selectbox(
            "Lieu",
            venue_slugs,
            index=(venue_slugs.index(current["venue"]) if existing else 0),
            format_func=lambda slug: venue_names[slug],
        )

        left, right = st.columns(2)

        selected_date = left.date_input(
            "Date civile de début",
            value=start.date(),
        )
        selected_time = right.time_input(
            "Heure locale de début",
            value=start.time(),
            step=60,
        )

        duration = st.number_input(
            "Durée en minutes",
            min_value=1,
            max_value=360,
            value=current.get("duration_minutes", 60),
            step=1,
        )

        description = st.text_area(
            "Description",
            value=current.get("description", ""),
        )

        specific: dict[str, Any] = {}

        if kind == "solo":
            default_artist = current["artist"] if same_kind else artist_slugs[0]

            specific["artist"] = st.selectbox(
                "Artiste",
                artist_slugs,
                index=artist_slugs.index(default_artist),
                format_func=lambda slug: artist_names[slug],
            )

            specific["min_age"] = st.number_input(
                "Âge minimum du public",
                min_value=0,
                max_value=18,
                value=current.get("min_age", 0) if same_kind else 0,
                step=1,
            )

        elif kind == "lineup":
            default_host = current["host"] if same_kind else artist_slugs[0]

            specific["host"] = st.selectbox(
                "Présentateur",
                artist_slugs,
                index=artist_slugs.index(default_host),
                format_func=lambda slug: artist_names[slug],
            )

            specific["acts"] = st.multiselect(
                "Artistes du plateau — au moins deux",
                artist_slugs,
                default=current["acts"] if same_kind else [],
                format_func=lambda slug: artist_names[slug],
            )

            st.caption(
                "L'ordre des artistes sélectionnés est l'ordre envoyé "
                "à l'API. Le présentateur ne doit pas être dans cette liste."
            )

        else:
            default_teacher = current["teacher"] if same_kind else artist_slugs[0]

            specific["teacher"] = st.selectbox(
                "Animateur",
                artist_slugs,
                index=artist_slugs.index(default_teacher),
                format_func=lambda slug: artist_names[slug],
            )

            specific["max_participants"] = st.number_input(
                "Nombre maximum de participants",
                min_value=1,
                value=(current["max_participants"] if same_kind else 12),
                step=1,
            )

            participants_text = st.text_area(
                "Participants — une personne par ligne",
                value=("\n".join(current["participants"]) if same_kind else ""),
            )

            specific["participants"] = [
                name.strip() for name in participants_text.splitlines() if name.strip()
            ]

        st.caption(
            "Le serveur vérifiera les dates, les références, "
            "les capacités et les pauses de 30 minutes."
        )

        confirmed = st.checkbox("Je confirme les informations à enregistrer.")

        submitted = st.form_submit_button(
            "Enregistrer les modifications" if existing else "Programmer le spectacle"
        )

    if submitted:
        if not confirmed:
            st.warning("Coche la confirmation avant d'enregistrer.")
            return

        body = {
            "kind": kind,
            "title": title,
            "venue": selected_venue,
            "start": datetime.combine(
                selected_date,
                selected_time,
            ).isoformat(),
            "duration_minutes": int(duration),
            "description": description,
            **specific,
        }

        if existing:
            result = api.put(
                f"/api/performances/{existing['id']}",
                body,
            )
            message = f"Spectacle modifié et sauvegardé. Identifiant : {result['id']}"
        else:
            result = api.post("/api/performances", body)
            message = f"Spectacle programmé et sauvegardé. Identifiant : {result['id']}"

        success_and_refresh(message)


def administration(
    api: FestivalAPI,
    festival: dict[str, Any],
    artists: list[dict[str, Any]],
    venues: list[dict[str, Any]],
    performances: list[dict[str, Any]],
) -> None:
    st.subheader("Centre d'administration")
    st.warning("Les actions validées ici modifient réellement les données du serveur connecté.")

    action = st.selectbox(
        "Opération",
        [
            "Programmer un spectacle",
            "Modifier ou déplacer",
            "Annuler un spectacle",
            "Ajouter un artiste",
            "Inscrire à un atelier",
        ],
    )

    if action == "Ajouter un artiste":
        artist_form(api)
        return

    if action == "Programmer un spectacle":
        performance_form(api, festival, artists, venues)
        return

    choices = performances

    if action == "Inscrire à un atelier":
        choices = [performance for performance in performances if performance["kind"] == "workshop"]

    if not choices:
        st.info("Aucune représentation disponible pour cette opération.")
        return

    by_id = {performance["id"]: performance for performance in choices}

    selected_id = st.selectbox(
        "Représentation",
        list(by_id),
        format_func=lambda value: performance_label(by_id[value]),
        key=f"target_{action}",
    )
    selected = by_id[selected_id]

    if action == "Modifier ou déplacer":
        performance_form(
            api,
            festival,
            artists,
            venues,
            existing=selected,
        )

    elif action == "Annuler un spectacle":
        st.write(f"Annulation de : {selected['title']} — {selected['venue_name']}")

        with st.form(f"cancel_{selected_id}"):
            confirmed = st.checkbox("Je confirme l'annulation de ce spectacle.")
            submitted = st.form_submit_button("Annuler définitivement")

        if submitted:
            if not confirmed:
                st.warning("Confirme l'annulation avec la case.")
                return

            api.delete(f"/api/performances/{selected_id}")
            success_and_refresh("Le spectacle a été annulé.")

    else:
        st.metric("Places restantes", selected["places_left"])

        with st.expander("Participants inscrits"):
            for participant in selected["participants"]:
                st.write(participant)

        with st.form(f"registration_{selected_id}"):
            name = st.text_input("Nom du participant")
            submitted = st.form_submit_button("Inscrire")

        if submitted:
            api.post(
                f"/api/performances/{selected_id}/participants",
                {"name": name},
            )
            success_and_refresh("L'inscription a été enregistrée et sauvegardée.")
