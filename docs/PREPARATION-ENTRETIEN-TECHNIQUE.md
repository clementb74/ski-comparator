# Préparation entretien — Comparateur de stations de ski

Notes pour présenter le projet techniquement. Organisé en : pitch rapide,
architecture, parcours des données, décisions et compromis assumés,
problèmes réels résolus (le plus utile en entretien), limites honnêtes,
questions probables.

## Pitch en 30 secondes

« J'ai construit un pipeline data engineering complet, de bout en bout :
ingestion automatisée de 3 sources externes (référentiel géographique,
météo/avalanche, bulletins neige), stockage brut dans MongoDB, chargement
et transformation dans Snowflake via dbt (staging → intermediate → marts),
calcul d'un score composite, exposé par une API FastAPI et consommé par un
frontend avec carte interactive. L'objectif était de couvrir toute la
chaîne, pas juste une brique, et de le faire avec de vraies sources
externes imparfaites plutôt que des données de démo. »

## Architecture

```
Sources externes (OSM, Météo-France BRA, skiinfo.fr)
        │  Python (requests), auth OAuth2 / clé, parsing XML/JSON
        ▼
  MongoDB (bronze — données brutes horodatées, upsert par clé)
        │
        ▼
  Snowflake RAW (silver-ready — même run d'ingestion, delete+insert)
        │  dbt
        ▼
  staging (nettoyage) → intermediate (jointures) → marts (métier)
        │
        ▼
  FastAPI (/api/v1/stations, /comparer, /recommandations)
        │  fetch, CORS
        ▼
  Frontend (Leaflet, vanilla JS/ES modules)
```

Stack et **pourquoi** ce choix (pas juste le choix) :

| Couche | Techno | Pourquoi |
|---|---|---|
| Ingestion | Python (pas PySpark) | PySpark nécessite Java, absent de la machine de dev ; pour des volumes de quelques dizaines de lignes par run, l'infra JVM n'apporte rien. Décision assumée et documentée, pas un oubli — PySpark reste en dépendance pour une future source à plus gros volume. |
| Stockage brut | MongoDB | Couche bronze : données telles que reçues (payloads JSON/XML complets conservés), schéma flexible adapté à 3 sources hétérogènes. |
| Entrepôt | Snowflake | Warehouse cloud, bien supporté par dbt, connecteur Python mature. |
| Transformation | dbt | Modélisation en couches (staging/intermediate/marts), tests déclaratifs (`not_null`, `unique`, `accepted_range`), SQL versionné. |
| API | FastAPI | Typage Pydantic, génération automatique de la doc OpenAPI, léger. |
| Frontend | Vanilla JS + Leaflet (CDN) | Pas de bundler : le scope ne le justifiait pas, Leaflet est suffisant pour une carte avec marqueurs/popups. Choix assumé plutôt que React par défaut. |

## Parcours des données, bout en bout

1. `ingestion/pipeline.py` orchestre 3 sources, chacune dans son module
   (`ingestion/sources/`) : géocodage, auth API, parsing.
2. Chaque source écrit en bronze (Mongo, upsert par clé) **et** charge
   directement en Snowflake RAW (delete+insert) dans le même run — pas de
   pont asynchrone séparé, décision pragmatique pour l'échelle du projet.
3. dbt transforme : `stg_*` (typage/passthrough), `int_*` (jointures),
   `dim_stations`/`fct_enneigement_quotidien`/`mart_score_qualite_neige`
   (logique métier + score).
4. L'API lit les marts via une connexion Snowflake ouverte par requête
   HTTP (pas de pool — choix pragmatique, documenté comme limite connue).
5. Le frontend appelle l'API et affiche une carte Leaflet avec marqueurs
   colorés par score, popups-fiches, et un comparateur multi-stations.

## Décisions et compromis assumés (bons sujets d'entretien)

- **data.gouv.fr abandonné pour le référentiel stations** après recherche
  effective : aucun jeu de données national propre trouvé (seulement des
  jeux régionaux, ex. Haute-Savoie seule — n'aurait pas couvert Tignes ou
  Chamrousse). Basculé sur OpenStreetMap (Nominatim + Overpass), vérifié en
  direct avant d'implémenter.
- **Granularité différente entre sources** : météo au niveau *massif* (23
  zones officielles Météo-France), bulletins neige au niveau *station*.
  Nécessite un mapping explicite station→massif
  (`stations_massif_bra.csv`), maintenu comme un seed dbt plutôt que codé
  en dur — un ajout/changement de station n'impose pas de modifier le code.
