"""Notification push via ntfy.sh (optionnelle)."""

import httpx


def push(topic: str, title: str, message: str) -> None:
    if not topic:
        return
    # Titre passé en paramètre d'URL : les en-têtes HTTP n'acceptent pas les accents
    httpx.post(
        f"https://ntfy.sh/{topic}",
        params={"title": title, "tags": "bulb"},
        content=message.encode("utf-8"),
        timeout=15,
    )
