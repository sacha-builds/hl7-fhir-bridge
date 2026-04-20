from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRIDGE_", env_file=".env", extra="ignore")

    http_port: int = 8000
    mllp_port: int = 2575
    log_level: str = "INFO"
    fhir_base_url: str = Field(default="http://localhost:8080/fhir")


settings = Settings()
