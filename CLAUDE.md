# Contexte projet — Comparateur intelligent de stations de ski

## Résumé

Projet portfolio personnel. Application qui agrège enneigement, météo et données
structurelles (altitude, exposition, taille du domaine) de stations de ski
françaises, calcule un score de qualité personnalisé, et propose une
recommandation via une interface cartographique.

Objectif : démontrer la maîtrise complète de la chaîne data engineering +
développement fullstack (ingestion → transformation → API → interface web).

La spécification complète (architecture, schéma dbt détaillé, endpoints API,
roadmap) est dans `docs/SPEC-comparateur-ski.md` — s'y référer avant toute décision structurante.

## Stack technique

- **Ingestion** : Python, PySpark
- **Stockage brut** : MongoDB
- **Data warehouse** : Snowflake
- **Transformation** : dbt
- **API** : FastAPI
- **Frontend** : React ou HTML/JS + carte interactive (Leaflet/Mapbox)
- **Infra** : AWS EC2 (Ubuntu), accès SSH depuis Windows 11 / Git Bash
- **Versioning** : Git

## Modèle de données (médaillon)

Bronze (MongoDB, brut) → Silver (dbt staging, Snowflake) → Gold (dbt marts,
Snowflake) → API → Frontend. Détail des modèles dbt (staging/intermediate/marts)
dans `docs/SPEC-comparateur-ski.md` section 5.

## Conventions de code

- Python : suivre PEP8, typage explicite (type hints) sur les fonctions publiques
- dbt : un modèle = une responsabilité claire (staging = nettoyage, marts = logique métier)
- API : endpoints REST versionnés, modèles Pydantic pour toute entrée/sortie
- Commits : messages clairs en français ou anglais, un commit = un changement cohérent

## Où en est le projet

Phase 1 (MVP data) en cours de démarrage — voir `docs/SPEC-comparateur-ski.md` section 7 pour la
roadmap complète. Mettre à jour cette section au fil de l'avancement.

## Décisions prises

- **Périmètre géographique pilote** : Alpes du Nord, 20 stations listées dans
  `dbt_project/seeds/perimetre_stations.csv` (extensible sans toucher au code —
  ajouter une ligne au CSV suffit). `stg_stations_referentiel` filtre sur ce seed.

## Points ouverts

- Fréquence de rafraîchissement du pipeline : à définir
- Formule exacte du score de qualité neige : à définir

## Note

Ce fichier donne le contexte à Claude Code. Les décisions de design/architecture
sont réfléchies en amont avec Claude (claude.ai) puis reportées ici et dans
`docs/SPEC-comparateur-ski.md` pour rester synchronisées.
