from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # API Configuration
    app_name: str = "Evolving Personal AI Assistant"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # API Keys
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    router_api_key: str = ""
    todoist_api_token: str = ""
    
    # Model Configuration (for reference - actual routing handled by Claude Code Router)
    max_tokens: int = 4096
    
    # Letta Configuration
    letta_api_key: str = ""
    letta_base_url: str = "https://api.letta.com"
    letta_agent_name: str = "evolving-assistant"
    
    # Workspace Configuration
    workspace_path: str = "./workspace"
    
    # Memory Database
    database_url: str = "sqlite+aiosqlite:///./data/memory.db"
    
    # Security
    secret_key: str = "change-me-in-production"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
