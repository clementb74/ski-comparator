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

Les 3 phases du roadmap sont implémentées : Phase 1 (MVP data — ingestion 3
sources → dbt → marts → score), Phase 2 (API FastAPI, 4 endpoints), Phase 3
(frontend carte/fiches/comparateur). Reste surtout des points de
calibration/finition (voir Points ouverts) et le déploiement, pas encore
abordé. Voir `docs/SPEC-comparateur-ski.md` section 7 pour la roadmap
complète. Mettre à jour cette section au fil de
l'avancement.

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
- **Fix d'un bug pré-existant** : `fct_enneigement_quotidien` ne contenait
  que la météo (`int_stations_meteo_joined`), jamais les bulletins neige —
  malgré son nom. Joint maintenant aussi `int_enneigement_historique` sur
  `station_id`.
- **Formule du score de qualité neige** (`mart_score_qualite_neige.sql`) :
  enneigement 50% (`base_snow_depth`, plein score à 100cm) + fraîcheur de la
  dernière chute 25% (plein score le jour même, dégressif à 0 sur 10 jours)
  + ouverture du domaine 25% (`open_trails`, plein score à 40 pistes
  ouvertes). Seuils choisis arbitrairement (pas de saison active pour les
  calibrer sur données réelles) — **à recalibrer en novembre 2026**. Le
  risque avalanche BRA (`niveau_risque_avalanche`) est exposé à part, pas
  intégré au score (ce n'est pas un critère de qualité, c'est un risque).
- **Score `NULL` hors-saison** (pas de `base_snow_depth`) plutôt qu'une
  valeur par défaut — décision explicite pour ne pas confondre "mauvaises
  conditions" et "pas de donnée". Le test dbt sur `score_qualite_neige` est
  `dbt_utils.accepted_range(0, 100)`, pas `not_null` (les `NULL` passent ce
  test sans échouer).
- **`int_enneigement_historique` reste un passthrough** (`select * from
  stg_bulletins_neige`), malgré son nom — une vraie agrégation
  saison/tendances nécessiterait plusieurs runs du pipeline dans le temps
  (le chargement Snowflake actuel est un delete+insert, pas un append) ; on
  n'a qu'un seul snapshot pour l'instant, donc rien à agréger. À revoir
  quand le pipeline tournera en continu.
- **Phase 2 démarrée : API FastAPI.** Endpoints sous préfixe `/api/v1`
  (convention "versionnés" déjà écrite plus haut) : `GET /stations`
  (filtres `massif`/`altitude_min`/`altitude_max`), `GET /stations/{id}`
  (404 explicite si absent), `GET /stations/comparer?ids=...`,
  `GET /recommandations` (tri par `score_qualite_neige`). Connexion
  Snowflake par requête HTTP (`api/core/snowflake_client.py`, même pattern
  que le sink d'ingestion) — pas de pool, cohérent avec l'échelle
  portfolio.
- **`/recommandations` simplifié : tri par score + filtre massif
  uniquement.** Les critères niveau/budget de la spec ne sont pas
  implémentés (aucune source n'ingère difficulté de pistes ou prix) —
  retirés de `StationFiltres` aussi plutôt que d'accepter des paramètres
  sans effet.
- **Fix d'un bug pré-existant** : `Station` (Pydantic) référençait
  `altitude_min`/`altitude_max` qui n'ont jamais existé dans les données
  (`dim_stations` n'a qu'`altitude_m`, point unique OSM) — corrigé.
  `/stations/comparer` était déclarée après `/stations/{station_id}` dans
  le routeur, donc FastAPI aurait matché "comparer" comme un `station_id` —
  ordre corrigé (test de non-régression dans `tests/test_api.py`).
- **Fix d'un bug pré-existant** : `APISettings`/`IngestionSettings`
  n'avaient pas `extra="ignore"` — dès que `.env` contient une variable que
  l'une des deux classes ne déclare pas (ex. `MONGODB_URI` pour
  `APISettings`), pydantic-settings lève une erreur de validation au
  chargement. Corrigé sur les deux, syntaxe modernisée
  (`model_config = SettingsConfigDict(...)` au lieu de `class Config`).
- **Phase 3 (frontend) implémentée** : `frontend/` en HTML/JS vanilla + ES
  modules natifs (pas de bundler, cohérent avec le squelette existant),
  Leaflet via CDN (`unpkg.com/leaflet@1.9.4`), fond de carte OpenStreetMap
  standard. Carte interactive (marqueurs colorés par `score_qualite_neige`,
  gris si `null`), fiches stations = popups Leaflet (pas de page dédiée),
  comparateur (état en mémoire, panneau latéral, table via
  `GET /stations/comparer`). Vérifié dans un vrai navigateur (Playwright,
  installé temporairement pour la vérification) : carte, popups, ajout et
  retrait du comparateur fonctionnent sans erreur console.
- **Ports de dev fixés à 5500 (frontend) et 8811 (API), pas les valeurs par
  défaut (3000 et 8000).** Les deux sont déjà occupés en permanence sur
  cette machine par d'autres projets de l'utilisateur (confirmé via
  `netstat` : un autre service écoute sur `0.0.0.0:8000`/`[::1]:8000`, un
  autre sur `:3000` qui redirige vers `/login`). Symptôme si on l'oublie :
  ça a l'air de marcher en `curl` (résout en IPv4, atteint le bon
  processus) mais échoue silencieusement dans un vrai navigateur (résout
  `localhost` différemment, atteint l'autre service, 404). `package.json`
  (`start`) et `frontend/src/config.js` (`API_BASE_URL`) sont la source de
  vérité pour ces ports ; CORS dans `api/main.py` doit rester aligné avec
  le port frontend.

## Points ouverts

- Fréquence de rafraîchissement du pipeline : à définir
- Recalibrer les seuils du score de qualité neige avec de vraies données en
  novembre 2026 (actuellement des valeurs arbitraires raisonnables)
- Revalider le parsing XML du BRA avec de vraies données dès novembre 2026
- Vérifier le massif BRA de Flaine (actuellement Aravis, TODO non confirmé)
- `altitude_min`/`altitude_max` (fourchette du domaine skiable) : aucune des
  3 sources ne les fournit, à résoudre par une source dédiée si besoin
- Passer `int_enneigement_historique` d'un passthrough à une vraie
  agrégation historique une fois plusieurs runs du pipeline accumulés

## Note

Ce fichier donne le contexte à Claude Code. Les décisions de design/architecture
sont réfléchies en amont avec Claude (claude.ai) puis reportées ici et dans
`docs/SPEC-comparateur-ski.md` pour rester synchronisées.
