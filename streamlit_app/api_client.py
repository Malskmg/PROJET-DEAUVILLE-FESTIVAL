"""Client HTTP de l'interface Streamlit."""

from typing import Any

import httpx


class APIError(Exception):
    """Erreur HTTP compréhensible par l'utilisateur."""


def error_message(response: httpx.Response) -> str:
    """Extraire une phrase depuis une réponse d'erreur."""
    try:
        payload = response.json()
    except ValueError:
        return f"Le serveur a renvoyé une erreur HTTP {response.status_code}."

    if not isinstance(payload, dict):
        return f"Réponse d'erreur inattendue : HTTP {response.status_code}."

    detail = payload.get("detail")

    if isinstance(detail, str):
        return detail

    if isinstance(detail, list):
        messages = []

        for problem in detail:
            if not isinstance(problem, dict):
                continue

            location = ".".join(
                str(part)
                for part in problem.get("loc", [])
                if part not in ("body", "query", "path")
            )
            message = str(problem.get("msg", "Valeur invalide"))
            messages.append(f"{location} : {message}" if location else message)

        return " / ".join(messages) or "La requête est invalide."

    return f"Le serveur a renvoyé une erreur HTTP {response.status_code}."


class FestivalAPI:
    """Effectuer les appels au serveur FastAPI."""

    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Envoyer une requête et contrôler sa réponse."""
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=15.0,
                transport=self.transport,
            ) as client:
                response = client.request(
                    method,
                    path,
                    params=params,
                    json=body,
                )

        except httpx.TimeoutException as error:
            raise APIError(
                "Le serveur met trop de temps à répondre. Vérifiez son terminal avant de réessayer."
            ) from error

        except httpx.RequestError as error:
            raise APIError(
                "Impossible de joindre FastAPI. Vérifiez que le serveur "
                f"est démarré à l'adresse {self.base_url}."
            ) from error

        if response.is_error:
            raise APIError(error_message(response))

        if response.status_code == 204:
            return None

        try:
            return response.json()
        except ValueError as error:
            raise APIError(
                "Le serveur n'a pas renvoyé une réponse JSON valide. Vérifiez l'adresse de l'API."
            ) from error

    def get(
        self,
        path: str,
        **params: Any,
    ) -> Any:
        clean_params = {key: value for key, value in params.items() if value is not None}

        return self.request("GET", path, params=clean_params)

    def post(self, path: str, body: dict[str, Any]) -> Any:
        return self.request("POST", path, body=body)

    def put(self, path: str, body: dict[str, Any]) -> Any:
        return self.request("PUT", path, body=body)

    def delete(self, path: str) -> None:
        self.request("DELETE", path)
