from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str
    admin_email: str
    admin_password: str
    piston_url: str = "http://localhost:2000"
    database_url: str = "sqlite:///./app.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
