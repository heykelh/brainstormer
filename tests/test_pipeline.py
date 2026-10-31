from types import SimpleNamespace

from brainstormer import digest
from brainstormer.extract import Extractor, build_prompt
from brainstormer.models import Insight
from brainstormer.scoring import score

LLM_OUTPUT = {
    "is_opportunity": True,
    "problem": "Cartographier les modèles ML vers les catégories de risque de l'AI Act",
    "audience": "Équipes data des PME européennes",
    "existing_solutions": "Tableurs",
    "idea_name": "RiskMapper",
    "idea_pitch": "Un registre des modèles qui classe chaque système selon l'AI Act.",
    "category": "conformite",
    "pain_severity": 4,
    "willingness_to_pay": 4,
    "solo_buildable": 4,
    "founder_fit": 5,
}


class FakeAnthropic:
    """Remplace le client Anthropic : aucun appel réseau, aucun coût."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=self.payload)])


def test_extract_forces_tool_and_parses(signal):
    fake = FakeAnthropic(LLM_OUTPUT)
    ins = Extractor("k", "claude-haiku-5-5", "Profil test", client=fake).extract(signal)
    assert ins.idea_name == "RiskMapper" and ins.signal_id == "hn:123"
    assert fake.calls[0]["tool_choice"] == {"type": "tool", "name": "record_insight"}


def test_extract_rejects_out_of_schema(signal):
    bad = {**LLM_OUTPUT, "pain_severity": 9}
    assert Extractor("k", "m", "p", client=FakeAnthropic(bad)).extract(signal) is None


def test_prompt_contains_profile(signal):
    p = build_prompt(signal, "Data engineer")
    assert "Data engineer" in p and "AI Act" in p


def test_score_bounds(signal):
    good = Insight(signal_id=signal.id, **LLM_OUTPUT)
    assert 60 < score(good, signal) <= 120
    assert score(good.model_copy(update={"is_opportunity": False}), signal) == 0


def test_full_pipeline_in_db(db, signal, tmp_path):
    assert db.upsert_signals([signal]) == 1
    assert db.upsert_signals([signal]) == 0  # dédoublonnage

    [todo] = db.unprocessed()
    ins = Extractor("k", "m", "p", client=FakeAnthropic(LLM_OUTPUT)).extract(todo)
    ins.score = score(ins, todo)
    db.save_insight(ins)
    assert db.unprocessed() == []

    ideas = db.top_ideas(5)
    path = digest.write(digest.render(ideas), tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "RiskMapper" in text and signal.url in text

    db.mark_reported([i["signal_id"] for i in ideas])
    assert db.top_ideas(5) == []  # pas de redite au digest suivant
    assert len(db.top_ideas(5, include_reported=True)) == 1

    db.add_feedback(signal.id, 1)
    assert db.stats()["votes"] == 1


def test_empty_digest():
    assert "Aucune nouvelle opportunité" in digest.render([])
