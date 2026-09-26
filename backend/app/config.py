import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from pydantic_settings import BaseSettings
    class SettingsBase(BaseSettings):
        class Config:
            env_file = str(BASE_DIR / ".env")
            extra = "ignore"
except ImportError:
    from pydantic import BaseModel
    class SettingsBase(BaseModel):
        pass

class Settings(SettingsBase):
    PROJECT_NAME: str = "DocuMind FastAPI Gateway"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Offline & Local Storage
    SQLITE_DB_PATH: str = str(BASE_DIR / "app_cache.db")
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    
    # Cloud Storage (NeonDB PostgreSQL + pgvector)
    NEON_DATABASE_URL: str = os.getenv("NEON_DATABASE_URL", "")
    ENABLE_CLOUD_SYNC: bool = False
    
    # Cloud LLMs
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Embeddings & RAG
    EMBEDDING_DIM: int = 384
    CHUNK_SIZE: int = 450
    CHUNK_OVERLAP: int = 60
    
    # Fully Homomorphic Encryption (FHE) - CKKS parameters
    FHE_POLY_MODULUS_DEGREE: int = 8192
    FHE_GLOBAL_SCALE_EXPONENT: int = 40

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
