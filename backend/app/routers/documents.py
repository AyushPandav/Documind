import os
import uuid
import aiofiles
import logging
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from typing import List, Dict, Any, Optional
from app.config import settings
from app.db.sqlite_cache import (
    save_document,
    update_document_status,
    get_all_documents,
    get_document,
    delete_document_and_chunks,
    save_chunks,
    get_all_chunks
)
from app.pipelines.router import process_document
from app.rag.chunker import chunk_document_pages
from app.rag.embeddings import embedding_service
from app.db.neondb import neon_db

router = APIRouter(prefix="/api/documents", tags=["Documents"])
logger = logging.getLogger("DocuMind.DocumentsRouter")

async def process_and_index_document(doc_id: str, file_path: str, file_name: str):
    """
    Asynchronous 4-stage document ingestion pipeline:
    1. Parsing / OpenCV Cleanup / RapidOCR (35% progress)
    2. Structural Chunking (70% progress)
    3. Dense Vector Embeddings (90% progress)
    4. SQLite & NeonDB Cloud Indexing (100% progress)
    """
    try:
        # Stage 1: Parsing & OCR Phase
        await update_document_status(doc_id, "OCR", progress=35)
        pages_data = process_document(file_path, file_name)
        pages_count = max(1, len(pages_data))

        # Stage 2: Structural Chunking Phase
        await update_document_status(doc_id, "PROCESSING", progress=70)
        chunks = chunk_document_pages(doc_id, file_name, pages_data)

        # Stage 3: Vector Embeddings
        await update_document_status(doc_id, "EMBEDDING", progress=85)
        for c in chunks:
            c["embedding"] = embedding_service.embed_text(c["content"])

        # Stage 4: Storage & Indexing Phase
        await save_chunks(chunks)
        await save_document(
            doc_id=doc_id,
            name=file_name,
            path=file_path,
            size=f"{max(0.1, round(os.path.getsize(file_path)/(1024*1024), 1))} MB" if os.path.exists(file_path) else "1.2 MB",
            pages=pages_count,
            status="INDEXED",
            progress=100
        )

        # Stage 5: Cloud Sync to NeonDB pgvector if enabled
        if settings.ENABLE_CLOUD_SYNC:
            await neon_db.sync_chunks_to_cloud(chunks)

        logger.info(f"Document {file_name} successfully indexed ({len(chunks)} chunks, {pages_count} pages).")
    except Exception as e:
        logger.error(f"Error during document indexing for {file_name}: {e}")
        await update_document_status(doc_id, "FAILED", progress=0)

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Uploads a document (PDF, PNG, JPG, CSV, TXT), schedules the asynchronous
    multi-pipeline processing (Digital PyMuPDF + pdfplumber Tables + OpenCV Denoise/Deskew + RapidOCR).
    """
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    file_name = file.filename or f"doc_{doc_id}.pdf"
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{file_name}")

    # Save to disk
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    file_size_mb = f"{max(0.1, round(len(content)/(1024*1024), 1))} MB"

    # Save initial QUEUED state
    await save_document(
        doc_id=doc_id,
        name=file_name,
        path=file_path,
        size=file_size_mb,
        pages=1,
        status="QUEUED",
        progress=15
    )

    # Dispatch to background task
    background_tasks.add_task(process_and_index_document, doc_id, file_path, file_name)

    return {
        "id": doc_id,
        "name": file_name,
        "size": file_size_mb,
        "status": "QUEUED",
        "progress": 15,
        "message": "Document queued for multi-pipeline processing."
    }

@router.get("/status")
async def get_all_document_statuses():
    """
    Returns indexing and processing progress for all documents.
    Directly satisfies architectural roadmap: /api/documents/status
    """
    docs = await get_all_documents()
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "status": d["status"],
            "progress": d["progress"],
            "pages": d["pages"],
            "size": d["size"]
        }
        for d in docs
    ]

@router.get("/{doc_id}/status")
async def get_single_document_status(doc_id: str):
    """Returns indexing progress and status for a specific document."""
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "id": doc["id"],
        "name": doc["name"],
        "status": doc["status"],
        "progress": doc["progress"],
        "pages": doc["pages"]
    }

@router.get("")
async def list_documents():
    """Returns all registered documents and metadata."""
    docs = await get_all_documents()
    return docs

@router.get("/{doc_id}")
async def get_document_details(doc_id: str):
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Deletes a document and its corresponding vector chunks."""
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove physical file if present
    if doc.get("path") and os.path.exists(doc["path"]):
        try:
            os.remove(doc["path"])
        except Exception as e:
            logger.warning(f"Could not remove physical file: {e}")

    await delete_document_and_chunks(doc_id)
    return {"status": "deleted", "id": doc_id, "message": f"Document {doc['name']} removed."}

@router.post("/sync")
async def sync_documents_to_cloud(background_tasks: BackgroundTasks):
    """Triggers synchronization of all local chunks to NeonDB serverless PostgreSQL."""
    chunks = await get_all_chunks()
    result = await neon_db.sync_chunks_to_cloud(chunks)
    return result

@router.get("/sync/status")
async def get_cloud_sync_status():
    """Returns NeonDB PostgreSQL connection and sync status."""
    return neon_db.get_sync_status()
