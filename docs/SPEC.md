# Comparateur intelligent de stations de ski — Spécification technique

## 1. Objectif du projet

Application qui agrège en quasi temps réel l'enneigement, la météo et des données structurelles (altitude, exposition, taille du domaine) de stations de ski françaises, calcule un score de qualité personnalisé selon les critères de l'utilisateur, et propose une recommandation via une interface cartographique.

Projet portfolio destiné à démontrer une maîtrise complète de la chaîne data engineering + développement fullstack :
ingestion → transformation (dbt/Snowflake) → API (FastAPI) → interface web.

## 2. Stack technique

| Couche | Technologie |
|---|---|
| Ingestion | Python, PySpark |
| Stockage brut | MongoDB (données semi-structurées, historique brut) |
| Data warehouse | Snowflake |
| Transformation | dbt |
| API | FastAPI |
| Frontend | React ou HTML/JS + carte interactive (Leaflet/Mapbox) |
| Infra | AWS EC2 (Ubuntu), accès SSH |
| Versioning | Git |

## 3. Sources de données

| Source | Type de données | Méthode d'accès |
|---|---|---|
| Météo France | Prévisions, relevés par zone montagne | API publique (data.gouv.fr) |
| data.gouv.fr | Référentiel domaines skiables, remontées mécaniques | Téléchargement / API |
| Bulletins neige stations | Hauteur de neige, état des pistes | Scraping léger (respect robots.txt) |
| IGN / OpenStreetMap (Overpass API) | Altitude, exposition, coordonnées pistes/remontées | API |

## 4. Architecture du pipeline (modèle médaillon)

```
Sources externes
      │
      ▼
[Bronze] Ingestion brute → MongoDB
   - Données telles que reçues, horodatées, non transformées
      │
      ▼
[Silver] Nettoyage / staging → Snowflake (via dbt staging models)
   - Typage, dédoublonnage, normalisation des noms de stations
      │
      ▼
[Gold] Modèles métier → Snowflake (via dbt marts)
   - Tables prêtes à consommer par l'API
      │
      ▼
API FastAPI → Frontend web
```

## 5. Schéma dbt proposé

### 5.1 Sources (`sources.yml`)
- `raw_meteo_releves` — relevés météo bruts par zone
- `raw_stations_referentiel` — référentiel stations (data.gouv.fr)
- `raw_bulletins_neige` — bulletins neige scrapés

### 5.2 Staging (`models/staging/`)
- `stg_meteo_releves.sql` — typage des dates, normalisation des unités (cm, °C)
- `stg_stations_referentiel.sql` — nettoyage noms de stations, altitude min/max, massif
- `stg_bulletins_neige.sql` — parsing des hauteurs de neige, gestion des valeurs manquantes

### 5.3 Intermediate (`models/intermediate/`)
- `int_stations_meteo_joined.sql` — jointure stations + relevés météo par zone géographique
- `int_enneigement_historique.sql` — historique d'enneigement par station et par saison

### 5.4 Marts (`models/marts/`)
- `dim_stations.sql` — dimension station (nom, massif, altitude, coordonnées, taille domaine)
- `fct_enneigement_quotidien.sql` — table de faits : enneigement/météo quotidiens par station
- `mart_score_qualite_neige.sql` — score calculé (enneigement, fraîcheur neige, météo à venir)

### 5.5 Tests dbt à prévoir
- `not_null` et `unique` sur les clés de station (`station_id`)
- `accepted_range` sur l'altitude, la hauteur de neige (valeurs cohérentes)
- Test de fraîcheur des données (`dbt source freshness`) sur les relevés météo

## 6. Endpoints API (FastAPI) — première itération

| Méthode | Route | Description |
|---|---|---|
| GET | `/stations` | Liste des stations avec filtres (massif, altitude, type de ski) |
| GET | `/stations/{id}` | Détail d'une station (score, historique enneigement) |
| GET | `/stations/comparer?ids=` | Comparaison de plusieurs stations |
| GET | `/recommandations` | Recommandation selon critères utilisateur (niveau, budget, dates) |

## 7. Roadmap

1. **Phase 1 — MVP data** : ingestion + dbt sur 15-20 stations pilotes (Alpes du Nord), premier score simple
2. **Phase 2 — API** : endpoints, logique de scoring, tests automatisés
3. **Phase 3 — Frontend** : carte interactive, fiches stations, comparateur

## 8. Points ouverts à trancher avec Claude Code

- Fréquence de rafraîchissement du pipeline (cron, Airflow léger, ou script manuel au départ ?)
- Granularité du score de qualité neige (formule à définir : pondération enneigement/météo/fraîcheur)
- Choix définitif du périmètre géographique pilote (un massif ou plusieurs ?)
