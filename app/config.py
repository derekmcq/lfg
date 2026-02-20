from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    IGDB_CLIENT_ID: str
    IGDB_CLIENT_SECRET: str

    class Config:
        env_file = ".env"


settings = Settings()
