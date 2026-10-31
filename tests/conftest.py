from datetime import UTC, datetime

import pytest

from brainstormer.db import Database
from brainstormer.models import Signal, Source


@pytest.fixture
def db():
    return Database(":memory:")


@pytest.fixture
def signal():
    return Signal(
        id="hn:123",
        source=Source.HACKERNEWS,
        title="Ask HN: How do you track AI Act obligations?",
        body="Is there a tool that maps our ML models to AI Act risk categories? "
        "We do it in spreadsheets and I would pay for something better.",
        url="https://news.ycombinator.com/item?id=123",
        engagement=80,
        created_at=datetime(2026, 10, 20, tzinfo=UTC),
    )
