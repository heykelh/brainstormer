"""Génère le digest Markdown des meilleures idées."""

from datetime import date
from pathlib import Path
from sqlite3 import Row

SOURCE_LABEL = {
    "github_repo": "Repo GitHub",
    "github_issue": "Issue GitHub",
    "hackernews": "Hacker News",
}


def render(ideas: list[Row], day: date | None = None) -> str:
    day = day or date.today()
    lines = [f"# BRAINSTORMER — digest du {day:%d/%m/%Y}", ""]
    if not ideas:
        lines.append("Aucune nouvelle opportunité cette fois-ci.")
        return "\n".join(lines) + "\n"
    for n, i in enumerate(ideas, 1):
        lines += [
            f"## {n}. {i['idea_name']} — score {i['score']:.0f}/120",
            "",
            f"**L'idée :** {i['idea_pitch']}",
            "",
            f"- **Problème :** {i['problem']}",
            f"- **Pour qui :** {i['audience'] or '—'}",
            f"- **Solutions existantes :** {i['existing_solutions'] or '—'}",
            f"- **Catégorie :** {i['category']}",
            f"- **Notes :** douleur {i['pain_severity']}/5 · paiement {i['willingness_to_pay']}/5"
            f" · faisable solo {i['solo_buildable']}/5 · adéquation {i['founder_fit']}/5",
            f"- **Preuve :** [{SOURCE_LABEL.get(i['source'], i['source'])} — {i['title']}]"
            f"({i['url']}) ({i['engagement']} d'engagement)",
            f"- **Voter :** `brainstormer vote {i['signal_id']} up` ou `down`",
            "",
        ]
    return "\n".join(lines)


def write(content: str, reports_dir: Path, day: date | None = None) -> Path:
    day = day or date.today()
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{day:%Y-%m-%d}.md"
    path.write_text(content, encoding="utf-8")
    return path
