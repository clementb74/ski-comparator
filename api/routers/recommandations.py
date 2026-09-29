"""Endpoint de recommandation de stations.

Version simplifiée : classement par score_qualite_neige, filtrable par
massif. Les critères niveau/budget prévus par la spec ne sont pas
implémentés faute de données (voir CLAUDE.md).
"""
from fastapi import APIRouter

from api.core.snowflake_client import run_query
from api.models.schemas import Station

router = APIRouter(prefix="/recommandations", tags=["recommandations"])


@router.get("", response_model=list[Station])
def recommander_stations(massif: str | None = None, limit: int = 10):
    """Stations triées par score de qualité neige décroissant."""
    sql = """
    select
        d.station_id,
        d.nom_station,
        d.massif,
        d.altitude_m,
        d.latitude,
        d.longitude,
        m.score_qualite_neige,
        m.niveau_risque_avalanche
    from dim_stations d
    left join mart_score_qualite_neige m on d.station_id = m.station_id
    """
    params: list = []
    if massif is not None:
        sql += " where d.massif = %s"
        params.append(massif)

    sql += " order by m.score_qualite_neige desc nulls last limit %s"
    params.append(limit)

    return run_query(sql, params)
