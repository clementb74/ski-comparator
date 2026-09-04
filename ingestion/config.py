"""Configuration centralisée pour les scripts d'ingestion (variables d'env)."""
from pydantic_settings import BaseSettings


class IngestionSettings(BaseSettings):
    mongodb_uri: str = ""
    meteo_france_api_key: str = ""

    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema: str = ""

    class Config:
        env_file = ".env"


settings = IngestionSettings()
