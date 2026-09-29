"""Chargement des données structurées en couche raw (Snowflake), lue par dbt source()."""
import snowflake.connector

from ingestion.config import settings

_STATIONS_REFERENTIEL_COLUMNS = (
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

_STATIONS_REFERENTIEL_CREATE_TABLE = """
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

_METEO_RELEVES_COLUMNS = (
    "id_massif_bra",
    "nom_massif_bra",
    "hors_saison",
    "date_bulletin",
    "risque_maxi",
    "risque_maxi_j2",
    "declenchement_accidentel",
    "declenchement_naturel",
    "resume",
    "ingested_at",
)

_METEO_RELEVES_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS raw_meteo_releves (
    id_massif_bra NUMBER,
    nom_massif_bra VARCHAR,
    hors_saison BOOLEAN,
    date_bulletin VARCHAR,
    risque_maxi VARCHAR,
    risque_maxi_j2 VARCHAR,
    declenchement_accidentel VARCHAR,
    declenchement_naturel VARCHAR,
    resume VARCHAR,
    ingested_at TIMESTAMP_NTZ
)
"""


_BULLETINS_NEIGE_COLUMNS = (
    "station_id",
    "resort_status",
    "last_snow_report_update",
    "base_snow_depth",
    "base_snow_depth_unit",
    "summit_snow_depth",
    "summit_snow_depth_unit",
    "last_snowfall_amount",
    "last_snowfall_amount_unit",
    "last_snowfall_date",
    "open_trails",
    "open_lifts",
    "projected_season_opening_date",
    "projected_season_closing_date",
    "ingested_at",
)

_BULLETINS_NEIGE_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS raw_bulletins_neige (
    station_id VARCHAR,
    resort_status VARCHAR,
    last_snow_report_update VARCHAR,
    base_snow_depth NUMBER,
    base_snow_depth_unit VARCHAR,
    summit_snow_depth NUMBER,
    summit_snow_depth_unit VARCHAR,
    last_snowfall_amount NUMBER,
    last_snowfall_amount_unit VARCHAR,
    last_snowfall_date VARCHAR,
    open_trails NUMBER,
    open_lifts NUMBER,
    projected_season_opening_date VARCHAR,
    projected_season_closing_date VARCHAR,
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


def _recharger_table(
    table: str,
    create_table_ddl: str,
    columns: tuple[str, ...],
    key_column: str,
    records: list[dict],
) -> None:
    """Recharge une table raw pour les enregistrements fournis (delete + insert par key_column)."""
    if not records:
        return

    key_values = [r[key_column] for r in records]
    rows = [tuple(r[col] for col in columns) for r in records]

    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(create_table_ddl)
        placeholders = ", ".join(["%s"] * len(key_values))
        cur.execute(
            f"DELETE FROM {table} WHERE {key_column} IN ({placeholders})",
            key_values,
        )
        cur.executemany(
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join(['%s'] * len(columns))})",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def load_raw_stations_referentiel(records: list[dict]) -> None:
    """Recharge la table raw_stations_referentiel pour les stations fournies."""
    _recharger_table(
        "raw_stations_referentiel",
        _STATIONS_REFERENTIEL_CREATE_TABLE,
        _STATIONS_REFERENTIEL_COLUMNS,
        "station_id",
        records,
    )


def load_raw_meteo_releves(records: list[dict]) -> None:
    """Recharge la table raw_meteo_releves pour les massifs fournis."""
    _recharger_table(
        "raw_meteo_releves",
        _METEO_RELEVES_CREATE_TABLE,
        _METEO_RELEVES_COLUMNS,
        "id_massif_bra",
        records,
    )


def load_raw_bulletins_neige(records: list[dict]) -> None:
    """Recharge la table raw_bulletins_neige pour les stations fournies."""
    _recharger_table(
        "raw_bulletins_neige",
        _BULLETINS_NEIGE_CREATE_TABLE,
        _BULLETINS_NEIGE_COLUMNS,
        "station_id",
        records,
    )
