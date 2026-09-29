"""Tests pour les modules d'ingestion."""
import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from ingestion.sinks.mongodb_sink import write_bronze
from ingestion.sinks.snowflake_sink import (
    load_raw_bulletins_neige,
    load_raw_meteo_releves,
    load_raw_stations_referentiel,
)
from ingestion.sources.bulletins_neige import fetch_bulletins_neige
from ingestion.sources.meteo_france import fetch_meteo_massifs
from ingestion.sources.stations_referentiel import fetch_referentiel_stations

SKIINFO_HORS_SAISON_HTML = """
<html><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"SkiResort","name":"Flaine"}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"SkiResort","name":"Flaine","additionalProperty":[
{"@type":"PropertyValue","name":"Resort status","value":"Fermée"},
{"@type":"PropertyValue","name":"Last snow report update","value":"2026-04-22"},
{"@type":"PropertyValue","name":"Last snowfall amount","value":0,"unitText":"centimeters"},
{"@type":"PropertyValue","name":"Last snowfall date","value":"2026-04-22"},
{"@type":"PropertyValue","name":"Projected season opening date","value":"2026-12-05"},
{"@type":"PropertyValue","name":"Projected season closing date","value":"2027-04-04"}
]}</script>
</head><body></body></html>
"""

SKIINFO_OUVERT_HTML = """
<html><head>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"SkiResort","name":"Valle Nevado","additionalProperty":[
{"@type":"PropertyValue","name":"Resort status","value":"Open"},
{"@type":"PropertyValue","name":"Last snow report update","value":"2026-09-27"},
{"@type":"PropertyValue","name":"Base snow depth","value":89,"unitText":"centimeters"},
{"@type":"PropertyValue","name":"Summit snow depth","value":180,"unitText":"centimeters"},
{"@type":"PropertyValue","name":"Last snowfall amount","value":0,"unitText":"centimeters"},
{"@type":"PropertyValue","name":"Last snowfall date","value":"2026-09-27"},
{"@type":"PropertyValue","name":"Open trails","value":44},
{"@type":"PropertyValue","name":"Open lifts","value":13},
{"@type":"PropertyValue","name":"Projected season opening date","value":"2026-06-19"},
{"@type":"PropertyValue","name":"Projected season closing date","value":"2026-10-18"}
]}</script>
</head><body></body></html>
"""

SKIINFO_SANS_JSON_LD_HTML = "<html><head></head><body>Page introuvable</body></html>"

BRA_HORS_SAISON_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    "<message><![CDATA[Bulletin avalanche : la saison est terminée "
    "sur le massif Vanoise, rendez-vous début novembre.]]></message>"
)

BRA_ACTIF_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    '<BULLETINRISQUE DATEBULLETIN="2027-01-15T16:00:00">'
    "<CARTOUCHERISQUE>"
    '<RISQUE RISQUEMAXI="3" RISQUEMAXIJ2="4" />'
    "<ACCIDENTEL>Risque accru en versants nord au-dessus de 2200m.</ACCIDENTEL>"
    "<NATUREL>Quelques coulées spontanées possibles.</NATUREL>"
    "<RESUME>Risque marqué, prudence hors-pistes.</RESUME>"
    "</CARTOUCHERISQUE>"
    "</BULLETINRISQUE>"
)

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


def _write_mapping_csv(tmp_path: Path, rows: list[dict]) -> Path:
    csv_path = tmp_path / "stations_massif_bra.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["station_id", "id_massif_bra", "nom_massif_bra"])
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def test_fetch_meteo_massifs_hors_saison(tmp_path):
    csv_path = _write_mapping_csv(
        tmp_path, [{"station_id": "val-thorens", "id_massif_bra": "10", "nom_massif_bra": "Vanoise"}]
    )

    with patch("ingestion.sources.meteo_france.requests.post") as mock_post, patch(
        "ingestion.sources.meteo_france.requests.get"
    ) as mock_get, patch("ingestion.sources.meteo_france.time.sleep"):
        mock_post.return_value = MagicMock(json=lambda: {"access_token": "fake-token"})
        mock_get.return_value = MagicMock(text=BRA_HORS_SAISON_XML)

        records = fetch_meteo_massifs(csv_path)

    assert len(records) == 1
    assert records[0]["id_massif_bra"] == 10
    assert records[0]["hors_saison"] is True
    assert records[0]["risque_maxi"] is None
    mock_get.assert_called_once_with(
        "https://public-api.meteofrance.fr/public/DPBRA/v1/massif/BRA",
        params={"id-massif": 10, "format": "xml"},
        headers={"Authorization": "Bearer fake-token"},
        timeout=30,
    )