- **Score à `NULL` plutôt qu'une valeur par défaut** hors-saison : décision
  délibérée pour ne pas confondre "mauvaises conditions" et "pas de
  donnée". Impacte jusqu'aux tests dbt (`accepted_range` plutôt que
  `not_null`, qui laisse passer les `NULL`).
- **Risque avalanche exclu du score** : séparé volontairement — un risque
  n'est pas un critère de qualité, les mélanger aurait biaisé la note.
- **Idempotence par delete+insert, pas par merge** : plus simple à
  raisonner pour un petit volume (une vingtaine de lignes par table), payé
  par l'absence d'historique entre deux runs — assumé et documenté comme
  limite (voir plus bas).

## Problèmes réels rencontrés et résolus

C'est la partie la plus utile pour "raconte-moi un problème technique que
tu as résolu" — ce sont de vrais blocages, pas des exercices.

**1. Authentification API Météo-France mal comprise au départ.**
Le portail `portail-api.meteofrance.fr` expose un bulletin avalanche (BRA)
par massif. Première tentative d'authentification avec l'identifiant de
connexion du portail comme `client_id` OAuth2 → échec (`invalid_client`),
reproduit deux fois pour être sûr que ce n'était pas un hasard. En creusant
la doc réelle du portail, j'ai découvert que l'authentification attendue
est un header `Authorization: Basic ...` fourni tout fait par le portail
(généré par application, pas reconstruit depuis login/mot de passe). Leçon :
tester en direct (`curl`) avant de coder contre une hypothèse non vérifiée.

**2. Rate limiting d'une API publique partagée (Overpass/OpenStreetMap).**
L'instance publique `overpass-api.de` renvoie des 429/504 sous charge,
surtout après des tests répétés depuis la même IP. Plutôt que de laisser
échouer tout le batch de 20 stations pour une indisponibilité partielle,
le code traite cette erreur comme "donnée indisponible" (`altitude_m =
null`) et continue — avec un test unitaire dédié à ce cas.

**3. Deux ports de développement par défaut déjà occupés sur la machine.**
Pendant la mise en place du frontend, le port 3000 (`serve` par défaut) et
le port 8000 (`uvicorn` par défaut) étaient déjà pris par d'autres projets
sur la machine. Symptôme trompeur : `curl` fonctionnait (résolution IPv4,
atteint le bon processus), mais un vrai navigateur échouait silencieusement
(résout `localhost` différemment selon la pile IPv4/IPv6, atteint l'autre
service, 404). Diagnostiqué avec `netstat -ano` pour voir qu'il y avait
bien deux processus différents sur le même port. Fixé sur des ports moins
courants (5500/8811) et documenté pour ne pas retomber dedans.

**4. Bug de jointure silencieux.** Un modèle dbt joignait météo et stations
sur une colonne qui valait toujours la même chaîne constante
("Alpes du Nord") pour les 20 stations du périmètre pilote — la jointure
« marchait » techniquement (aucune erreur SQL) mais produisait un résultat
incorrect (quasi produit cartésien). Trouvé en relisant le modèle plutôt
qu'en attendant qu'un test échoue — bon rappel que l'absence d'erreur
n'est pas une preuve de correction.

**5. Bug de routage FastAPI.** `/stations/comparer` était déclarée après
`/stations/{station_id}` : FastAPI aurait matché "comparer" comme une
valeur de `station_id` avant d'atteindre la bonne route. Corrigé par
l'ordre de déclaration, avec un test de non-régression explicite.

**6. Découverte méthodologique sur une source de scraping.** Pour les
bulletins neige, plutôt que de scraper du HTML fragile, j'ai trouvé que
skiinfo.fr publie un bloc JSON-LD structuré (`schema.org/SkiResort`). Comme
toutes les stations françaises étaient hors-saison au moment du
développement, impossible de valider le schéma complet sur des données
réelles locales — j'ai testé sur un domaine skiable actuellement ouvert
dans l'hémisphère sud (Chili, saison inversée) pour confirmer la structure
complète des champs avant d'écrire le parsing.

