"""Endpoints liés aux stations de ski."""
from fastapi import APIRouter, HTTPException, Query

from api.core.snowflake_client import run_query
from api.models.schemas import Station

router = APIRouter(prefix="/stations", tags=["stations"])

_SELECT_STATIONS = """
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


@router.get("", response_model=list[Station])
def lister_stations(
    massif: str | None = None,
    altitude_min: float | None = None,
    altitude_max: float | None = None,
):
    """Liste des stations, filtrable par massif et par plage d'altitude."""
    conditions = []
    params: list = []

    if massif is not None:
        conditions.append("d.massif = %s")
        params.append(massif)
    if altitude_min is not None:
        conditions.append("d.altitude_m >= %s")
        params.append(altitude_min)
    if altitude_max is not None:
        conditions.append("d.altitude_m <= %s")
        params.append(altitude_max)

    sql = _SELECT_STATIONS
    if conditions:
        sql += " where " + " and ".join(conditions)

    return run_query(sql, params)


@router.get("/comparer", response_model=list[Station])
def comparer_stations(ids: list[str] = Query(...)):
    """Comparaison de plusieurs stations données par leurs station_id."""
    if not ids:
        raise HTTPException(status_code=400, detail="Le paramètre 'ids' ne peut pas être vide")

    placeholders = ", ".join(["%s"] * len(ids))
    sql = f"{_SELECT_STATIONS} where d.station_id in ({placeholders})"
    return run_query(sql, ids)


@router.get("/{station_id}", response_model=Station)
def detail_station(station_id: str):
    """Détail d'une station : score, risque avalanche."""
    resultats = run_query(f"{_SELECT_STATIONS} where d.station_id = %s", [station_id])
    if not resultats:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' introuvable")
    return resultats[0]
