"""Extraction LLM : un signal brut -> un Insight structuré.

On force Claude à répondre via un outil (tool use) : la sortie respecte un
schéma JSON, pas besoin de parser du texte libre.
"""

import logging

from anthropic import Anthropic

from .models import Insight, Signal

log = logging.getLogger(__name__)

SYSTEM = """Tu es l'analyste du BRAINSTORMER. Tu lis un signal public (repo GitHub, \
issue GitHub, commentaire Hacker News) et tu détermines s'il révèle une opportunité \
de produit logiciel qu'un développeur solo pourrait construire et vendre.

Règles :
- Sois exigeant : la plupart des signaux ne sont PAS des opportunités. Un bug, une \
question technique pointue, une opinion ou un simple projet perso n'en sont pas.
- Pour un repo GitHub en forte croissance, l'opportunité peut être : une version \
hébergée/clé en main, un outil complémentaire, ou le même concept pour un autre public.
- Pour une issue ou un commentaire, l'opportunité est le besoin exprimé, s'il dépasse \
ce seul projet ou cette seule personne.
- Évalue l'adéquation avec le profil du fondateur fourni.
- Réponds en français, de façon concise et concrète. N'invente aucun fait."""

TOOL = {
    "name": "record_insight",
    "description": "Enregistre l'analyse du signal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_opportunity": {"type": "boolean"},
            "problem": {"type": "string", "description": "Le problème, en une phrase."},
            "audience": {"type": "string", "description": "Qui a ce problème."},
            "existing_solutions": {
                "type": "string",
                "description": "Solutions mentionnées ou connues, sinon 'inconnues'.",
            },
            "idea_name": {"type": "string", "description": "Nom de code court de l'idée."},
            "idea_pitch": {"type": "string", "description": "Le produit en 2 phrases max."},
            "category": {
                "type": "string",
                "enum": [
                    "dev-tools",
                    "b2b-saas",
                    "data-ia",
                    "conformite",
                    "productivite",
                    "grand-public",
                    "autre",
                ],
            },
            "pain_severity": {"type": "integer", "minimum": 0, "maximum": 5},
            "willingness_to_pay": {"type": "integer", "minimum": 0, "maximum": 5},
            "solo_buildable": {"type": "integer", "minimum": 0, "maximum": 5},
            "founder_fit": {"type": "integer", "minimum": 0, "maximum": 5},
        },
        "required": [
            "is_opportunity",
            "problem",
            "idea_name",
            "idea_pitch",
            "category",
            "pain_severity",
            "willingness_to_pay",
            "solo_buildable",
            "founder_fit",
        ],
    },
}


def build_prompt(signal: Signal, founder_profile: str) -> str:
    extra = ", ".join(f"{k}={v}" for k, v in signal.extra.items() if v not in (None, [], ""))
    return (
        f"PROFIL DU FONDATEUR : {founder_profile}\n\n"
        f"SOURCE : {signal.source.value}\n"
        f"TITRE : {signal.title}\n"
        f"ENGAGEMENT : {signal.engagement}\n"
        f"MÉTADONNÉES : {extra or 'aucune'}\n"
        f"CONTENU :\n{signal.body or '(vide)'}"
    )


class Extractor:
    def __init__(
        self, api_key: str, model: str, founder_profile: str, client: Anthropic | None = None
    ):
        self.client = client or Anthropic(api_key=api_key)
        self.model = model
        self.founder_profile = founder_profile

    def extract(self, signal: Signal) -> Insight | None:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            system=SYSTEM,
            tools=[TOOL],
            tool_choice={"type": "tool", "name": TOOL["name"]},
            messages=[{"role": "user", "content": build_prompt(signal, self.founder_profile)}],
        )
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                try:
                    return Insight(signal_id=signal.id, **block.input)
                except Exception as e:  # sortie hors schéma : on journalise et on passe
                    log.warning("Insight invalide pour %s : %s", signal.id, e)
                    return None
        log.warning("Pas de tool_use pour %s", signal.id)
        return None
