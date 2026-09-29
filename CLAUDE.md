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
  fourchette du domaine skiable. L'espoir initial était que la source
  bulletins neige fournirait cette fourchette — **vérifié que non** (le
  JSON-LD skiinfo.fr n'a aucun champ altitude, voir plus bas) : point
  toujours ouvert, à résoudre par une source dédiée si besoin plus tard.
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
  un delete+insert par une clé (`station_id` ou `id_massif_bra` selon la
  source, paramétrable via `key_field`/`key_column`), pas un merge
  incrémental.
- **Source météo : BRA (Bulletin de Risque d'Avalanche) Météo-France, pas
  une API de prévisions générales.** L'API accessible avec les identifiants
  du projet (`portail-api.meteofrance.fr` + `public-api.meteofrance.fr`)
  couvre le risque avalanche et l'enneigement par massif, pas
  température/vent/pluie. Auth : header `Authorization` fourni tel quel par
  le portail dans `.env` (`METEO_FRANCE_AUTHORIZATION`, format `Basic
  xxx...`) — **ce n'est pas** un `client_id`/`client_secret` à reconstruire
  (l'identifiant de connexion au portail ne fonctionne pas comme client_id,
  vérifié à deux reprises). Un appel par massif BRA (pas par station, 7
  massifs pour 20 stations), token réutilisé pour tout le run
  (`ingestion/sources/meteo_france.py`).
- **BRA est saisonnier (novembre à juin)** : hors saison (ex. septembre),
  l'API répond un `<message>` "saison terminée" au lieu du bulletin. Géré
  explicitement (`hors_saison=True`), pas une erreur. **Le schéma XML du
  bulletin en saison n'a pas pu être vérifié sur des données réelles** — le
  parsing (`DATEBULLETIN`, `CARTOUCHERISQUE/RISQUE`, ...) est basé sur une
  source tierce technique, pas la doc officielle Météo-France (PDF
  illisible en l'état). Le XML brut est conservé en bronze pour ré-analyse
  si besoin. **À revalider dès la reprise de saison en novembre 2026.**
- **`sous_massif` du seed pilote (Faucigny, Tarentaise) ne correspond pas
  aux 23 massifs BRA officiels.** Mapping station → massif BRA dans
  `dbt_project/seeds/stations_massif_bra.csv`, confirmé station par station
  avec l'utilisateur — sauf **flaine → Aravis, qui reste un TODO
  incertain** (pas de massif BRA officiel pour "Faucigny", choix par
  proximité géographique non vérifié).
- **Fix d'un bug pré-existant** : `int_stations_meteo_joined.sql` joignait
  sur `stations.massif` (toujours "Alpes du Nord", donc inutilisable comme
  clé). Remplacé par une jointure via `stations_massif_bra` sur le massif
  BRA fin.
- **Source bulletins neige : skiinfo.fr (JSON-LD `schema.org/SkiResort`),
  pas de scraping HTML fragile.** Chaque page
  `skiinfo.fr/alpes-du-nord/{slug}/bulletin-neige` contient un bloc JSON
  structuré (`additionalProperty`) avec hauteur de neige (base + sommet),
  pistes/remontées ouvertes, statut station. Légal (`robots.txt` : `Allow:
  /`), pas de clé. Schéma complet vérifié sur un resort réellement ouvert
  (Valle Nevado, Chili, saison australe en cours) plutôt que sur une
  station française (toutes hors-saison actuellement) —
  `ingestion/sources/bulletins_neige.py`, parsing défensif par nom de
  propriété, tolérant aux champs absents hors-saison.
- **Mapping station → slug skiinfo.fr** dans
  `dbt_project/seeds/stations_skiinfo_slug.csv` : 4 des 20 slugs diffèrent
  du `station_id` (vérifiés un par un par requêtes HTTP réelles) —
  `chamonix-mont-blanc`→`chamonix`, `morzine-avoriaz`→`morzine`,
  `les-arcs`→`les-arcs-bourg-st-maurice`, `les-sept-laux`→`les-7-laux`.
- **Les 3 sources du roadmap ingestion sont maintenant implémentées**
  (référentiel, météo/avalanche, bulletins neige) — pipeline bout en bout
  validé : `ingestion/pipeline.py` → MongoDB (bronze) → Snowflake RAW →
  `stg_*`/`int_*`/marts dbt.

## Points ouverts

- Fréquence de rafraîchissement du pipeline : à définir
- Formule exacte du score de qualité neige : à définir
- Revalider le parsing XML du BRA avec de vraies données dès novembre 2026
- Vérifier le massif BRA de Flaine (actuellement Aravis, TODO non confirmé)
- `altitude_min`/`altitude_max` (fourchette du domaine skiable) : aucune des
  3 sources ne les fournit, à résoudre par une source dédiée si besoin

## Note

Ce fichier donne le contexte à Claude Code. Les décisions de design/architecture
sont réfléchies en amont avec Claude (claude.ai) puis reportées ici et dans
`docs/SPEC-comparateur-ski.md` pour rester synchronisées.
