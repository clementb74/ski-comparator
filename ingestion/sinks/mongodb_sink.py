"""Écriture des données brutes en couche bronze (MongoDB)."""
import pymongo

from ingestion.config import settings

DATABASE_NAME = "ski_comparator_bronze"


def write_bronze(records: list[dict], collection: str, key_field: str = "station_id") -> None:
    """Upsert une liste d'enregistrements dans une collection bronze, par key_field."""
    client = pymongo.MongoClient(settings.mongodb_uri)
    try:
        coll = client[DATABASE_NAME][collection]
        for record in records:
            coll.update_one(
                {key_field: record[key_field]},
                {"$set": record},
                upsert=True,
            )
    finally:
        client.close()
