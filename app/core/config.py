from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Application configuration settings.
    """
    # Upstream llama.cpp server configuration
    UPSTREAM_BASE_URL: str = "http://127.0.0.1:8080"
    
    # Adapter configuration
    ENABLE_DEBUG_ENDPOINTS: bool = True
    LOG_NORMALIZED_REQUESTS: bool = True
    
    # API configuration
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "llamacpp-llm-adapter-api"

    # Pydantic Settings configuration
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

# Singleton instance
settings = Settings()
