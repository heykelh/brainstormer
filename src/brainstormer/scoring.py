"""Score V1 : heuristique transparente et réglable.

Sera remplacé en V3 par un modèle de classement appris sur tes votes (table feedback).
"""

import math

from .models import Insight, Signal, Source

# Poids des critères notés par le LLM (sur 5). La somme vaut 1.
WEIGHTS = {
    "pain_severity": 0.30,
    "willingness_to_pay": 0.30,
    "solo_buildable": 0.20,
    "founder_fit": 0.20,
}

# Engagement "typique" par source, pour normaliser étoiles / réactions / points
ENGAGEMENT_REF = {
    Source.GITHUB_REPO: 500,
    Source.GITHUB_ISSUE: 50,
    Source.HACKERNEWS: 100,
}


def engagement_factor(signal: Signal) -> float:
    """Entre 0.8 et 1.2 : l'engagement module le score sans l'écraser."""
    ref = ENGAGEMENT_REF.get(signal.source, 100)
    ratio = math.log1p(max(signal.engagement, 0)) / math.log1p(ref)
    return 0.8 + 0.4 * min(ratio, 1.0)


def score(insight: Insight, signal: Signal) -> float:
    if not insight.is_opportunity:
        return 0.0
    base = sum(getattr(insight, k) / 5 * w for k, w in WEIGHTS.items())
    return round(100 * base * engagement_factor(signal), 1)
