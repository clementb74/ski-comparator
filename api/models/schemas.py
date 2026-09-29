"""Modèles Pydantic pour les entrées/sorties de l'API."""
from pydantic import BaseModel


class Station(BaseModel):
    station_id: str
    nom_station: str
    massif: str
    # Point unique (village/centre station, source OSM), pas la fourchette
    # du domaine skiable — voir CLAUDE.md, altitude_min/max non résolu.
    altitude_m: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    score_qualite_neige: float | None = None
    niveau_risque_avalanche: str | None = None


class StationFiltres(BaseModel):
    # niveau/budget_max retirés : aucune source n'ingère difficulté de
    # pistes ou prix pour l'instant (voir CLAUDE.md).
    massif: str | None = None
    altitude_min: float | None = None
    altitude_max: float | None = None
