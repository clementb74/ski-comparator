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
- **Source du référentiel stations : OpenStreetMap (Nominatim + Overpass), pas
  data.gouv.fr.** Aucun jeu de données data.gouv.fr propre et couvrant toute
  la France n'a été trouvé (seuls des jeux régionaux existent). Nominatim
  géocode chaque station (nom → lat/lon, département, région) ; Overpass
  récupère l'altitude (tag `ele`) quand disponible. Aucune clé requise, mais
  l'instance publique `overpass-api.de` est partagée et répond parfois par
  des 429/504 sous charge — géré en laissant `altitude_m` à `null` plutôt que
  de faire échouer le batch (`ingestion/sources/stations_referentiel.py`).
- **Une seule altitude (`altitude_m`), pas altitude_min/max.** OSM ne donne
  fiablement que l'altitude d'un point (village/centre station), pas la
  fourchette du domaine skiable. `altitude_min`/`altitude_max` viendront de
  la source bulletins neige (qui publie souvent cette fourchette), pas encore
  implémentée.
- **MongoDB local via Docker pour le dev** (`docker run -d --name
  ski-comparator-mongo -p 27017:27017 mongo:7`), `MONGODB_URI` dans `.env`.
  Bascule vers Atlas/EC2 prévue pour la prod.
- **Ingestion en Python simple, pas PySpark, pour l'instant.** PySpark
  nécessite Java (absent de la machine de dev, install Windows pénible) pour
  un gain nul sur des volumes de quelques dizaines de lignes. Réservé à une
  future source à plus gros volume (ex. relevés météo quotidiens).
  `requirements.txt` garde pyspark en dépendance, inutilisée pour l'instant.
- **Environnement Python isolé (`venv/`) pour `ingestion/`/`api/`/`tests/`**,
  pour ne pas entrer en conflit avec l'installation dbt globale de la machine
  (dbt-snowflake épingle une version de `snowflake-connector-python`
  différente de celle du projet).
- **Pipeline `ingestion/pipeline.py` : double écriture Mongo (bronze) +
  Snowflake RAW (silver-ready) dans le même run**, pas de chantier séparé
  pour le pont Bronze→Snowflake pour l'instant. Le chargement Snowflake est
  un delete+insert par `station_id` (idempotent), pas un merge incrémental.

## Points ouverts

- Fréquence de rafraîchissement du pipeline : à définir
- Formule exacte du score de qualité neige : à définir
- Sources météo et bulletins neige (2/3 et 3/3 du roadmap ingestion) : pas
  encore implémentées

## Note

Ce fichier donne le contexte à Claude Code. Les décisions de design/architecture
sont réfléchies en amont avec Claude (claude.ai) puis reportées ici et dans
`docs/SPEC-comparateur-ski.md` pour rester synchronisées.
