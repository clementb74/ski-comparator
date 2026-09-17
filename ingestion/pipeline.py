"""Point d'entrée du pipeline d'ingestion.

Orchestre la collecte des sources (référentiel stations, météo/avalanche par
massif ; bulletins neige à venir) et l'écriture en couche bronze (MongoDB) +
raw (Snowflake).
"""
import logging
from pathlib import Path

from ingestion.sinks.mongodb_sink import write_bronze
from ingestion.sinks.snowflake_sink import load_raw_meteo_releves, load_raw_stations_referentiel
from ingestion.sources.meteo_france import fetch_meteo_massifs
from ingestion.sources.stations_referentiel import fetch_referentiel_stations

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
PERIMETRE_CSV_PATH = REPO_ROOT / "dbt_project" / "seeds" / "perimetre_stations.csv"
MASSIF_BRA_CSV_PATH = REPO_ROOT / "dbt_project" / "seeds" / "stations_massif_bra.csv"


def run() -> None:
    logging.basicConfig(level=logging.INFO)

    stations = fetch_referentiel_stations(PERIMETRE_CSV_PATH)
    logger.info("Référentiel stations : %d enregistrements récupérés", len(stations))

    write_bronze(stations, collection="raw_stations_referentiel")
    logger.info("Référentiel stations écrit en bronze (MongoDB)")

    load_raw_stations_referentiel(stations)
    logger.info("Référentiel stations chargé en raw (Snowflake)")

    massifs = fetch_meteo_massifs(MASSIF_BRA_CSV_PATH)
    logger.info("Météo/avalanche : %d massifs récupérés", len(massifs))

    write_bronze(massifs, collection="raw_meteo_releves", key_field="id_massif_bra")
    logger.info("Météo/avalanche écrit en bronze (MongoDB)")

    load_raw_meteo_releves(massifs)
    logger.info("Météo/avalanche chargé en raw (Snowflake)")


if __name__ == "__main__":
    run()
