import os
import cv2
import numpy as np
import mimetypes
import logging
import pymupdf
from typing import List, Dict, Any

from app.pipelines.pdf_extractor import extract_text_pymupdf
from app.pipelines.table_extractor import extract_tables_as_markdown
from app.pipelines.ocr_pipeline import run_ocr
from app.pipelines.word_extractor import (
    extract_docx,
    extract_pptx,
    extract_excel,
    extract_json_file
)
from app.pipelines.exif_extractor import extract_file_metadata
from app.pipelines.face_redactor import redact_faces_in_image
from app.pipelines.image_classifier import classify_document_page, classify_pdf_first_page
from app.rag.clip_embeddings import clip_service

logger = logging.getLogger("DocuMind.PipelineRouter")


def process_document(file_path: str, file_name: str) -> List[Dict[str, Any]]:
    """
    [PIPELINE ROUTER] Multimodal Content-Aware Vision & Document Router:

    1. EXIF & Forensics Extraction: DPI, scanner model, scan date, creation info.
    2. PII Face Redaction: Detects human faces on scanned IDs/resumes/forms and blurs them.
    3. Document Image Classifier: Detects chart, table, stamped invoice, ID card, or handwritten note.
    4. Multimodal CLIP Embeddings: Generates 512-dim visual embeddings for zero-shot visual retrieval.
    5. Structural & OCR Ingestion: High-throughput parsing based on classified page modality.

    Returns structured pages with text content, CLIP vectors, and forensic metadata.
    """
    ext = os.path.splitext(file_name)[1].lower()
    pages: List[Dict[str, Any]] = []
    file_size_kb = round(os.path.getsize(file_path) / 1024, 1) if os.path.exists(file_path) else 0

    # ── Step 0: Extract Digital Forensics & EXIF Metadata ────────────────────
    forensic_metadata = extract_file_metadata(file_path)
    logger.info("=" * 65)
    logger.info(f"[PIPELINE ROUTER] Document: {file_name} ({file_size_kb} KB)")
    logger.info(
        f"[PIPELINE ROUTER] Forensics: Format={forensic_metadata.get('format', ext.upper())} | "
        f"DPI={forensic_metadata.get('dpi', 72)} | Scanner={forensic_metadata.get('scanner_make') or 'N/A'}"
    )
    logger.info("=" * 65)

    if ext == ".pdf":
        logger.info("[PIPELINE ROUTER] → Route A: Digital PDF + Multimodal Vision Pipeline")

        # ── Step 1: Content-Aware First Page Classification ──────────────────
        pdf_classification = classify_pdf_first_page(file_path)
        logger.info(
            f"[PIPELINE ROUTER] PDF Category: '{pdf_classification['predicted_category']}' "
            f"(confidence={pdf_classification['confidence']:.2f}, route='{pdf_classification['suggested_route']}')"
        )

        # ── Step 2: Native text extraction via PyMuPDF ───────────────────────
        pdf_pages = extract_text_pymupdf(file_path)
        logger.info(f"[Stage 1/3] PyMuPDF extracted {len(pdf_pages)} page(s)")

        # ── Step 3: Table extraction via pdfplumber + pandas ──────────────────
        tables = extract_tables_as_markdown(file_path)
        table_map: Dict[int, List[str]] = {}
        for t in tables:
            p_num = t["page_number"]
            table_map.setdefault(p_num, []).append(t["markdown"])

        # ── Step 4: Per-page multimodal routing ──────────────────────────────
        total_digital_pages = sum(1 for p in pdf_pages if not p.get("is_scanned", False))
        is_predominantly_digital = total_digital_pages >= max(2, len(pdf_pages) // 4)

        doc_fitz = None
        try:
            doc_fitz = pymupdf.open(file_path)
        except Exception:
            pass

        clip_pages_processed = 0
        max_clip_pages = 5  # Only compute CLIP on top visual/first pages to maintain low latency

        for page in pdf_pages:
            p_num = page["page_number"]
            page_text = page["text"]
            clip_emb: List[float] = []
            page_meta = {
                **forensic_metadata,
                "category": pdf_classification["predicted_category"],
                "classification_confidence": pdf_classification["confidence"],
                "pii_redacted": False,
                "faces_detected": 0
            }

            # Only run visual CLIP / face redactor if page is truly scanned (non-digital PDF) or page 1
            should_render_visual = (p_num == 1) or (page.get("is_scanned", False) and not is_predominantly_digital)
            if should_render_visual and clip_pages_processed < max_clip_pages:
                if doc_fitz and p_num - 1 < len(doc_fitz):
                    try:
                        fitz_page = doc_fitz[p_num - 1]
                        pix = fitz_page.get_pixmap(dpi=150)
                        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        if pix.n == 4:
                            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                        elif pix.n == 3:
                            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

                        # CLIP 512-d visual embedding
                        clip_emb = clip_service.embed_image(img_np)
                        clip_pages_processed += 1

                        # Check for faces and redact on genuine scanned pages
                        if page.get("is_scanned", False) and not is_predominantly_digital:
                            tmp_page_path = f"{file_path}_p{p_num}.jpg"
                            cv2.imwrite(tmp_page_path, img_np)
                            redact_res = redact_faces_in_image(tmp_page_path)
                            if redact_res["pii_redacted"]:
                                page_meta["pii_redacted"] = True
                                page_meta["faces_detected"] = redact_res["faces_detected"]
                                logger.info(f"[PIPELINE ROUTER] 🛡 Page {p_num}: Redacted {redact_res['faces_detected']} face(s)")
                            if os.path.exists(tmp_page_path):
                                os.remove(tmp_page_path)
                    except Exception as pix_err:
                        logger.warning(f"[PIPELINE ROUTER] Could not generate page {p_num} visual features: {pix_err}")

            # Only activate RapidOCR if the PDF is actually scanned (not a digital PDF with empty/blank pages)
            if page.get("is_scanned", False):
                if not is_predominantly_digital or len(pdf_pages) <= 5:
                    logger.info(f"[Stage 3/3]   Page {p_num}: ⚠ Scanned/empty — activating RapidOCR")
                    ocr_text = run_ocr(file_path, page_number=p_num)
                    if ocr_text:
                        page_text = ocr_text
                        logger.info(f"[Stage 3/3]   Page {p_num}: ✓ OCR recovered {len(ocr_text)} chars")
                    else:
                        page_text = f"[Scanned page {p_num} — Visual category: {pdf_classification['predicted_category']}]"
                else:
                    # In digital PDFs, blank/spacer pages don't need slow OCR
                    logger.debug(f"[Stage 3/3]   Page {p_num}: Spacer/blank digital page (OCR skipped)")

            # Append structured markdown tables if detected on this page
            if p_num in table_map:
                table_md_block = "\n\n### Extracted Tables:\n" + "\n\n".join(table_map[p_num])
                page_text = f"{page_text}\n{table_md_block}".strip()

            pages.append({
                "page_number": p_num,
                "content": page_text,
                "source_type": "pdf_multimodal",
                "clip_embedding": clip_emb,
                "metadata": page_meta
            })

        if doc_fitz:
            doc_fitz.close()

        logger.info(f"[PIPELINE ROUTER] ✓ PDF Processing COMPLETE: {len(pages)} pages indexed")

    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".heic"]:
        logger.info("[PIPELINE ROUTER] → Route C: Scanned Image — Vision Intelligence Pipeline")

        # ── 1. PII Face Redaction ─────────────────────────────────────────────
        logger.info("[Stage 1/4] Running InsightFace PII Redactor...")
        redact_res = redact_faces_in_image(file_path)
        if redact_res["pii_redacted"]:
            logger.info(
                f"[PIPELINE ROUTER] 🛡 PII Redactor: Sanitized {redact_res['faces_detected']} face(s) in {file_name}"
            )

        # ── 2. Content-Aware Document Image Classifier ────────────────────────
        logger.info("[Stage 2/4] Running Document Image Classifier (ViT + Morphological)...")
        classification = classify_document_page(file_path)
        cat = classification["predicted_category"]
        conf = classification["confidence"]
        logger.info(
            f"[PIPELINE ROUTER] 🎯 Document Classified: '{cat}' "
            f"(confidence={conf:.2f}, route='{classification['suggested_route']}')"
        )

        # ── 3. Multimodal CLIP Image Embedding ────────────────────────────────
        logger.info("[Stage 3/4] Computing 512-dim Normalized CLIP Visual Embedding...")
        clip_emb = clip_service.embed_image(file_path)
        logger.info(f"[PIPELINE ROUTER] ✓ CLIP Visual Vector Generated ({len(clip_emb)}d)")

        # ── 4. RapidOCR Text Extraction ───────────────────────────────────────
        logger.info("[Stage 4/4] Running OpenCV Cleanup + RapidOCR...")
        ocr_text = run_ocr(file_path)

        visual_tag = f"[Document Type: {cat.replace('_', ' ').title()} | Visual Features: {classification.get('visual_features', {})}]"
        if ocr_text:
            content = f"{visual_tag}\n\n{ocr_text}"
        else:
            content = f"{visual_tag}\n\n[Visual document without dense text — indexed via CLIP multimodal embeddings for cross-modal search]"

        page_meta = {
            **forensic_metadata,
            "category": cat,
            "classification_confidence": conf,
            "pii_redacted": redact_res["pii_redacted"],
            "faces_detected": redact_res["faces_detected"],
            "redaction_method": "InsightFace Zero-Knowledge Local Redactor"
        }

        pages.append({
            "page_number": 1,
            "content": content,
            "source_type": f"image_{cat}",
            "clip_embedding": clip_emb,
            "metadata": page_meta
        })
        logger.info(f"[PIPELINE ROUTER] ✓ Image Ingestion COMPLETE: category='{cat}', {len(content)} chars")

    elif ext in [".docx", ".doc"]:
        logger.info("[PIPELINE ROUTER] → Route E: Word Document Ingestion Pipeline (.docx/.doc)")
        docx_pages = extract_docx(file_path)
        for p in docx_pages:
            p["clip_embedding"] = []
            p["metadata"] = {**forensic_metadata, "category": "word_document"}
        pages = docx_pages

    elif ext in [".pptx", ".ppt"]:
        logger.info("[PIPELINE ROUTER] → Route F: PowerPoint Ingestion Pipeline (.pptx/.ppt)")
        pptx_pages = extract_pptx(file_path)
        for p in pptx_pages:
            p["clip_embedding"] = []
            p["metadata"] = {**forensic_metadata, "category": "presentation_slides"}
        pages = pptx_pages

    elif ext in [".xlsx", ".xls"]:
        logger.info("[PIPELINE ROUTER] → Route G: Excel Spreadsheet Ingestion Pipeline (.xlsx/.xls)")
        excel_pages = extract_excel(file_path)
        for p in excel_pages:
            p["clip_embedding"] = []
            p["metadata"] = {**forensic_metadata, "category": "table_financial"}
        pages = excel_pages

    elif ext in [".json"]:
        logger.info("[PIPELINE ROUTER] → Route H: Structured JSON Ingestion Pipeline")
        json_pages = extract_json_file(file_path)
        for p in json_pages:
            p["clip_embedding"] = []
            p["metadata"] = {**forensic_metadata, "category": "structured_data"}
        pages = json_pages

    elif ext in [".txt", ".md", ".csv", ".tsv"]:
        logger.info("[PIPELINE ROUTER] → Route D: Plain Text/CSV Read")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages.append({
                "page_number": 1,
                "content": content,
                "source_type": "plain_text",
                "clip_embedding": [],
                "metadata": {**forensic_metadata, "category": "plain_text"}
            })
        except Exception as e:
            logger.error(f"[PIPELINE ROUTER] ✗ Error reading text document: {e}")

    else:
        logger.warning(f"[PIPELINE ROUTER] → Route Fallback: Generic read for '{ext}'")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages.append({
                "page_number": 1,
                "content": content if content.strip() else f"Document {file_name} uploaded successfully.",
                "source_type": "generic_text",
                "clip_embedding": [],
                "metadata": {**forensic_metadata, "category": "generic"}
            })
        except Exception:
            pages.append({
                "page_number": 1,
                "content": f"Document {file_name} uploaded successfully (type: {ext}).",
                "source_type": "generic",
                "clip_embedding": [],
                "metadata": {**forensic_metadata, "category": "generic"}
            })

    logger.info("=" * 65)
    return pages

