"""Modèles de données du pipeline : Signal (brut) -> Insight (extrait par le LLM)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Source(StrEnum):
    GITHUB_REPO = "github_repo"
    GITHUB_ISSUE = "github_issue"
    HACKERNEWS = "hackernews"


class Signal(BaseModel):
    """Un élément brut collecté : repo, issue, commentaire HN..."""

    id: str  # unique : "<source>:<id externe>"
    source: Source
    title: str
    body: str = ""
    url: str
    engagement: int = 0  # étoiles, réactions, points : normalisé plus tard
    created_at: datetime
    extra: dict = Field(default_factory=dict)


class Insight(BaseModel):
    """Ce que le LLM extrait d'un signal."""

    signal_id: str
    is_opportunity: bool
    problem: str = ""
    audience: str = ""
    existing_solutions: str = ""
    idea_name: str = ""
    idea_pitch: str = ""
    category: str = ""
    pain_severity: int = Field(0, ge=0, le=5)
    willingness_to_pay: int = Field(0, ge=0, le=5)
    solo_buildable: int = Field(0, ge=0, le=5)
    founder_fit: int = Field(0, ge=0, le=5)
    score: float = 0.0
