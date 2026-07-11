import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Adaptive Academic Scheduling Platform"
    
    # DB Config
    # If DATABASE_URL is set, use it (e.g. postgresql://...), otherwise default to sqlite
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./timetable.db")
    
    # Security/JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_token_for_hackathon_scheduling_platform_12345")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours for easy demo sessions
    
    # Config allowed origins
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ] + ([o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()] if os.getenv("ALLOWED_ORIGINS") else [])
    
    # Setup
    DEFAULT_ADMIN_USER: str = "admin@timetable.edu"
    DEFAULT_ADMIN_PASS: str = "Admin@12345"

    class Config:
        case_sensitive = True

    def __init__(self, **values):
        super().__init__(**values)
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)

settings = Settings()
