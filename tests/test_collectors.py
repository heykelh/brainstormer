import httpx
import respx

from brainstormer.collectors import GitHubCollector, HackerNewsCollector
from brainstormer.models import Source

REPO = {
    "id": 1,
    "full_name": "acme/llm-guard",
    "description": "Guardrails for LLM apps",
    "html_url": "https://github.com/acme/llm-guard",
    "stargazers_count": 1200,
    "created_at": "2026-10-20T10:00:00Z",
    "topics": ["llm"],
    "language": "Python",
    "homepage": None,
}
ISSUE = {
    "id": 9,
    "title": "Feature request: export to Parquet",
    "body": "Many of us need this.",
    "html_url": "https://github.com/acme/tool/issues/9",
    "repository_url": "https://api.github.com/repos/acme/tool",
    "reactions": {"total_count": 42},
    "comments": 7,
    "created_at": "2026-09-01T00:00:00Z",
}


@respx.mock
def test_github_collect_dedupes_issues():
    respx.get("https://api.github.com/search/repositories").mock(
        return_value=httpx.Response(200, json={"items": [REPO]})
    )
    # La même issue remonte via les 3 requêtes : elle ne doit apparaître qu'une fois
    respx.get("https://api.github.com/search/issues").mock(
        return_value=httpx.Response(200, json={"items": [ISSUE]})
    )

    signals = GitHubCollector().collect(lookback_days=14)

    repos = [s for s in signals if s.source == Source.GITHUB_REPO]
    issues = [s for s in signals if s.source == Source.GITHUB_ISSUE]
    assert len(repos) == 1 and repos[0].engagement == 1200
    assert repos[0].extra["stars_per_day"] > 0
    assert len(issues) == 1
    assert issues[0].title == "[acme/tool] Feature request: export to Parquet"
    assert issues[0].engagement == 42


@respx.mock
def test_github_sends_token():
    route = respx.get("https://api.github.com/search/repositories").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    respx.get("https://api.github.com/search/issues").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    GitHubCollector(token="abc").collect(7)
    assert route.calls[0].request.headers["Authorization"] == "Bearer abc"


@respx.mock
def test_hackernews_cleans_html_and_skips_short():
    hits = [
        {
            "objectID": "1",
            "comment_text": "<p>Is there a tool that does X &amp; Y for small "
            "accounting firms? I&#x27;d happily pay monthly for it.</p>",
            "story_title": "Show HN: Foo",
            "points": None,
            "created_at_i": 1_790_000_000,
        },
        {"objectID": "2", "comment_text": "Is there a tool? no", "created_at_i": 1_790_000_000},
    ]
    respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
        return_value=httpx.Response(200, json={"hits": hits})
    )

    signals = HackerNewsCollector().collect(14)

    assert {s.id for s in signals} == {"hn:1"}
    assert "X & Y" in signals[0].body and "<p>" not in signals[0].body
    assert signals[0].url.endswith("id=1")
