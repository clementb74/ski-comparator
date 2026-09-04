"""Configuration centralisée pour les scripts d'ingestion (variables d'env)."""
from pydantic_settings import BaseSettings


class IngestionSettings(BaseSettings):
    mongodb_uri: str = ""
    meteo_france_api_key: str = ""

    class Config:
        env_file = ".env"


settings = IngestionSettings()
