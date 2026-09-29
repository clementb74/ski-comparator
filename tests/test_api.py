"""Tests pour l'API FastAPI."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

STATION_VAL_THORENS = {
    "station_id": "val-thorens",
    "nom_station": "Val Thorens",
    "massif": "Alpes du Nord",
    "altitude_m": 2318.0,
    "latitude": 45.29,
    "longitude": 6.58,
    "score_qualite_neige": 42.5,
    "niveau_risque_avalanche": "3",
}

STATION_TIGNES = {
    "station_id": "tignes",
    "nom_station": "Tignes",
    "massif": "Alpes du Nord",
    "altitude_m": 2100.0,
    "latitude": 45.47,
    "longitude": 6.9,
    "score_qualite_neige": None,
    "niveau_risque_avalanche": None,
}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_lister_stations_sans_filtre():
    with patch("api.routers.stations.run_query") as mock_run_query:
        mock_run_query.return_value = [STATION_VAL_THORENS, STATION_TIGNES]

        response = client.get("/api/v1/stations")

    assert response.status_code == 200
    assert len(response.json()) == 2
    sql, params = mock_run_query.call_args.args
    assert "where" not in sql.lower()
    assert params == []


def test_lister_stations_filtre_massif():
    with patch("api.routers.stations.run_query") as mock_run_query:
        mock_run_query.return_value = [STATION_VAL_THORENS]

        response = client.get("/api/v1/stations", params={"massif": "Alpes du Nord"})

    assert response.status_code == 200
    sql, params = mock_run_query.call_args.args
    assert "d.massif = %s" in sql
    assert params == ["Alpes du Nord"]


def test_detail_station_trouvee():
    with patch("api.routers.stations.run_query") as mock_run_query:
        mock_run_query.return_value = [STATION_VAL_THORENS]

        response = client.get("/api/v1/stations/val-thorens")

    assert response.status_code == 200
    assert response.json()["station_id"] == "val-thorens"


def test_detail_station_introuvable():
    with patch("api.routers.stations.run_query") as mock_run_query:
        mock_run_query.return_value = []

        response = client.get("/api/v1/stations/station-inconnue")

    assert response.status_code == 404


def test_comparer_stations():
    with patch("api.routers.stations.run_query") as mock_run_query:
        mock_run_query.return_value = [STATION_VAL_THORENS, STATION_TIGNES]

        response = client.get(
            "/api/v1/stations/comparer", params={"ids": ["val-thorens", "tignes"]}
        )

    assert response.status_code == 200
    assert len(response.json()) == 2
    sql, params = mock_run_query.call_args.args
    assert "in (%s, %s)" in sql
    assert params == ["val-thorens", "tignes"]


def test_comparer_stations_route_pas_capturee_par_detail():
    """Vérifie le fix d'ordre de routage : /comparer ne doit pas matcher /{station_id}."""
    with patch("api.routers.stations.run_query") as mock_run_query:
        mock_run_query.return_value = []

        response = client.get("/api/v1/stations/comparer", params={"ids": ["val-thorens"]})

    assert response.status_code == 200


def test_recommander_stations_tri_par_score():
    with patch("api.routers.recommandations.run_query") as mock_run_query:
        mock_run_query.return_value = [STATION_VAL_THORENS]

        response = client.get("/api/v1/recommandations", params={"massif": "Alpes du Nord"})

    assert response.status_code == 200
    sql, params = mock_run_query.call_args.args
    assert "order by m.score_qualite_neige desc nulls last" in sql.lower()
    assert params == ["Alpes du Nord", 10]
