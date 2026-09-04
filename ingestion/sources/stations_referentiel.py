"""Récupération du référentiel des stations de ski (nom, altitude, coordonnées).

Source : OpenStreetMap (Nominatim pour le géocodage, Overpass pour les tags),
pas data.gouv.fr — aucun jeu de données data.gouv.fr propre et couvrant
l'ensemble du territoire n'a été trouvé (voir docs/SPEC-comparateur-ski.md et
CLAUDE.md). Le périmètre des stations à interroger vient du seed dbt
dbt_project/seeds/perimetre_stations.csv, qui reste la source de vérité pour
station_id/nom_station/massif/sous_massif.
"""
import csv
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Politique d'usage Nominatim : User-Agent explicite obligatoire, 1 req/s max.
USER_AGENT = "ski-comparator-portfolio/0.1 (clementbousson@gmail.com)"
RATE_LIMIT_SECONDS = 1.0


def _lire_perimetre(perimetre_csv_path: Path) -> list[dict]:
    with open(perimetre_csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [row for row in rows if row["actif"].strip().lower() == "true"]


def _geocoder_nominatim(nom_station: str) -> dict | None:
    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": f"{nom_station}, France",
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    response.raise_for_status()
    results = response.json()
    return results[0] if results else None


def _recuperer_tags_overpass(osm_type: str, osm_id: int) -> dict | None:
    query = f"[out:json][timeout:25];{osm_type}({osm_id});out tags;"
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # L'instance publique overpass-api.de est partagée et répond parfois
        # par des 504 sous charge ; l'altitude reste nullable, donc on continue
        # plutôt que de faire échouer tout le batch pour une station.
        logger.warning("Overpass indisponible pour %s(%s) : %s", osm_type, osm_id, exc)
        return None

    payload = response.json()
    elements = payload.get("elements", [])
    return elements[0] if elements else None


def fetch_referentiel_stations(perimetre_csv_path: Path) -> list[dict]:
    """Récupère nom, altitude et coordonnées pour les stations actives du périmètre pilote."""
    stations = _lire_perimetre(perimetre_csv_path)
    records = []

    for i, station in enumerate(stations):
        nom_station = station["nom_station"]
        if i > 0:
            time.sleep(RATE_LIMIT_SECONDS)

        raw_nominatim = _geocoder_nominatim(nom_station)
        if raw_nominatim is None:
            logger.warning("Nominatim n'a trouvé aucun résultat pour %r", nom_station)
            records.append(
                {
                    "station_id": station["station_id"],
                    "nom_station": nom_station,
                    "massif": station["massif"],
                    "sous_massif": station["sous_massif"],
                    "altitude_m": None,
                    "latitude": None,
                    "longitude": None,
                    "departement": None,
                    "region": None,
                    "osm_type": None,
                    "osm_id": None,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "raw_nominatim": None,
                    "raw_overpass": None,
                }
            )
            continue

        osm_type = raw_nominatim["osm_type"]
        osm_id = raw_nominatim["osm_id"]
        address = raw_nominatim.get("address", {})

        time.sleep(RATE_LIMIT_SECONDS)
        raw_overpass = _recuperer_tags_overpass(osm_type, osm_id)
        altitude_m = None
        if raw_overpass is not None:
            ele = raw_overpass.get("tags", {}).get("ele")
            altitude_m = float(ele) if ele is not None else None

        records.append(
            {
                "station_id": station["station_id"],
                "nom_station": nom_station,
                "massif": station["massif"],
                "sous_massif": station["sous_massif"],
                "altitude_m": altitude_m,
                "latitude": float(raw_nominatim["lat"]),
                "longitude": float(raw_nominatim["lon"]),
                "departement": address.get("county"),
                "region": address.get("state"),
                "osm_type": osm_type,
                "osm_id": osm_id,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "raw_nominatim": raw_nominatim,
                "raw_overpass": raw_overpass,
            }
        )

    return records
