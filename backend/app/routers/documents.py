import os
import uuid
import time
import base64
import asyncio
import aiofiles
import logging
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
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
from app.rag.document_analyzer import analyze_uploaded_batch
from app.db.neondb import neon_db

router = APIRouter(prefix="/api/documents", tags=["Documents"])
logger = logging.getLogger("DocuMind.DocumentsRouter")

# ── Allowed upload file types ─────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".heic",
    ".txt", ".md", ".json", ".csv", ".tsv"
}
MAX_FILE_SIZE_MB = 100


async def process_and_index_document(doc_id: str, file_path: str, file_name: str):
    """
    Asynchronous 5-Stage Document Ingestion Pipeline with Full Terminal Logging:

    Stage 1  [35%]  — Multi-Pipeline Parsing (PyMuPDF / pdfplumber / OpenCV+OCR)
    Stage 2  [60%]  — Recursive Structural Chunking (paragraph/sentence/overlap)
    Stage 3  [80%]  — Dense Vector Embedding  (SentenceTransformers / deterministic fallback)
    Stage 4  [95%]  — SQLite Storage & Local Index
    Stage 5  [100%] — NeonDB Cloud Sync (if enabled)
    """
    t_start = time.monotonic()

    logger.info("━" * 65)
    logger.info(f"[INGESTION] ▶ Starting pipeline for: {file_name} (ID: {doc_id})")
    logger.info("━" * 65)

    try:
        # ──────────────────────────────────────────────────────────────────────
        # Stage 1: Multi-Pipeline Document Parsing + OCR
        # ──────────────────────────────────────────────────────────────────────
        logger.info(f"[Stage 1/5] ⚙ Document Parsing & OCR  →  {file_name}")
        await update_document_status(doc_id, "OCR", progress=15)

        t1 = time.monotonic()
        pages_data = process_document(file_path, file_name)
        pages_count = max(1, len(pages_data))
        total_chars = sum(len(p.get("content", "")) for p in pages_data)

        await update_document_status(doc_id, "OCR", progress=35)
        t1_elapsed = time.monotonic() - t1
        logger.info(
            f"[Stage 1/5] ✓ Parsing DONE: {pages_count} page(s), "
            f"{total_chars:,} total chars extracted in {t1_elapsed:.2f}s"
        )

        # ──────────────────────────────────────────────────────────────────────
        # Stage 2: Recursive Structural Chunking
        # ──────────────────────────────────────────────────────────────────────
        logger.info(f"[Stage 2/5] ⚙ Recursive Chunker  →  chunk_size={settings.CHUNK_SIZE}, overlap={settings.CHUNK_OVERLAP}")
        await update_document_status(doc_id, "PROCESSING", progress=50)

        t2 = time.monotonic()
        chunks = chunk_document_pages(doc_id, file_name, pages_data)
        t2_elapsed = time.monotonic() - t2

        await update_document_status(doc_id, "PROCESSING", progress=60)
        logger.info(
            f"[Stage 2/5] ✓ Chunking DONE: {len(chunks)} chunks created in {t2_elapsed:.2f}s "
            f"(avg {total_chars // max(1, len(chunks))} chars/chunk)"
        )

        # ──────────────────────────────────────────────────────────────────────
        # Stage 3: Dense Vector Embedding
        # ──────────────────────────────────────────────────────────────────────
        logger.info(f"[Stage 3/5] ⚙ Dense Vector Embedding  →  dim={settings.EMBEDDING_DIM}")
        await update_document_status(doc_id, "EMBEDDING", progress=70)

        t3 = time.monotonic()
        model_type = "SentenceTransformer" if embedding_service._model else "Deterministic Projection"
        for idx, c in enumerate(chunks):
            c["embedding"] = embedding_service.embed_text(c["content"])
            if (idx + 1) % max(1, len(chunks) // 4) == 0 or (idx + 1) == len(chunks):
                logger.info(
                    f"[Stage 3/5]   Embedded {idx + 1}/{len(chunks)} chunks ({model_type})..."
                )
        t3_elapsed = time.monotonic() - t3

        await update_document_status(doc_id, "EMBEDDING", progress=80)
        logger.info(
            f"[Stage 3/5] ✓ Embedding DONE: {len(chunks)} vectors ({settings.EMBEDDING_DIM}d) "
            f"via {model_type} in {t3_elapsed:.2f}s"
        )

        # ──────────────────────────────────────────────────────────────────────
        # Stage 4: SQLite Storage & Index
        # ──────────────────────────────────────────────────────────────────────
        logger.info(f"[Stage 4/5] ⚙ SQLite Storage & Index  →  {settings.SQLITE_DB_PATH}")
        await update_document_status(doc_id, "INDEXING", progress=85)

        t4 = time.monotonic()
        await save_chunks(chunks)
        file_size_mb = (
            f"{max(0.1, round(os.path.getsize(file_path) / (1024 * 1024), 1))} MB"
            if os.path.exists(file_path) else "1.2 MB"
        )
        doc_meta = pages_data[0].get("metadata", {}) if pages_data else {}
        await save_document(
            doc_id=doc_id,
            name=file_name,
            path=file_path,
            size=file_size_mb,
            pages=pages_count,
            status="INDEXED",
            progress=100,
            doc_metadata=doc_meta
        )
        t4_elapsed = time.monotonic() - t4

        logger.info(
            f"[Stage 4/5] ✓ SQLite DONE: {len(chunks)} chunks persisted in {t4_elapsed:.2f}s"
        )

        # ──────────────────────────────────────────────────────────────────────
        # Stage 5: Cloud Sync to NeonDB (if configured)
        # ──────────────────────────────────────────────────────────────────────
        if settings.ENABLE_CLOUD_SYNC and settings.NEON_DATABASE_URL:
            logger.info(f"[Stage 5/5] ⚙ NeonDB Cloud Sync  →  {len(chunks)} chunks")
            t5 = time.monotonic()
            sync_result = await neon_db.sync_chunks_to_cloud(chunks)
            t5_elapsed = time.monotonic() - t5
            if sync_result.get("synced"):
                logger.info(
                    f"[Stage 5/5] ✓ NeonDB Sync DONE: {sync_result.get('synced_count', 0)} chunks "
                    f"synced in {t5_elapsed:.2f}s"
                )
            else:
                logger.warning(f"[Stage 5/5] ⚠ NeonDB Sync SKIPPED: {sync_result.get('reason') or sync_result.get('error')}")
        else:
            logger.info(f"[Stage 5/5] ⏭ NeonDB Cloud Sync DISABLED (set ENABLE_CLOUD_SYNC=True to enable)")

        total_elapsed = time.monotonic() - t_start
        logger.info("━" * 65)
        logger.info(
            f"[INGESTION] ✅ COMPLETE: {file_name} — "
            f"{len(chunks)} chunks, {pages_count} pages, {file_size_mb} in {total_elapsed:.2f}s total"
        )
        logger.info("━" * 65)

    except Exception as e:
        total_elapsed = time.monotonic() - t_start
        logger.error("━" * 65)
        logger.error(f"[INGESTION] ✗ FAILED: {file_name} after {total_elapsed:.2f}s")
        logger.error(f"[INGESTION] Error: {e}", exc_info=True)
        logger.error("━" * 65)
        await update_document_status(doc_id, "FAILED", progress=0)


# ─────────────────────────────────────────────────────────────────────────────
# Single File Upload
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Single-file upload endpoint.
    Accepts: PDF, PNG, JPG, JPEG, BMP, TIFF, WEBP, TXT, MD, CSV, TSV.
    Schedules asynchronous multi-pipeline ingestion (Digital / Table / OCR).
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    file_size_mb_val = len(content) / (1024 * 1024)
    if file_size_mb_val > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit.")

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    file_name = file.filename or f"doc_{doc_id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{file_name}")
    file_size_str = f"{max(0.1, round(file_size_mb_val, 1))} MB"

    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(content)

    logger.info(f"[Upload] Received: '{file_name}' ({file_size_str}) → queued as {doc_id}")

    await save_document(
        doc_id=doc_id,
        name=file_name,
        path=file_path,
        size=file_size_str,
        pages=1,
        status="QUEUED",
        progress=5
    )

    background_tasks.add_task(process_and_index_document, doc_id, file_path, file_name)

    return {
        "id": doc_id,
        "name": file_name,
        "size": file_size_str,
        "status": "QUEUED",
        "progress": 5,
        "message": f"'{file_name}' queued for multi-pipeline processing (ID: {doc_id})."
    }


