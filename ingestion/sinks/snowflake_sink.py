"""Chargement des données structurées en couche raw (Snowflake), lue par dbt source()."""
import snowflake.connector

from ingestion.config import settings

_COLUMNS = (
    "station_id",
    "nom_station",
    "massif",
    "sous_massif",
    "altitude_m",
    "latitude",
    "longitude",
    "departement",
    "region",
    "ingested_at",
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS raw_stations_referentiel (
    station_id VARCHAR,
    nom_station VARCHAR,
    massif VARCHAR,
    sous_massif VARCHAR,
    altitude_m NUMBER,
    latitude FLOAT,
    longitude FLOAT,
    departement VARCHAR,
    region VARCHAR,
    ingested_at TIMESTAMP_NTZ
)
"""


def _connect():
    return snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
        schema=settings.snowflake_schema,
    )


def load_raw_stations_referentiel(records: list[dict]) -> None:
    """Recharge la table raw_stations_referentiel pour les stations fournies (delete + insert)."""
    if not records:
        return

    station_ids = [r["station_id"] for r in records]
    rows = [tuple(r[col] for col in _COLUMNS) for r in records]

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(_CREATE_TABLE)
        placeholders = ", ".join(["%s"] * len(station_ids))
        cur.execute(
            f"DELETE FROM raw_stations_referentiel WHERE station_id IN ({placeholders})",
            station_ids,
        )
        cur.executemany(
            f"INSERT INTO raw_stations_referentiel ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join(['%s'] * len(_COLUMNS))})",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
