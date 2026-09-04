# Comparateur intelligent de stations de ski

Projet portfolio combinant data engineering (PySpark, dbt, Snowflake) et
développement fullstack (FastAPI, frontend web) pour recommander des stations
de ski selon l'enneigement, la météo et les préférences utilisateur.

## Documentation

- `docs/SPEC-comparateur-ski.md` — spécification complète (architecture, schéma dbt, API, roadmap)
- `CLAUDE.md` — contexte projet pour Claude Code

## Structure du projet

- `ingestion/` — scripts PySpark de collecte des données (bronze)
- `dbt_project/` — transformations dbt (silver/gold) sur Snowflake
- `api/` — API FastAPI
- `frontend/` — interface web
- `tests/` — tests Python (ingestion + API)
- `scripts/` — scripts utilitaires (déploiement, etc.)

## Démarrage rapide

\`\`\`bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # puis compléter les identifiants
\`\`\`
