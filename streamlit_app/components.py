"""Composants visuels partagés."""

from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

KIND_LABELS = {
    "solo": "Solo",
    "lineup": "Plateau",
    "workshop": "Atelier",
}


def show_hero(festival: dict[str, Any]) -> None:
    """Afficher le bandeau principal."""
    first_day = datetime.fromisoformat(festival["first_day"]).strftime("%d/%m/%Y")

    last_day = datetime.fromisoformat(festival["last_day"]).strftime("%d/%m/%Y")

    st.html(
        f"""
        <div class="festival-hero">
            <span class="festival-tag">FESTIVAL CONTROL CENTER</span>
            <h1>{escape(festival["name"])}</h1>
            <p>Programmation et opérations · {first_day} → {last_day}</p>
        </div>
        """
    )


def show_performance(performance: dict[str, Any]) -> None:
    """Afficher une carte de représentation."""
    start = datetime.fromisoformat(performance["start"])
    end = datetime.fromisoformat(performance["end"])
    kind = performance["kind"]
    label = KIND_LABELS.get(kind, kind)
    safe_kind = kind if kind in KIND_LABELS else "solo"

    description = escape(performance.get("description", ""))
    summary = escape(performance["summary"])

    extra = f"Capacité : {performance['capacity']} places"

    if kind == "workshop":
        extra += f" · Places restantes : {performance['places_left']}"
    elif kind == "solo":
        extra += f" · Âge minimum : {performance['min_age']} ans"

    st.html(
        f"""
        <div class="festival-card performance-card">
            <div class="performance-top">
                <span class="festival-tag {safe_kind}">
                    {escape(label)}
                </span>
                <span class="performance-time">
                    {start:%d/%m %H:%M} → {end:%d/%m %H:%M}
                </span>
            </div>
            <h3>{escape(performance["title"])}</h3>
            <p class="performance-venue">
                {escape(performance["venue_name"])}
            </p>
            <p>{summary}</p>
            <p class="performance-description">{description}</p>
            <div class="performance-footer">{escape(extra)}</div>
        </div>
        """
    )


def show_performances(performances: list[dict[str, Any]]) -> None:
    if not performances:
        st.info("Aucun spectacle ne correspond à cette sélection.")
        return

    for performance in performances:
        show_performance(performance)


def success_and_refresh(message: str) -> None:
    """Conserver la confirmation pendant le rafraîchissement."""
    st.session_state["success_message"] = message
    st.rerun()


def performance_label(performance: dict[str, Any]) -> str:
    return (
        f"{performance['start'][:16].replace('T', ' ')} · "
        f"{performance['title']} · {performance['venue_name']}"
    )