**7. Diagnostic d'une lenteur perçue côté utilisateur ("Ajouter au
comparateur" prend plusieurs secondes).** Plutôt que de supposer la cause,
mesuré en direct avec le connecteur Snowflake en mode debug : la requête
SQL elle-même prend 0.15s, mais établir une connexion Snowflake en prend
~65s — y compris quand le warehouse est déjà démarré (vérifié via `SHOW
WAREHOUSES` : état `STARTED`), ce qui exclut un simple "réveil" de
warehouse. Les logs montrent que le temps est concentré sur un seul appel
HTTP (`POST /session/v1/login-request`), pas sur la vérification OCSP
(servie depuis le cache local, donc rapide). Cause architecturale : l'API
(`api/core/snowflake_client.py`) ouvre une connexion neuve à chaque
requête HTTP (voir "Limites actuelles"), contrairement à `dbt run` qui
réutilise une seule connexion pour tout le run — d'où l'impression que dbt
"va vite" après le premier modèle, alors que l'API paie ce coût à chaque
clic. Bonne illustration de "mesurer avant de corriger" : la première
hypothèse (warehouse suspendu) s'est révélée fausse une fois testée.

## Tests et qualité

- Tests unitaires Python (`pytest`) sur toute la couche ingestion et API :
  mocks des appels réseau/DB, aucun test ne touche un vrai service externe.
- Tests dbt déclaratifs sur les modèles marts (`not_null`, `unique`,
  `accepted_range`).
- Vérification manuelle en conditions réelles à chaque étape (contre
  Snowflake réel, puis dans un vrai navigateur via Playwright installé
  ponctuellement) plutôt que de se fier uniquement aux tests automatisés.

## Limites actuelles, assumées

- Pas d'historique : chargement Snowflake en delete+insert, pas d'append —
  un seul snapshot à la fois, pas de tendance dans le temps pour l'instant.
- Score de qualité neige basé sur des seuils de normalisation choisis
  arbitrairement (ex. 100cm = plein score enneigement), faute de données
  réelles en saison au moment du développement — à recalibrer.
- `altitude_min`/`altitude_max` (fourchette du domaine skiable) non
  résolus : aucune des 3 sources ne les fournit.
- Pas de pool de connexions Snowflake côté API (une connexion par requête
  HTTP) — pragmatique à cette échelle, mais mesuré comme coûteux en
  pratique (~65s par connexion contre 0.15s pour la requête elle-même, voir
  problème #7 ci-dessus). Le vrai coût utilisateur n'est donc pas la
  requête mais l'absence de réutilisation de connexion — correction
  identifiée (connexion persistante/pool au démarrage de l'API plutôt que
  par requête) mais pas encore appliquée.

## Questions probables et pistes de réponse

**"Pourquoi Snowflake et pas Postgres ?"**
Pour le côté entrepôt analytique cloud et l'intégration native avec dbt,
dans l'optique de démontrer la stack data (pas juste un CRUD classique).

**"Pourquoi MongoDB en bronze et pas directement dans Snowflake ?"**
Séparer la couche brute (fidèle à la source, schéma flexible, peu coûteuse)
de la couche analytique (structurée, typée) — modèle médaillon classique.
Permet aussi de rejouer la transformation sans refaire les appels API.

**"Comment gères-tu les pannes d'une source externe ?"**
Chaque source a sa propre stratégie de dégradation : Overpass →
`null` + continuer le batch ; BRA hors-saison → champ explicite
`hors_saison` plutôt qu'une erreur ; JSON-LD absent → enregistrement avec
champs à `null` plutôt qu'exception. Toujours : ne jamais faire échouer
tout le run pour une ligne.

**"Comment tu valides qu'un modèle dbt est correct ?"**
Tests déclaratifs dbt + vérification manuelle du résultat contre la
donnée source (ex. recalcul à la main du score pour une station pour
vérifier la formule).

**"Qu'est-ce que tu ferais différemment avec plus de temps ?"**
Un vrai mécanisme d'historisation (append + SCD plutôt que delete+insert),
un pool de connexions pour l'API, et recalibrer le score avec des données
de saison réelles plutôt que des seuils choisis à l'aveugle.

**"Comment tu débogues un problème de lenteur perçue par l'utilisateur ?"**
Exemple concret sur ce projet : "Ajouter au comparateur" semblait lent.
Plutôt que de deviner, j'ai mesuré séparément le temps de connexion
Snowflake et le temps d'exécution de la requête (logs du connecteur en
mode debug). Résultat : la requête prend 0.15s, la connexion ~65s — et ce
même warehouse déjà démarré, ce qui a invalidé ma première hypothèse
("le warehouse se réveille"). La vraie cause : l'API ouvre une connexion
neuve à chaque requête HTTP au lieu d'en réutiliser une. Mesurer avant de
corriger évite de corriger la mauvaise chose.
