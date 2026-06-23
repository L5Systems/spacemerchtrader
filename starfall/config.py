from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./starfall.db"
    redis_url: str = "redis://localhost:6379"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    company_name: str = "Starfall Space Merchandise Handling Co."
    launch_broker_use_llm: bool = True
    launch_broker_llm_api_key: str | None = None
    launch_broker_llm_api_base: str = "https://api.openai.com/v1"
    launch_broker_llm_model: str = "gpt-4o-mini"


settings = Settings()
