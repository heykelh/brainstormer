# 🧠 BRAINSTORMER

> Un agent IA qui scrute GitHub et Hacker News pour transformer de **vrais besoins exprimés** en idées d'apps à construire.

La plupart des générateurs d'idées demandent à un LLM « donne-moi une idée de SaaS » et obtiennent les mêmes réponses génériques que tout le monde. Le BRAINSTORMER part dans l'autre sens : il collecte des **preuves** (issues GitHub très votées, commentaires « is there a tool… », repos en forte croissance), puis seulement ensuite demande à Claude de les analyser. Chaque idée du digest renvoie à sa source.

## Fonctionnement

```
 GitHub (repos montants, feature requests)  ┐
                                            ├─► SQLite ─► Claude (extraction structurée) ─► score ─► digest.md ─► ntfy 📱
 Hacker News (« is there a tool », Ask HN)  ┘
```

| Étape | Ce qui se passe |
|---|---|
| `collect` | Récupère les signaux via les API officielles (GitHub Search, HN Algolia). Dédoublonnage par identifiant. |
| `extract` | Claude lit chaque signal et remplit un schéma imposé (tool use) : problème, public, solutions existantes, idée, 4 notes sur 5. |
| `digest` | Classe les opportunités, écrit `reports/AAAA-MM-JJ.md`, ne répète jamais une idée déjà présentée. |
| `vote` | Tu notes les idées 👍/👎 : ces étiquettes entraîneront le classement en V3. |

Score V1 = moyenne pondérée (douleur 30 %, volonté de payer 30 %, faisable en solo 20 %, adéquation avec ton profil 20 %), modulée de ±20 % par l'engagement. Réglable dans `src/brainstormer/scoring.py`.

## Installation (Windows / PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env    # puis remplis ANTHROPIC_API_KEY (et GITHUB_TOKEN recommandé)
```

> Si PowerShell bloque l'activation : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Utilisation

```powershell
brainstormer run          # pipeline complet
brainstormer collect      # ou étape par étape
brainstormer extract --limit 20
brainstormer digest
brainstormer stats
brainstormer vote hn:41234567 up
```

`python -m brainstormer ...` fonctionne aussi.

## Tests

```powershell
pytest
ruff check .
```

Les tests n'appellent ni GitHub, ni HN, ni Claude : tout est simulé.

## Coût

Avec Claude Haiku, une analyse coûte une fraction de centime. Un `run` hebdomadaire sur ~50 signaux reste très bon marché. `--limit` permet de plafonner.

## Données et conformité

- Uniquement des **API officielles** et des données publiques, pour un usage personnel de recherche.
- Les tokens restent dans `.env` (ignoré par git).
- Reddit est volontairement absent de la V1 : son API interdit l'usage commercial sans licence (c'est ce qui a coulé GummySearch). À traiter proprement avant toute commercialisation.

## Feuille de route

Voir [docs/ROADMAP.md](docs/ROADMAP.md).
