from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    admin_secret_key: str = "changeme"
    database_url: str = "sqlite:///./data/ai_basic_law.db"
    law_pdf_path: str = "./data/ai_basic_law.pdf"
    font_dir: str = "./data/fonts"
    rate_limit_max_requests: int = 5
    rate_limit_window_seconds: int = 600
    allowed_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
