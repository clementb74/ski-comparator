"""Endpoints liés aux stations de ski."""
from fastapi import APIRouter

from api.models.schemas import Station

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[Station])
def lister_stations(massif: str | None = None, niveau: str | None = None):
    """Liste des stations avec filtres optionnels (massif, niveau, etc.)."""
    # TODO: interroger la table mart_score_qualite_neige / dim_stations sur Snowflake
    raise NotImplementedError


@router.get("/{station_id}", response_model=Station)
def detail_station(station_id: str):
    """Détail d'une station : score, historique enneigement."""
    # TODO: interroger Snowflake pour la station donnée
    raise NotImplementedError


@router.get("/comparer", response_model=list[Station])
def comparer_stations(ids: list[str]):
    """Comparaison de plusieurs stations."""
    # TODO: interroger Snowflake pour la liste de stations donnée
    raise NotImplementedError
