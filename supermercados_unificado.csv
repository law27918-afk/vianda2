from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://vianda:vianda@db:5432/vianda"
    csv_path: str = "/app/data/supermercados_unificado.csv"

    class Config:
        env_file = ".env"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        # Railway/Heroku entregan postgres:// o postgresql:// sin el driver psycopg2
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+psycopg2://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v


settings = Settings()
