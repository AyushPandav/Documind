import logging
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
from app.routers import documents, chat, fhe

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DocuMind.Gateway")

async def seed_initial_demo_corpus():
    """
    Seeds initial realistic documents so judges and devs can test immediately
    without having to manually upload files first.
    """
    existing_docs = await get_all_documents()
    if existing_docs:
        return

    logger.info("Database empty. Seeding realistic DocuMind demo corpus...")

    # Document 1: company_policy.pdf
    doc1_id = "doc-policy"
    doc1_name = "company_policy.pdf"
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

    for c in doc1_chunks:
        c["embedding"] = embedding_service.embed_text(c["content"])
    await save_chunks(doc1_chunks)

    # Document 2: employee_handbook.pdf
    doc2_id = "doc-handbook"
    doc2_name = "employee_handbook.pdf"
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

    for c in doc2_chunks:
        c["embedding"] = embedding_service.embed_text(c["content"])
    await save_chunks(doc2_chunks)

    logger.info("Initial demo corpus successfully seeded.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite tables & seed corpus
    await init_sqlite_db()
    await seed_initial_demo_corpus()
    logger.info(f"DocuMind Gateway online on port {settings.PORT}.")
    yield
    # Shutdown
    logger.info("DocuMind Gateway shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware (Allows React Native Expo, Web, and Emulators)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(fhe.router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "offline_ready": True,
        "fhe_enabled": True
    }
