"""Point d'entrée du pipeline d'ingestion.

Orchestre la collecte des sources (référentiel stations pour l'instant ;
météo et bulletins neige à venir) et l'écriture en couche bronze (MongoDB) +
raw (Snowflake).
"""
import logging
from pathlib import Path

from ingestion.sinks.mongodb_sink import write_bronze
from ingestion.sinks.snowflake_sink import load_raw_stations_referentiel
from ingestion.sources.stations_referentiel import fetch_referentiel_stations

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
PERIMETRE_CSV_PATH = REPO_ROOT / "dbt_project" / "seeds" / "perimetre_stations.csv"


def run() -> None:
    logging.basicConfig(level=logging.INFO)

    records = fetch_referentiel_stations(PERIMETRE_CSV_PATH)
    logger.info("Référentiel stations : %d enregistrements récupérés", len(records))

    write_bronze(records, collection="raw_stations_referentiel")
    logger.info("Référentiel stations écrit en bronze (MongoDB)")

    load_raw_stations_referentiel(records)
    logger.info("Référentiel stations chargé en raw (Snowflake)")


if __name__ == "__main__":
    run()
