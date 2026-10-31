"""Collecte Hacker News via l'API publique Algolia (aucune clé nécessaire).

On cherche les formulations qui trahissent un besoin non couvert :
"is there a tool", "I wish there was", "I would pay for"...
"""

import html
import re
from datetime import UTC, datetime, timedelta

import httpx

from ..models import Signal, Source

API = "https://hn.algolia.com/api/v1"

PAIN_QUERIES = [
    '"is there a tool"',
    '"is there an app"',
    '"I wish there was"',
    '"I would pay for"',
    '"why is there no"',
    '"looking for a tool"',
]

TAG_RE = re.compile(r"<[^>]+>")


def clean(text: str | None) -> str:
    return html.unescape(TAG_RE.sub(" ", text or "")).strip()


class HackerNewsCollector:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(base_url=API, timeout=30)

    def _search(self, query: str, tags: str, since: datetime, hits: int) -> list[dict]:
        r = self.client.get(
            "/search_by_date",
            params={
                "query": query,
                "tags": tags,
                "numericFilters": f"created_at_i>{int(since.timestamp())}",
                "hitsPerPage": hits,
            },
        )
        r.raise_for_status()
        return r.json().get("hits", [])

    def pain_comments(self, since: datetime, per_query: int = 30) -> list[Signal]:
        signals: dict[str, Signal] = {}
        for q in PAIN_QUERIES:
            for h in self._search(q, "comment", since, per_query):
                text = clean(h.get("comment_text"))
                if len(text) < 60:  # trop court pour contenir un vrai besoin
                    continue
                sid = f"hn:{h['objectID']}"
                signals[sid] = Signal(
                    id=sid,
                    source=Source.HACKERNEWS,
                    title=clean(h.get("story_title")) or "Commentaire HN",
                    body=text[:3000],
                    url=f"https://news.ycombinator.com/item?id={h['objectID']}",
                    engagement=h.get("points") or 0,
                    created_at=datetime.fromtimestamp(h["created_at_i"], UTC),
                    extra={"query": q},
                )
        return list(signals.values())

    def ask_hn(self, since: datetime, hits: int = 30) -> list[Signal]:
        out = []
        for h in self._search("", "ask_hn", since, hits):
            if (h.get("points") or 0) < 20:
                continue
            out.append(
                Signal(
                    id=f"hn:{h['objectID']}",
                    source=Source.HACKERNEWS,
                    title=clean(h.get("title")),
                    body=clean(h.get("story_text"))[:3000],
                    url=f"https://news.ycombinator.com/item?id={h['objectID']}",
                    engagement=h.get("points") or 0,
                    created_at=datetime.fromtimestamp(h["created_at_i"], UTC),
                    extra={"comments": h.get("num_comments", 0), "type": "ask_hn"},
                )
            )
        return out

    def collect(self, lookback_days: int) -> list[Signal]:
        since = datetime.now(UTC) - timedelta(days=lookback_days)
        return self.pain_comments(since) + self.ask_hn(since)
