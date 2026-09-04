"""Configuration de l'API (variables d'environnement Snowflake, etc.)."""
from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema: str = ""

    class Config:
        env_file = ".env"


settings = APISettings()