def test_fetch_meteo_massifs_bulletin_actif(tmp_path):
    csv_path = _write_mapping_csv(
        tmp_path, [{"station_id": "val-thorens", "id_massif_bra": "10", "nom_massif_bra": "Vanoise"}]
    )

    with patch("ingestion.sources.meteo_france.requests.post") as mock_post, patch(
        "ingestion.sources.meteo_france.requests.get"
    ) as mock_get:
        mock_post.return_value = MagicMock(json=lambda: {"access_token": "fake-token"})
        mock_get.return_value = MagicMock(text=BRA_ACTIF_XML)

        records = fetch_meteo_massifs(csv_path)

    record = records[0]
    assert record["hors_saison"] is False
    assert record["date_bulletin"] == "2027-01-15T16:00:00"
    assert record["risque_maxi"] == "3"
    assert record["risque_maxi_j2"] == "4"
    assert record["resume"] == "Risque marqué, prudence hors-pistes."


def test_fetch_meteo_massifs_deduplique_par_massif(tmp_path):
    csv_path = _write_mapping_csv(
        tmp_path,
        [
            {"station_id": "val-thorens", "id_massif_bra": "10", "nom_massif_bra": "Vanoise"},
            {"station_id": "courchevel", "id_massif_bra": "10", "nom_massif_bra": "Vanoise"},
            {"station_id": "tignes", "id_massif_bra": "6", "nom_massif_bra": "Haute-Tarentaise"},
        ],
    )

    with patch("ingestion.sources.meteo_france.requests.post") as mock_post, patch(
        "ingestion.sources.meteo_france.requests.get"
    ) as mock_get, patch("ingestion.sources.meteo_france.time.sleep"):
        mock_post.return_value = MagicMock(json=lambda: {"access_token": "fake-token"})
        mock_get.return_value = MagicMock(text=BRA_HORS_SAISON_XML)

        records = fetch_meteo_massifs(csv_path)

    assert len(records) == 2
    assert mock_get.call_count == 2
    mock_post.assert_called_once()


def test_write_bronze_key_field_personnalise():
    mock_client = MagicMock()
    mock_collection = mock_client.__getitem__.return_value.__getitem__.return_value

    with patch("ingestion.sinks.mongodb_sink.pymongo.MongoClient", return_value=mock_client):
        write_bronze(
            [{"id_massif_bra": 10, "nom_massif_bra": "Vanoise"}],
            "raw_meteo_releves",
            key_field="id_massif_bra",
        )

    mock_collection.update_one.assert_called_once_with(
        {"id_massif_bra": 10},
        {"$set": {"id_massif_bra": 10, "nom_massif_bra": "Vanoise"}},
        upsert=True,
    )


def test_load_raw_meteo_releves_delete_puis_insert():
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value

    record = {
        "id_massif_bra": 10,
        "nom_massif_bra": "Vanoise",
        "hors_saison": True,
        "date_bulletin": None,
        "risque_maxi": None,
        "risque_maxi_j2": None,
        "declenchement_accidentel": None,
        "declenchement_naturel": None,
        "resume": "Saison terminée.",
        "ingested_at": "2026-09-17T10:00:00+00:00",
    }

    with patch("ingestion.sinks.snowflake_sink._connect", return_value=mock_conn):
        load_raw_meteo_releves([record])

    delete_call = mock_cursor.execute.call_args_list[1]
    assert "DELETE FROM raw_meteo_releves" in delete_call.args[0]
    assert delete_call.args[1] == [10]

    insert_call = mock_cursor.executemany.call_args
    assert "INSERT INTO raw_meteo_releves" in insert_call.args[0]
    mock_conn.commit.assert_called_once()


