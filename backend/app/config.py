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
    ENABLE_CLOUD_SYNC: bool = os.getenv("ENABLE_CLOUD_SYNC", "False").lower() in ("true", "1", "yes")
    
    # Authentication & Security (JWT)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "documind_jwt_secret_2026_prod_fhe_rag_secure")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # PRIMARY LOCAL LLM: Ollama (Qwen 2.5 3B-Instruct)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    # FALLBACK-1: Groq API (High-speed cloud inference)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    # FALLBACK-2: Mistral API
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    
    # Embeddings & RAG
    EMBEDDING_DIM: int = 384
    CHUNK_SIZE: int = 450
    CHUNK_OVERLAP: int = 60
    
    # Fully Homomorphic Encryption (FHE) - CKKS parameters
    FHE_POLY_MODULUS_DEGREE: int = 8192
    FHE_GLOBAL_SCALE_EXPONENT: int = 40

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
