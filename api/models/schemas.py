"""Modèles Pydantic pour les entrées/sorties de l'API."""
from pydantic import BaseModel


class Station(BaseModel):
    station_id: str
    nom_station: str
    massif: str
    altitude_min: int
    altitude_max: int
    latitude: float
    longitude: float
    score_qualite_neige: float | None = None


class StationFiltres(BaseModel):
    massif: str | None = None
    altitude_min: int | None = None
    niveau: str | None = None
    budget_max: float | None = None