def _write_slug_csv(tmp_path: Path, rows: list[dict]) -> Path:
    csv_path = tmp_path / "stations_skiinfo_slug.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["station_id", "skiinfo_slug"])
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def test_fetch_bulletins_neige_hors_saison(tmp_path):
    csv_path = _write_slug_csv(tmp_path, [{"station_id": "flaine", "skiinfo_slug": "flaine"}])

    with patch("ingestion.sources.bulletins_neige.requests.get") as mock_get, patch(
        "ingestion.sources.bulletins_neige.time.sleep"
    ):
        mock_get.return_value = MagicMock(text=SKIINFO_HORS_SAISON_HTML)

        records = fetch_bulletins_neige(csv_path)

    assert len(records) == 1
    record = records[0]
    assert record["station_id"] == "flaine"
    assert record["resort_status"] == "Fermée"
    assert record["base_snow_depth"] is None
    assert record["open_trails"] is None
    assert record["last_snowfall_amount"] == 0
    assert record["last_snowfall_amount_unit"] == "centimeters"
    mock_get.assert_called_once_with(
        "https://www.skiinfo.fr/alpes-du-nord/flaine/bulletin-neige",
        headers={"User-Agent": "ski-comparator-portfolio/0.1 (clementbousson@gmail.com)"},
        timeout=20,
    )


def test_fetch_bulletins_neige_station_ouverte(tmp_path):
    csv_path = _write_slug_csv(
        tmp_path, [{"station_id": "val-thorens", "skiinfo_slug": "val-thorens"}]
    )

    with patch("ingestion.sources.bulletins_neige.requests.get") as mock_get, patch(
        "ingestion.sources.bulletins_neige.time.sleep"
    ):
        mock_get.return_value = MagicMock(text=SKIINFO_OUVERT_HTML)

        records = fetch_bulletins_neige(csv_path)

    record = records[0]
    assert record["resort_status"] == "Open"
    assert record["base_snow_depth"] == 89
    assert record["base_snow_depth_unit"] == "centimeters"
    assert record["summit_snow_depth"] == 180
    assert record["open_trails"] == 44
    assert record["open_lifts"] == 13
    assert record["raw_json_ld"]["name"] == "Valle Nevado"


def test_fetch_bulletins_neige_json_ld_absent(tmp_path):
    csv_path = _write_slug_csv(
        tmp_path, [{"station_id": "station-x", "skiinfo_slug": "station-x"}]
    )

    with patch("ingestion.sources.bulletins_neige.requests.get") as mock_get, patch(
        "ingestion.sources.bulletins_neige.time.sleep"
    ):
        mock_get.return_value = MagicMock(text=SKIINFO_SANS_JSON_LD_HTML)

        records = fetch_bulletins_neige(csv_path)

    assert len(records) == 1
    record = records[0]
    assert record["station_id"] == "station-x"
    assert record["resort_status"] is None
    assert record["raw_json_ld"] is None


def test_load_raw_bulletins_neige_delete_puis_insert():
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value

    record = {
        "station_id": "val-thorens",
        "resort_status": "Open",
        "last_snow_report_update": "2026-09-27",
        "base_snow_depth": 89,
        "base_snow_depth_unit": "centimeters",
        "summit_snow_depth": 180,
        "summit_snow_depth_unit": "centimeters",
        "last_snowfall_amount": 0,
        "last_snowfall_amount_unit": "centimeters",
        "last_snowfall_date": "2026-09-27",
        "open_trails": 44,
        "open_lifts": 13,
        "projected_season_opening_date": "2026-06-19",
        "projected_season_closing_date": "2026-10-18",
        "ingested_at": "2026-09-29T10:00:00+00:00",
    }

    with patch("ingestion.sinks.snowflake_sink._connect", return_value=mock_conn):
        load_raw_bulletins_neige([record])

    delete_call = mock_cursor.execute.call_args_list[1]
    assert "DELETE FROM raw_bulletins_neige" in delete_call.args[0]
    assert delete_call.args[1] == ["val-thorens"]

    insert_call = mock_cursor.executemany.call_args
    assert "INSERT INTO raw_bulletins_neige" in insert_call.args[0]
    mock_conn.commit.assert_called_once()
