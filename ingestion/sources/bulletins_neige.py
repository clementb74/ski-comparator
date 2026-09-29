"""Récupération des bulletins neige par station (hauteur de neige, état des pistes).

Source : skiinfo.fr, qui publie pour chaque station un bloc JSON-LD structuré
(schema.org/SkiResort) plutôt que de nécessiter un scraping HTML fragile.
Vérifié légal (robots.txt : Allow: /, aucune restriction) et vérifié en
conditions réelles sur un resort ouvert (schéma complet avec hauteur de
neige et pistes/remontées ouvertes, voir CLAUDE.md). Le mapping station ->
slug skiinfo.fr vient du seed dbt
dbt_project/seeds/stations_skiinfo_slug.csv (4 slugs diffèrent du station_id).
"""
import csv
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BULLETIN_URL = "https://www.skiinfo.fr/alpes-du-nord/{slug}/bulletin-neige"
USER_AGENT = "ski-comparator-portfolio/0.1 (clementbousson@gmail.com)"
RATE_LIMIT_SECONDS = 0.5

_JSON_LD_RE = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)

_PROPRIETES = {
    "resort_status": "Resort status",
    "last_snow_report_update": "Last snow report update",
    "base_snow_depth": "Base snow depth",
    "summit_snow_depth": "Summit snow depth",
    "last_snowfall_amount": "Last snowfall amount",
    "last_snowfall_date": "Last snowfall date",
    "open_trails": "Open trails",
    "open_lifts": "Open lifts",
    "projected_season_opening_date": "Projected season opening date",
    "projected_season_closing_date": "Projected season closing date",
}


def _lire_mapping_slugs(mapping_csv_path: Path) -> list[dict]:
    with open(mapping_csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _recuperer_page(slug: str) -> str:
    response = requests.get(
        BULLETIN_URL.format(slug=slug),
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    return response.text


def _extraire_json_ld_skiresort(html: str) -> dict | None:
    for bloc in _JSON_LD_RE.findall(html):
        try:
            objet = json.loads(bloc)
        except json.JSONDecodeError:
            continue
        if objet.get("@type") == "SkiResort" and "additionalProperty" in objet:
            return objet
    return None


def _parser_proprietes(json_ld: dict) -> dict:
    proprietes = {
        prop["name"]: (prop.get("value"), prop.get("unitText"))
        for prop in json_ld.get("additionalProperty", [])
    }

    champs = {}
    for champ, nom_propriete in _PROPRIETES.items():
        valeur, unite = proprietes.get(nom_propriete, (None, None))
        champs[champ] = valeur
        if unite is not None:
            champs[f"{champ}_unit"] = unite
    for champ in ("base_snow_depth", "summit_snow_depth", "last_snowfall_amount"):
        champs.setdefault(f"{champ}_unit", None)

    return champs


def fetch_bulletins_neige(mapping_csv_path: Path) -> list[dict]:
    """Récupère le bulletin neige (JSON-LD skiinfo.fr) pour chaque station du mapping."""
    stations = _lire_mapping_slugs(mapping_csv_path)
    records = []

    for i, station in enumerate(stations):
        if i > 0:
            time.sleep(RATE_LIMIT_SECONDS)

        station_id = station["station_id"]
        html = _recuperer_page(station["skiinfo_slug"])
        json_ld = _extraire_json_ld_skiresort(html)

        if json_ld is None:
            logger.warning("Bloc JSON-LD SkiResort introuvable pour %r", station_id)
            record = {champ: None for champ in _PROPRIETES}
            record.update(
                base_snow_depth_unit=None,
                summit_snow_depth_unit=None,
                last_snowfall_amount_unit=None,
            )
            record["raw_json_ld"] = None
        else:
            record = _parser_proprietes(json_ld)
            record["raw_json_ld"] = json_ld

        record["station_id"] = station_id
        record["ingested_at"] = datetime.now(timezone.utc).isoformat()
        records.append(record)

    return records
