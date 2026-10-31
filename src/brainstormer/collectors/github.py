"""Collecte GitHub via l'API officielle de recherche.

Deux signaux :
- repos récents à croissance rapide -> concepts qui émergent, et opportunités
  "version hébergée" d'un projet open source populaire ;
- issues de type feature request très votées -> besoins explicitement exprimés.
"""

from datetime import UTC, datetime, timedelta

import httpx

from ..models import Signal, Source

API = "https://api.github.com"

ISSUE_QUERIES = [
    "is:issue is:open label:enhancement",
    'is:issue is:open label:"feature request"',
    'is:issue is:open "feature request" in:title',
]


class GitHubCollector:
    def __init__(self, token: str = "", client: httpx.Client | None = None):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "brainstormer",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = client or httpx.Client(base_url=API, headers=headers, timeout=30)

    def _search(self, kind: str, q: str, sort: str, per_page: int) -> list[dict]:
        r = self.client.get(
            f"/search/{kind}",
            params={"q": q, "sort": sort, "order": "desc", "per_page": per_page},
        )
        r.raise_for_status()
        return r.json().get("items", [])

    def rising_repos(self, since: datetime, min_stars: int = 50, limit: int = 30) -> list[Signal]:
        q = f"created:>={since:%Y-%m-%d} stars:>={min_stars}"
        signals = []
        for it in self._search("repositories", q, "stars", limit):
            created = datetime.fromisoformat(it["created_at"].replace("Z", "+00:00"))
            age_days = max((datetime.now(UTC) - created).days, 1)
            stars = it.get("stargazers_count", 0)
            signals.append(
                Signal(
                    id=f"gh_repo:{it['id']}",
                    source=Source.GITHUB_REPO,
                    title=it["full_name"],
                    body=(it.get("description") or "")[:2000],
                    url=it["html_url"],
                    engagement=stars,
                    created_at=created,
                    extra={
                        "stars_per_day": round(stars / age_days, 1),
                        "topics": it.get("topics", []),
                        "language": it.get("language"),
                        "has_homepage": bool(it.get("homepage")),
                    },
                )
            )
        return signals

    def hot_feature_requests(
        self, since: datetime, min_reactions: int = 10, per_query: int = 20
    ) -> list[Signal]:
        signals: dict[str, Signal] = {}
        for base in ISSUE_QUERIES:
            q = f"{base} created:>={since:%Y-%m-%d} reactions:>={min_reactions}"
            for it in self._search("issues", q, "reactions", per_query):
                sid = f"gh_issue:{it['id']}"
                repo = it["repository_url"].removeprefix(f"{API}/repos/")
                signals[sid] = Signal(
                    id=sid,
                    source=Source.GITHUB_ISSUE,
                    title=f"[{repo}] {it['title']}",
                    body=(it.get("body") or "")[:3000],
                    url=it["html_url"],
                    engagement=it.get("reactions", {}).get("total_count", 0),
                    created_at=datetime.fromisoformat(it["created_at"].replace("Z", "+00:00")),
                    extra={"repo": repo, "comments": it.get("comments", 0)},
                )
        return list(signals.values())

    def collect(self, lookback_days: int) -> list[Signal]:
        since = datetime.now(UTC) - timedelta(days=lookback_days)
        # Les issues anciennes mais toujours votées sont intéressantes : fenêtre plus large
        issues_since = datetime.now(UTC) - timedelta(days=max(lookback_days, 90))
        return self.rising_repos(since) + self.hot_feature_requests(issues_since)
