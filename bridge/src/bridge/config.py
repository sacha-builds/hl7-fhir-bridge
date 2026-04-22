from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRIDGE_", env_file=".env", extra="ignore")

    http_port: int = 8000
    mllp_port: int = 2575
    log_level: str = "INFO"
    fhir_base_url: str = Field(default="http://localhost:8080/fhir")

    # OAuth2 client-credentials — set all three for Medplum / authenticated FHIR servers.
    fhir_oauth_token_url: str | None = None
    fhir_oauth_client_id: str | None = None
    fhir_oauth_client_secret: str | None = None

    # Demo seeder — when > 0, the bridge process replays a random fixture
    # every N minutes to keep the deployed showcase inbox populated.
    demo_replay_interval_minutes: int = 0
    demo_fixtures_path: str = "/app/fixtures/messages"


settings = Settings()
