"""Interface en ligne de commande du BRAINSTORMER.

brainstormer collect   # récupère les signaux
brainstormer extract   # analyse par le LLM
brainstormer digest    # écrit le rapport des meilleures idées
brainstormer run       # les trois d'affilée
"""

import logging

import httpx
import typer

from . import digest as digest_mod
from . import notify
from .collectors import GitHubCollector, HackerNewsCollector
from .config import get_settings
from .db import Database
from .extract import Extractor
from .scoring import score

app = typer.Typer(
    help="BRAINSTORMER : des idées d'apps tirées de vrais besoins.", no_args_is_help=True
)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("brainstormer")
logging.getLogger("httpx").setLevel(logging.WARNING)


def _db() -> Database:
    return Database(get_settings().db_path)


@app.command()
def collect(days: int = typer.Option(None, help="Fenêtre en jours (défaut : .env)")) -> None:
    """Collecte les signaux GitHub et Hacker News."""
    s = get_settings()
    days = days or s.brainstormer_lookback_days
    db = _db()
    collectors = {
        "GitHub": GitHubCollector(token=s.github_token),
        "Hacker News": HackerNewsCollector(),
    }
    for name, c in collectors.items():
        try:
            signals = c.collect(days)
        except httpx.HTTPStatusError as e:
            log.error(
                "%s : erreur HTTP %s (%s)",
                name,
                e.response.status_code,
                "limite atteinte ? ajoute un GITHUB_TOKEN" if name == "GitHub" else "",
            )
            continue
        except httpx.HTTPError as e:
            log.error("%s : %s", name, e)
            continue
        new = db.upsert_signals(signals)
        typer.echo(f"{name} : {len(signals)} signaux, dont {new} nouveaux")


@app.command()
def extract(limit: int = typer.Option(50, help="Nombre max de signaux à analyser")) -> None:
    """Analyse les signaux non traités avec Claude."""
    s = get_settings()
    if not s.anthropic_api_key:
        raise typer.BadParameter("ANTHROPIC_API_KEY manquante dans le fichier .env")
    db = _db()
    ex = Extractor(s.anthropic_api_key, s.brainstormer_model, s.brainstormer_founder_profile)
    todo = db.unprocessed(limit)
    found = 0
    with typer.progressbar(todo, label="Analyse") as bar:
        for sig in bar:
            try:
                ins = ex.extract(sig)
            except Exception as e:
                log.error("Échec sur %s : %s", sig.id, e)
                continue
            if ins is None:
                continue
            ins.score = score(ins, sig)
            db.save_insight(ins)
            found += ins.is_opportunity
    typer.echo(f"{len(todo)} signaux analysés, {found} opportunités détectées")


@app.command()
def digest(
    size: int = typer.Option(None, help="Nombre d'idées (défaut : .env)"),
    all_: bool = typer.Option(False, "--all", help="Inclure les idées déjà présentées"),
) -> None:
    """Écrit le digest Markdown des meilleures idées et notifie si ntfy est configuré."""
    s = get_settings()
    db = _db()
    ideas = db.top_ideas(size or s.brainstormer_digest_size, include_reported=all_)
    path = digest_mod.write(digest_mod.render(ideas), s.reports_dir)
    db.mark_reported([i["signal_id"] for i in ideas])
    typer.echo(f"Digest écrit : {path}")
    if ideas:
        notify.push(
            s.ntfy_topic,
            f"BRAINSTORMER : {len(ideas)} idées",
            "\n".join(f"• {i['idea_name']} ({i['score']:.0f})" for i in ideas),
        )


@app.command()
def run() -> None:
    """Pipeline complet : collect -> extract -> digest."""
    collect(days=None)
    extract(limit=50)
    digest(size=None, all_=False)


@app.command()
def vote(signal_id: str, direction: str = typer.Argument(..., help="up ou down")) -> None:
    """Note une idée. Ces votes serviront à entraîner le classement (V3)."""
    if direction not in ("up", "down"):
        raise typer.BadParameter("direction doit valoir 'up' ou 'down'")
    _db().add_feedback(signal_id, 1 if direction == "up" else -1)
    typer.echo("Vote enregistré 👍" if direction == "up" else "Vote enregistré 👎")


@app.command()
def stats() -> None:
    """Affiche l'état de la base."""
    for k, v in _db().stats().items():
        typer.echo(f"{k:>14} : {v}")


if __name__ == "__main__":
    app()
