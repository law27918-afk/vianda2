from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://vianda:vianda@db:5432/vianda"
    csv_path: str = "/app/data/supermercados_unificado.csv"

    class Config:
        env_file = ".env"


settings = Settings()
