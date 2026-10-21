"""Pages de consultation du festival."""

from datetime import date, datetime, time
from typing import Any

import streamlit as st
from streamlit_app.api_client import FestivalAPI
from streamlit_app.components import (
    KIND_LABELS,
    show_performances,
)


def dashboard(
    api: FestivalAPI,
    festival: dict[str, Any],
    artists: list[dict[str, Any]],
    venues: list[dict[str, Any]],
    performances: list[dict[str, Any]],
) -> None:
    st.subheader("Vue d'ensemble")

    columns = st.columns(4)

    columns[0].metric("Représentations", len(performances))
    columns[1].metric("Artistes", len(artists))
    columns[2].metric("Lieux", len(venues))
    columns[3].metric(
        "Places proposées en atelier",
        sum(
            performance["capacity"]
            for performance in performances
            if performance["kind"] == "workshop"
        ),
    )

    st.caption(
        "L'indicateur des ateliers additionne les capacités des sessions. "
        "Il ne représente ni des ventes ni des participants uniques."
    )

    st.divider()
    st.subheader("Sur scène et à suivre")

    mode = st.radio(
        "Moment de consultation",
        ["Simulation", "Maintenant à Deauville"],
        horizontal=True,
    )

    if mode == "Simulation":
        left, right = st.columns(2)

        selected_day = left.date_input(
            "Date civile",
            value=date.fromisoformat(festival["first_day"]),
        )
        selected_time = right.time_input(
            "Heure locale",
            value=time(21, 0),
            step=60,
        )

        moment = datetime.combine(selected_day, selected_time)
        situation = api.get("/api/now", at=moment.isoformat())
    else:
        situation = api.get("/api/now")

    st.caption(f"Situation au {situation['at'].replace('T', ' ')}")

    left, right = st.columns(2)

    with left:
        st.markdown("### Sur scène")
        show_performances(situation["now_playing"])

    with right:
        st.markdown("### Trois prochains spectacles")
        show_performances(situation["up_next"])

    st.divider()
    st.subheader("Répartition du programme")

    st.dataframe(
        [
            {
                "Type": label,
                "Représentations": sum(performance["kind"] == kind for performance in performances),
            }
            for kind, label in KIND_LABELS.items()
        ],
        hide_index=True,
        use_container_width=True,
    )


def programme(
    api: FestivalAPI,
    festival: dict[str, Any],
    venues: list[dict[str, Any]],
) -> None:
    st.subheader("Explorer le programme")

    venue_names = {venue["slug"]: venue["name"] for venue in venues}

    first, second, third = st.columns(3)

    selected_day = first.selectbox(
        "Journée du festival",
        [None, *festival["days"]],
        format_func=lambda value: "Toutes les journées" if value is None else value,
    )

    selected_venue = second.selectbox(
        "Lieu",
        [None, *venue_names],
        format_func=lambda value: "Tous les lieux" if value is None else venue_names[value],
    )

    selected_kind = third.selectbox(
        "Type",
        [None, *KIND_LABELS],
        format_func=lambda value: "Tous les types" if value is None else KIND_LABELS[value],
    )

    search = st.text_input("Rechercher un titre")

    performances = api.get(
        "/api/programme",
        day=selected_day,
        venue=selected_venue,
    )

    filtered = [
        performance
        for performance in performances
        if (selected_kind is None or performance["kind"] == selected_kind)
        and search.casefold() in performance["title"].casefold()
    ]

    st.caption(f"{len(filtered)} représentation(s). Une journée du festival se termine à 06 h.")
    show_performances(filtered)


def artists_page(
    api: FestivalAPI,
    artists: list[dict[str, Any]],
) -> None:
    st.subheader("Les artistes")

    if not artists:
        st.info("Aucun artiste enregistré.")
        return

    names = {artist["slug"]: artist["name"] for artist in artists}

    selected_slug = st.selectbox(
        "Choisir un artiste",
        list(names),
        format_func=lambda slug: names[slug],
    )

    artist = api.get(f"/api/artists/{selected_slug}")

    st.markdown(f"### {artist['name']}")
    st.write(artist["bio"] or "Biographie non renseignée.")
    st.metric("Représentations", len(artist["performances"]))

    show_performances(artist["performances"])


def venues_page(
    venues: list[dict[str, Any]],
    performances: list[dict[str, Any]],
) -> None:
    st.subheader("Les lieux")

    for venue in venues:
        with st.container(border=True):
            st.markdown(f"### {venue['name']}")
            st.write(venue["address"])

            left, right = st.columns(2)
            left.metric("Places", venue["capacity"])
            right.metric(
                "Représentations",
                sum(performance["venue"] == venue["slug"] for performance in performances),
            )
