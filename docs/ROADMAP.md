# Feuille de route

## V1 — Le pipeline de base ✅
- [x] Collecte GitHub : repos récents à forte croissance + feature requests très votées
- [x] Collecte Hacker News : commentaires « is there a tool / I wish there was / I'd pay for » + Ask HN
- [x] Extraction structurée par Claude (tool use, schéma imposé)
- [x] Score heuristique transparent
- [x] Digest Markdown hebdomadaire avec liens de preuve, sans redites
- [x] Votes 👍/👎 stockés (futures étiquettes ML)
- [x] Notification ntfy
- [ ] Planification : tâche cron sur le Raspberry Pi (`0 8 * * 1 brainstormer run`)

## V2 — Plus de sources, moins de bruit
- [ ] Clustering par embeddings (BERTopic / HDBSCAN) : regrouper les besoins similaires, compter les occurrences
- [ ] Sources francophones et européennes : avis de logiciels, Malt, forums métiers
- [ ] Veille réglementaire : EUR-Lex / Légifrance → besoins d'outillage créés par chaque obligation
- [ ] Offres d'emploi : tâches manuelles répétitives recrutées en masse
- [ ] Module de validation : concurrents existants + volume de recherche par idée
- [ ] Migration SQLite → Supabase + petite interface (Next.js) pour lire et voter

## V3 — Machine learning
- [ ] Classifieur « opportunité / bruit » distillé à partir des étiquettes du LLM (coût ÷ 10)
- [ ] Détection de tendances : accélération d'un cluster dans le temps
- [ ] Classement appris sur les votes (learning to rank) une fois ~300 votes accumulés
- [ ] Évaluation : précision@5 du digest mesurée sur les votes
