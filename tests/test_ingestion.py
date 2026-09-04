"""Tests pour les modules d'ingestion."""
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from ingestion.sinks.mongodb_sink import write_bronze
from ingestion.sinks.snowflake_sink import load_raw_stations_referentiel
from ingestion.sources.stations_referentiel import fetch_referentiel_stations

NOMINATIM_RESULT = {
    "osm_type": "node",
    "osm_id": 2376164369,
    "lat": "45.2979109",
    "lon": "6.5822693",
    "address": {"county": "Savoie", "state": "Auvergne-Rhône-Alpes"},
}

OVERPASS_RESULT = {
    "type": "node",
    "id": 2376164369,
    "tags": {"ele": "2318", "name": "Val Thorens"},
}


def _write_perimetre_csv(tmp_path: Path, rows: list[dict]) -> Path:
    csv_path = tmp_path / "perimetre_stations.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["station_id", "nom_station", "massif", "sous_massif", "actif"]
        )
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def test_fetch_referentiel_stations_cas_nominal(tmp_path):
    csv_path = _write_perimetre_csv(
        tmp_path,
        [
            {
                "station_id": "val-thorens",
                "nom_station": "Val Thorens",
                "massif": "Alpes du Nord",
                "sous_massif": "Vanoise",
                "actif": "true",
            }
        ],
    )

    with patch("ingestion.sources.stations_referentiel.requests.get") as mock_get, patch(
        "ingestion.sources.stations_referentiel.requests.post"
    ) as mock_post, patch("ingestion.sources.stations_referentiel.time.sleep"):
        mock_get.return_value = MagicMock(json=lambda: [NOMINATIM_RESULT])
        mock_post.return_value = MagicMock(
            json=lambda: {"elements": [OVERPASS_RESULT]}
        )

        records = fetch_referentiel_stations(csv_path)

    assert len(records) == 1
    record = records[0]
    assert record["station_id"] == "val-thorens"
    assert record["altitude_m"] == 2318.0
    assert record["latitude"] == 45.2979109
    assert record["departement"] == "Savoie"


def test_fetch_referentiel_stations_overpass_indisponible(tmp_path):
    csv_path = _write_perimetre_csv(
        tmp_path,
        [
            {
                "station_id": "val-thorens",
                "nom_station": "Val Thorens",
                "massif": "Alpes du Nord",
                "sous_massif": "Vanoise",
                "actif": "true",
            }
        ],
    )

    with patch("ingestion.sources.stations_referentiel.requests.get") as mock_get, patch(
        "ingestion.sources.stations_referentiel.requests.post"
    ) as mock_post, patch("ingestion.sources.stations_referentiel.time.sleep"):
        mock_get.return_value = MagicMock(json=lambda: [NOMINATIM_RESULT])
        mock_post.side_effect = requests.exceptions.HTTPError("504 Gateway Timeout")

        records = fetch_referentiel_stations(csv_path)

    assert len(records) == 1
    assert records[0]["altitude_m"] is None
    assert records[0]["latitude"] == 45.2979109


def test_fetch_referentiel_stations_ignore_inactives(tmp_path):
    csv_path = _write_perimetre_csv(
        tmp_path,
        [
            {
                "station_id": "val-thorens",
                "nom_station": "Val Thorens",
                "massif": "Alpes du Nord",
                "sous_massif": "Vanoise",
                "actif": "false",
            }
        ],
    )

    with patch("ingestion.sources.stations_referentiel.requests.get") as mock_get:
        records = fetch_referentiel_stations(csv_path)

    mock_get.assert_not_called()
    assert records == []


def test_fetch_referentiel_stations_nominatim_sans_resultat(tmp_path):
    csv_path = _write_perimetre_csv(
        tmp_path,
        [
            {
                "station_id": "station-inconnue",
                "nom_station": "Station Inconnue",
                "massif": "Alpes du Nord",
                "sous_massif": "Vanoise",
                "actif": "true",
            }
        ],
    )

    with patch("ingestion.sources.stations_referentiel.requests.get") as mock_get, patch(
        "ingestion.sources.stations_referentiel.requests.post"
    ) as mock_post:
        mock_get.return_value = MagicMock(json=lambda: [])

        records = fetch_referentiel_stations(csv_path)

    mock_post.assert_not_called()
    assert len(records) == 1
    assert records[0]["altitude_m"] is None
    assert records[0]["latitude"] is None


def test_write_bronze_upsert_par_station_id():
    mock_client = MagicMock()
    mock_collection = mock_client.__getitem__.return_value.__getitem__.return_value

    with patch("ingestion.sinks.mongodb_sink.pymongo.MongoClient", return_value=mock_client):
        write_bronze([{"station_id": "val-thorens", "nom_station": "Val Thorens"}], "raw_stations_referentiel")

    mock_collection.update_one.assert_called_once_with(
        {"station_id": "val-thorens"},
        {"$set": {"station_id": "val-thorens", "nom_station": "Val Thorens"}},
        upsert=True,
    )
    mock_client.close.assert_called_once()


def test_load_raw_stations_referentiel_delete_puis_insert():
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value

    record = {
        "station_id": "val-thorens",
        "nom_station": "Val Thorens",
        "massif": "Alpes du Nord",
        "sous_massif": "Vanoise",
        "altitude_m": 2318.0,
        "latitude": 45.29,
        "longitude": 6.58,
        "departement": "Savoie",
        "region": "Auvergne-Rhône-Alpes",
        "ingested_at": "2026-09-04T10:00:00+00:00",
    }

    with patch(
        "ingestion.sinks.snowflake_sink._connect", return_value=mock_conn
    ):
        load_raw_stations_referentiel([record])

    delete_call = mock_cursor.execute.call_args_list[1]
    assert "DELETE FROM raw_stations_referentiel" in delete_call.args[0]
    assert delete_call.args[1] == ["val-thorens"]

    insert_call = mock_cursor.executemany.call_args
    assert "INSERT INTO raw_stations_referentiel" in insert_call.args[0]
    mock_conn.commit.assert_called_once()


def test_load_raw_stations_referentiel_liste_vide_ne_se_connecte_pas():
    with patch("ingestion.sinks.snowflake_sink._connect") as mock_connect:
        load_raw_stations_referentiel([])

    mock_connect.assert_not_called()
