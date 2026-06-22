from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./starfall.db"
    redis_url: str = "redis://localhost:6379"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    company_name: str = "Starfall Space Merchandise Handling Co."


settings = Settings()