# ─────────────────────────────────────────────────────────────────────────────
# Guaranteed Base64 Single File Upload (Mobile & Universal Fail-safe)
# ─────────────────────────────────────────────────────────────────────────────
class Base64UploadRequest(BaseModel):
    filename: str
    file_base64: str
    mime_type: Optional[str] = "application/octet-stream"

@router.post("/upload-base64")
async def upload_base64_document(
    request: Base64UploadRequest,
    background_tasks: BackgroundTasks
):
    """
    JSON Base64 upload endpoint.
    Eliminates all native mobile multipart boundary and WinterCG fetch errors.
    Decodes the raw bytes, stores to upload directory, and triggers the 5-stage ingestion pipeline.
    """
    file_name = request.filename or "uploaded_document.pdf"
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    try:
        raw_bytes = base64.b64decode(request.file_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {e}")

    file_size_mb_val = len(raw_bytes) / (1024 * 1024)
    if file_size_mb_val > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit.")

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{file_name}")
    file_size_str = f"{max(0.1, round(file_size_mb_val, 1))} MB"

    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(raw_bytes)

    logger.info(f"[UploadBase64] Received: '{file_name}' ({file_size_str}) → queued as {doc_id}")

    await save_document(
        doc_id=doc_id,
        name=file_name,
        path=file_path,
        size=file_size_str,
        pages=1,
        status="QUEUED",
        progress=5
    )

    background_tasks.add_task(process_and_index_document, doc_id, file_path, file_name)

    return {
        "id": doc_id,
        "name": file_name,
        "size": file_size_str,
        "status": "QUEUED",
        "progress": 5,
        "message": f"'{file_name}' queued for multi-pipeline processing (ID: {doc_id})."
    }


# ─────────────────────────────────────────────────────────────────────────────
# Multi-File Batch Upload
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/upload-batch")
async def upload_batch_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Multi-file batch upload endpoint.
    Accepts up to 10 files simultaneously.
    Returns per-file ingestion tokens and a batch analysis summary.

    After all files are queued, automatically runs cross-document relatedness
    analysis using TF-IDF keyword fingerprinting and Jaccard similarity scoring.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch upload.")

    logger.info("━" * 65)
    logger.info(f"[BatchUpload] ▶ Received batch of {len(files)} file(s)")
    logger.info("━" * 65)

    queued_docs = []
    rejected_files = []

    for idx, file in enumerate(files):
        file_name = file.filename or f"batch_doc_{idx + 1}"
        ext = os.path.splitext(file_name)[1].lower()

        logger.info(f"[BatchUpload] Processing file {idx + 1}/{len(files)}: '{file_name}'")

        if ext not in ALLOWED_EXTENSIONS:
            logger.warning(f"[BatchUpload]   ✗ Rejected: unsupported type '{ext}'")
            rejected_files.append({
                "name": file_name,
                "reason": f"Unsupported file type '{ext}'"
            })
            continue

        try:
            content = await file.read()
            file_size_mb_val = len(content) / (1024 * 1024)

            if file_size_mb_val > MAX_FILE_SIZE_MB:
                logger.warning(f"[BatchUpload]   ✗ Rejected: file too large ({file_size_mb_val:.1f} MB > {MAX_FILE_SIZE_MB} MB)")
                rejected_files.append({
                    "name": file_name,
                    "reason": f"File too large ({file_size_mb_val:.1f} MB, limit: {MAX_FILE_SIZE_MB} MB)"
                })
                continue

            doc_id = f"doc-{uuid.uuid4().hex[:8]}"
            file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{file_name}")
            file_size_str = f"{max(0.1, round(file_size_mb_val, 1))} MB"

            async with aiofiles.open(file_path, "wb") as out_file:
                await out_file.write(content)

            await save_document(
                doc_id=doc_id,
                name=file_name,
                path=file_path,
                size=file_size_str,
                pages=1,
                status="QUEUED",
                progress=5
            )

            background_tasks.add_task(process_and_index_document, doc_id, file_path, file_name)

            queued_docs.append({
                "id": doc_id,
                "name": file_name,
                "size": file_size_str,
                "status": "QUEUED",
                "progress": 5
            })
            logger.info(f"[BatchUpload]   ✓ Queued: '{file_name}' → {doc_id} ({file_size_str})")

        except Exception as e:
            logger.error(f"[BatchUpload]   ✗ Error saving '{file_name}': {e}")
            rejected_files.append({"name": file_name, "reason": str(e)})

    logger.info(
        f"[BatchUpload] Summary: {len(queued_docs)} queued, {len(rejected_files)} rejected"
    )
    logger.info("━" * 65)

    return {
        "batch_size": len(files),
        "queued_count": len(queued_docs),
        "rejected_count": len(rejected_files),
        "queued_documents": queued_docs,
        "rejected_files": rejected_files,
        "message": (
            f"Batch of {len(queued_docs)} document(s) queued for processing. "
            f"Use GET /api/documents/status to track progress. "
            f"Use POST /api/documents/analyze to run relatedness analysis once indexed."
        )
    }


# ─────────────────────────────────────────────────────────────────────────────
# Document Relatedness & Summary Analysis
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/analyze")
async def analyze_documents(body: Optional[Dict[str, Any]] = None):
    """
    Cross-Document Analysis Endpoint:
    Analyzes all indexed documents (or a provided subset by doc_ids) for:
    - Per-document 2–3 sentence AI summaries
    - TF-IDF keyword fingerprints
    - Pairwise Jaccard similarity scores
    - Overall relatedness verdict (Highly Related / Partially Related / Unrelated)
    - Shared themes across all documents
    - Actionable recommendation

    Logs all analysis steps to terminal.
    """
    doc_ids: Optional[List[str]] = None
    if body and "doc_ids" in body:
        doc_ids = body["doc_ids"]

    logger.info("[DocumentAnalysis] ▶ Analysis endpoint called")

    if doc_ids:
        logger.info(f"[DocumentAnalysis] Analyzing specific docs: {doc_ids}")
        target_ids = doc_ids
    else:
        all_docs = await get_all_documents()
        indexed_docs = [d for d in all_docs if d.get("status") == "INDEXED"]
        target_ids = [d["id"] for d in indexed_docs]
        logger.info(f"[DocumentAnalysis] Analyzing all indexed docs: {len(target_ids)} document(s)")

    if not target_ids:
        return {
            "error": "No indexed documents available for analysis. Upload and index documents first.",
            "doc_summaries": {},
            "is_related": False,
            "relationship_label": "N/A"
        }

    async def _get_chunks(doc_id: str):
        return await get_all_chunks(doc_id=doc_id)

    async def _get_doc(doc_id: str):
        return await get_document(doc_id)

    result = await analyze_uploaded_batch(target_ids, _get_chunks, _get_doc)
    return result


@router.get("/analyze/{doc_id}/summary")
async def get_single_document_summary(doc_id: str):
    """Returns a generated summary for a specific document."""
    from app.rag.document_analyzer import generate_document_summary

    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = await get_all_chunks(doc_id=doc_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="No indexed chunks found for this document.")

    summary = generate_document_summary(doc["name"], chunks)
    return {
        "doc_id": doc_id,
        "name": doc["name"],
        "pages": doc.get("pages", 1),
        "chunk_count": len(chunks),
        "summary": summary
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standard Status / CRUD Endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/status")
async def get_all_document_statuses():
    """Returns indexing and processing progress for all documents."""
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
    return await get_all_documents()

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

    if doc.get("path") and os.path.exists(doc["path"]):
        try:
            os.remove(doc["path"])
            logger.info(f"[Delete] Physical file removed: {doc['path']}")
        except Exception as e:
            logger.warning(f"[Delete] Could not remove physical file: {e}")

    await delete_document_and_chunks(doc_id)
    logger.info(f"[Delete] Document '{doc['name']}' (ID: {doc_id}) removed from SQLite")
    return {"status": "deleted", "id": doc_id, "message": f"Document '{doc['name']}' removed."}

@router.post("/sync")
async def sync_documents_to_cloud(background_tasks: BackgroundTasks):
    """Triggers synchronization of all local chunks to NeonDB serverless PostgreSQL."""
    chunks = await get_all_chunks()
    logger.info(f"[CloudSync] Manual sync triggered: {len(chunks)} total chunks")
    result = await neon_db.sync_chunks_to_cloud(chunks)
    return result

@router.get("/sync/status")
async def get_cloud_sync_status():
    """Returns NeonDB PostgreSQL connection and sync status."""
    return neon_db.get_sync_status()


# ─────────────────────────────────────────────────────────────────────────────
# Multimodal Visual Search & Forensics
# ─────────────────────────────────────────────────────────────────────────────
class VisualSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 4
    doc_filter: Optional[str] = None


@router.post("/visual-search")
async def visual_clip_search(request: VisualSearchRequest):
    """
    Multimodal Zero-Shot Visual Search via CLIP ViT-B/32:
    Directly searches document pages and scanned images for visual semantics
    (e.g., 'pie chart', 'invoices with red stamps', 'architectural diagram', 'handwritten notes')
    without requiring OCR text extraction.
    """
    from app.rag.clip_embeddings import clip_service

    all_chunks = await get_all_chunks()
    if request.doc_filter:
        all_chunks = [
            c for c in all_chunks
            if c.get("doc_name") == request.doc_filter
            or c.get("doc_id") == request.doc_filter
            or request.doc_filter.lower() in c.get("doc_name", "").lower()
        ]

    visual_chunks = [c for c in all_chunks if c.get("clip_embedding")]
    if not visual_chunks:
        return {
            "query": request.query,
            "total_visual_pages": 0,
            "results": [],
            "message": "No visual CLIP embeddings found in the indexed corpus. Upload scanned PDFs or images to enable visual search."
        }

    query_vec = clip_service.embed_text(request.query)
    scored = []
    for c in visual_chunks:
        score = clip_service.compute_similarity(query_vec, c["clip_embedding"])
        meta = c.get("metadata", {})
        scored.append({
            "chunk_id": c["id"],
            "doc_id": c["doc_id"],
            "doc_name": c["doc_name"],
            "page_number": c["page_number"],
            "visual_similarity_score": round(score, 4),
            "category": meta.get("category", "image"),
            "classification_confidence": meta.get("classification_confidence", 0.0),
            "pii_redacted": meta.get("pii_redacted", False),
            "faces_detected": meta.get("faces_detected", 0),
            "dpi": meta.get("dpi", 72),
            "scanner_make": meta.get("scanner_make"),
            "content_preview": c["content"][:240].strip() + "..."
        })

    scored.sort(key=lambda x: x["visual_similarity_score"], reverse=True)
    top_results = scored[:request.top_k]

    return {
        "query": request.query,
        "total_visual_pages": len(visual_chunks),
        "results_count": len(top_results),
        "results": top_results
    }


@router.get("/{doc_id}/forensics")
async def get_document_forensics(doc_id: str):
    """
    Returns digital forensic metadata, EXIF hardware parameters,
    content-aware category, and PII face redaction logs for an uploaded document.
    """
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    meta = doc.get("metadata", {})
    return {
        "doc_id": doc["id"],
        "name": doc["name"],
        "status": doc["status"],
        "pages": doc["pages"],
        "size": doc["size"],
        "forensic_metadata": meta
    }

