"""Accès en lecture à Snowflake pour l'API (connexion par requête HTTP)."""
import snowflake.connector

from api.core.config import settings


def _connect():
    return snowflake.connector.connect(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
        schema=settings.snowflake_schema,
    )


def run_query(sql: str, params: tuple | list | None = None) -> list[dict]:
    """Exécute une requête et retourne les lignes en dicts (clés en minuscules)."""
    conn = _connect()
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute(sql, params or [])
        return [{k.lower(): v for k, v in row.items()} for row in cur.fetchall()]
    finally:
        conn.close()
