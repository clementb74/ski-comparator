"""Récupération des bulletins risque avalanche / enneigement par massif (BRA, Météo-France).

Source : API BRA sur portail-api.meteofrance.fr / public-api.meteofrance.fr
(inscription + abonnement requis, voir CLAUDE.md). Un appel par massif BRA
(pas par station) : le mapping station -> massif vient du seed dbt
dbt_project/seeds/stations_massif_bra.csv.

Le schéma XML du bulletin "en saison" n'a pas pu être vérifié sur des
données réelles (API testée hors-saison, réponse `<message>`). Le parsing
des champs en saison (DATEBULLETIN, CARTOUCHERISQUE/RISQUE, ...) est basé
sur une source tierce, pas la documentation officielle — à revalider en
novembre. Le XML brut est toujours conservé pour permettre une ré-analyse.
"""
import csv
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import requests

from ingestion.config import settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://portail-api.meteofrance.fr/token"
BRA_URL = "https://public-api.meteofrance.fr/public/DPBRA/v1/massif/BRA"
RATE_LIMIT_SECONDS = 0.5


def _lire_mapping_massifs(mapping_csv_path: Path) -> list[dict]:
    with open(mapping_csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    massifs = {}
    for row in rows:
        id_massif = row["id_massif_bra"]
        massifs[id_massif] = {
            "id_massif_bra": int(id_massif),
            "nom_massif_bra": row["nom_massif_bra"],
        }
    return list(massifs.values())


def _obtenir_token() -> str:
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        headers={"Authorization": settings.meteo_france_authorization},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _recuperer_bulletin_massif(token: str, id_massif: int) -> str:
    response = requests.get(
        BRA_URL,
        params={"id-massif": id_massif, "format": "xml"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def _parser_bulletin(xml_text: str) -> dict:
    root = ElementTree.fromstring(xml_text)

    if root.tag == "message":
        return {
            "hors_saison": True,
            "date_bulletin": None,
            "risque_maxi": None,
            "risque_maxi_j2": None,
            "declenchement_accidentel": None,
            "declenchement_naturel": None,
            "resume": root.text,
        }

    cartouche_risque = root.find(".//CARTOUCHERISQUE")
    risque = cartouche_risque.find("RISQUE") if cartouche_risque is not None else None

    def _texte(element, tag):
        if element is None:
            return None
        enfant = element.find(tag)
        return enfant.text if enfant is not None else None

    return {
        "hors_saison": False,
        "date_bulletin": root.get("DATEBULLETIN"),
        "risque_maxi": risque.get("RISQUEMAXI") if risque is not None else None,
        "risque_maxi_j2": risque.get("RISQUEMAXIJ2") if risque is not None else None,
        "declenchement_accidentel": _texte(cartouche_risque, "ACCIDENTEL"),
        "declenchement_naturel": _texte(cartouche_risque, "NATUREL"),
        "resume": _texte(cartouche_risque, "RESUME"),
    }


def fetch_meteo_massifs(mapping_csv_path: Path) -> list[dict]:
    """Récupère un bulletin BRA par massif distinct référencé dans le mapping station->massif."""
    massifs = _lire_mapping_massifs(mapping_csv_path)
    token = _obtenir_token()
    records = []

    for i, massif in enumerate(massifs):
        if i > 0:
            time.sleep(RATE_LIMIT_SECONDS)

        raw_xml = _recuperer_bulletin_massif(token, massif["id_massif_bra"])
        champs = _parser_bulletin(raw_xml)

        records.append(
            {
                "id_massif_bra": massif["id_massif_bra"],
                "nom_massif_bra": massif["nom_massif_bra"],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "raw_xml": raw_xml,
                **champs,
            }
        )

    return records
