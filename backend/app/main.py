import logging
import sys
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.sqlite_cache import (
    init_sqlite_db,
    get_all_documents,
    save_document,
    save_chunks
)
from app.rag.embeddings import embedding_service
from app.routers import documents, chat, fhe, auth, tts
from app.auth.neon_users import ensure_users_table

# Force UTF-8 output on Windows to prevent CP1252 UnicodeEncodeErrors
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ─── Logging Configuration ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                             if hasattr(sys.stdout, 'buffer') else sys.stdout)
    ]
)
logger = logging.getLogger("DocuMind.Gateway")


async def seed_initial_demo_corpus():
    """
    Seeds initial realistic documents so judges and devs can test immediately
    without having to manually upload files first.
    """
    existing_docs = await get_all_documents()
    if existing_docs:
        logger.info(f"[Seed] Database already has {len(existing_docs)} document(s) — skipping demo seed")
        return

    logger.info("[Seed] Database empty. Seeding DocuMind demo corpus with 2 realistic documents...")

    # ── Document 1: company_policy.pdf ───────────────────────────────────────
    doc1_id = "doc-policy"
    doc1_name = "company_policy.pdf"
    logger.info(f"[Seed] Seeding '{doc1_name}'...")
    await save_document(
        doc_id=doc1_id,
        name=doc1_name,
        path="",
        size="1.1 MB",
        pages=18,
        status="INDEXED",
        progress=100
    )

    doc1_chunks = [
        {
            "id": f"{doc1_id}-c1",
            "doc_id": doc1_id,
            "doc_name": doc1_name,
            "page_number": 12,
            "chunk_index": 1,
            "content": "Refund requests must be submitted within 30 days of initial purchase. All requests require proof of payment and are issued to the original payment method within 5-7 business days."
        },
        {
            "id": f"{doc1_id}-c2",
            "doc_id": doc1_id,
            "doc_name": doc1_name,
            "page_number": 14,
            "chunk_index": 2,
            "content": "Enterprise software configurations, dedicated instance provisioning fees, and custom development packages are strictly non-refundable once the onboarding period commences."
        },
        {
            "id": f"{doc1_id}-c3",
            "doc_id": doc1_id,
            "doc_name": doc1_name,
            "page_number": 7,
            "chunk_index": 3,
            "content": "API keys, service account credentials, and master database connection strings must be rotated every 90 days or immediately following staff role alterations."
        }
    ]

    logger.info(f"[Seed] Embedding {len(doc1_chunks)} chunks for '{doc1_name}'...")
    for c in doc1_chunks:
        c["embedding"] = embedding_service.embed_text(c["content"])
    await save_chunks(doc1_chunks)
    logger.info(f"[Seed] ✓ '{doc1_name}' seeded ({len(doc1_chunks)} chunks)")

    # ── Document 2: employee_handbook.pdf ────────────────────────────────────
    doc2_id = "doc-handbook"
    doc2_name = "employee_handbook.pdf"
    logger.info(f"[Seed] Seeding '{doc2_name}'...")
    await save_document(
        doc_id=doc2_id,
        name=doc2_name,
        path="",
        size="2.4 MB",
        pages=42,
        status="INDEXED",
        progress=100
    )

    doc2_chunks = [
        {
            "id": f"{doc2_id}-c1",
            "doc_id": doc2_id,
            "doc_name": doc2_name,
            "page_number": 8,
            "chunk_index": 1,
            "content": "Full-time team members accrue standard annual paid leave at a rate of 2.0 days per calendar month, totaling 24 days per fiscal year."
        },
        {
            "id": f"{doc2_id}-c2",
            "doc_id": doc2_id,
            "doc_name": doc2_name,
            "page_number": 9,
            "chunk_index": 2,
            "content": "Planned vacation time exceeding 3 consecutive business days must be logged via the DocuMind People Portal at least 14 days prior to commencement."
        },
        {
            "id": f"{doc2_id}-c3",
            "doc_id": doc2_id,
            "doc_name": doc2_name,
            "page_number": 22,
            "chunk_index": 3,
            "content": "All workstation endpoints and cloud services require hardware-backed or authenticator app multi-factor verification. SMS verification is explicitly prohibited."
        },
        {
            "id": f"{doc2_id}-c4",
            "doc_id": doc2_id,
            "doc_name": doc2_name,
            "page_number": 25,
            "chunk_index": 4,
            "content": "Engineering and operations personnel must preserve deployment logs and participate in bi-annual SOC2 Type II compliance audits without exception."
        }
    ]

    logger.info(f"[Seed] Embedding {len(doc2_chunks)} chunks for '{doc2_name}'...")
    for c in doc2_chunks:
        c["embedding"] = embedding_service.embed_text(c["content"])
    await save_chunks(doc2_chunks)
    logger.info(f"[Seed] ✓ '{doc2_name}' seeded ({len(doc2_chunks)} chunks)")

    logger.info("[Seed] >> Demo corpus seeded successfully (2 documents, 7 total chunks)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info("═" * 65)
    logger.info(f"  DocuMind Gateway — v{settings.VERSION}")
    logger.info(f"  FastAPI Backend: Production-Grade RAG + FHE Engine")
    logger.info("═" * 65)
    logger.info(f"[Startup] Initializing SQLite database at: {settings.SQLITE_DB_PATH}")
    await init_sqlite_db()
    logger.info(f"[Startup] ✓ SQLite schema initialized (5 tables)")

    logger.info(f"[Startup] Seeding demo corpus if needed...")
    await seed_initial_demo_corpus()

    logger.info(f"[Startup] Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"[Startup] Embedding model: {'SentenceTransformer all-MiniLM-L6-v2' if embedding_service._model else 'Deterministic Projection (384d)'}")
    logger.info(f"[Startup] Cloud sync: {'Enabled → NeonDB' if settings.ENABLE_CLOUD_SYNC else 'Disabled'}")
    
    # ── Initialize Auth Schema (NeonDB PostgreSQL + Local SQLite fallback) ────
    logger.info(f"[Startup] Initializing Authentication layer...")
    neon_auth_ok = await ensure_users_table()
    auth_provider_str = "NeonDB Serverless PostgreSQL ✓" if neon_auth_ok else "Local SQLite (Offline fallback)"
    logger.info(f"[Startup] Auth provider: {auth_provider_str}")

    logger.info(f"[Startup] LLM Primary: Ollama ({settings.OLLAMA_MODEL}) at {settings.OLLAMA_BASE_URL}")
    logger.info(f"[Startup] LLM Fallback-1: Groq ({settings.GROQ_MODEL}) ✓")
    logger.info(f"[Startup] LLM Fallback-2: Mistral ({settings.MISTRAL_MODEL}) ✓")
    logger.info("═" * 65)
    logger.info(f"[Startup] ✅ DocuMind Gateway ONLINE — http://{settings.HOST}:{settings.PORT}")
    logger.info(f"[Startup]    API Docs: http://localhost:{settings.PORT}/docs")
    logger.info(f"[Startup]    ReDoc:    http://localhost:{settings.PORT}/redoc")
    logger.info("═" * 65)

    yield

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("═" * 65)
    logger.info("[Shutdown] DocuMind Gateway shutting down gracefully...")
    logger.info("═" * 65)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "DocuMind: Production-Grade FastAPI backend featuring Multi-Pipeline Document Ingestion, "
        "Self-Reflective Corrective RAG Loop, Hybrid BM25 + Dense Vector Retrieval, "
        "Fully Homomorphic Encryption (CKKS), Dual LLM Circuit Breaker, "
        "JWT Authentication backed by NeonDB Serverless PostgreSQL, "
        "and Offline-First SQLite + NeonDB Cloud Sync."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ─── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(fhe.router)
app.include_router(tts.router)


@app.get("/health", tags=["System"])
async def health_check():
    """System health check — returns service status, capabilities, and config."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "features": {
            "authentication_jwt": True,
            "multi_pipeline_ingestion": True,
            "hybrid_rag_retrieval": True,
            "self_reflective_loop": True,
            "fhe_zero_knowledge_search": True,
            "offline_ready": True,
            "multi_file_upload": True,
            "document_relatedness_analysis": True,
        },
        "auth": {
            "enabled": True,
            "provider": "NeonDB Serverless PostgreSQL" if settings.NEON_DATABASE_URL else "SQLite Local",
            "token_type": "Bearer JWT",
            "expiry_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES
        },
        "llm_config": {
            "primary": f"Ollama ({settings.OLLAMA_MODEL})",
            "fallback_1": f"Groq ({settings.GROQ_MODEL})",
            "fallback_2": f"Mistral ({settings.MISTRAL_MODEL})",
            "offline": "Deterministic Heuristic Synthesizer",
        },
        "embedding": {
            "model": "all-MiniLM-L6-v2" if embedding_service._model else "Deterministic Projection",
            "dimension": settings.EMBEDDING_DIM
        },
        "cloud_sync": settings.ENABLE_CLOUD_SYNC,
    }
