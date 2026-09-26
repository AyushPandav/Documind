import os
import mimetypes
import logging
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

logger = logging.getLogger("DocuMind.PipelineRouter")


def process_document(file_path: str, file_name: str) -> List[Dict[str, Any]]:
    """
    [PIPELINE ROUTER] Intelligent 3-Way Multi-Pipeline Document Router:

    Route A — Digital PDF   → PyMuPDF native text + pdfplumber table extraction
    Route B — Scanned Pages → OpenCV cleanup (grayscale/denoise/threshold/deskew) + RapidOCR
    Route C — Image files   → OpenCV cleanup + RapidOCR
    Route D — Text/CSV/MD   → Direct UTF-8 read

    Returns structured pages: [{"page_number": int, "content": str, "source_type": str}]
    """
    ext = os.path.splitext(file_name)[1].lower()
    pages: List[Dict[str, Any]] = []
    file_size_kb = round(os.path.getsize(file_path) / 1024, 1) if os.path.exists(file_path) else 0

    logger.info("=" * 65)
    logger.info(f"[PIPELINE ROUTER] Document: {file_name}")
    logger.info(f"[PIPELINE ROUTER] Extension: {ext.upper()} | Size: {file_size_kb} KB")
    logger.info("=" * 65)

    if ext == ".pdf":
        logger.info("[PIPELINE ROUTER] → Route A: Digital PDF + Table Ingestion Pipeline")

        # ── Stage 1: Native text extraction via PyMuPDF ──────────────────────
        logger.info("[Stage 1/3] PyMuPDF Native Text Extraction...")
        pdf_pages = extract_text_pymupdf(file_path)
        logger.info(f"[Stage 1/3] ✓ Extracted {len(pdf_pages)} pages")

        # ── Stage 2: Table extraction via pdfplumber + pandas ─────────────────
        logger.info("[Stage 2/3] pdfplumber + pandas Table Extraction...")
        tables = extract_tables_as_markdown(file_path)
        table_map: Dict[int, List[str]] = {}
        for t in tables:
            p_num = t["page_number"]
            table_map.setdefault(p_num, []).append(t["markdown"])
        logger.info(f"[Stage 2/3] ✓ Extracted {len(tables)} table(s) from {len(table_map)} page(s)")

        # ── Stage 3: Per-page routing — digital text or OCR ──────────────────
        logger.info("[Stage 3/3] Per-Page Text/OCR Routing...")
        for page in pdf_pages:
            p_num = page["page_number"]
            page_text = page["text"]

            if page.get("is_scanned", False):
                logger.info(f"[Stage 3/3]   Page {p_num}: ⚠ Scanned/empty — activating OpenCV+OCR fallback")
                ocr_text = run_ocr(file_path, page_number=p_num)
                if ocr_text:
                    page_text = ocr_text
                    logger.info(f"[Stage 3/3]   Page {p_num}: ✓ OCR recovered {len(ocr_text)} chars")
                else:
                    logger.warning(f"[Stage 3/3]   Page {p_num}: ✗ OCR returned empty")
            else:
                logger.info(f"[Stage 3/3]   Page {p_num}: ✓ Digital text ({page['char_count']} chars)")

            # Append structured markdown tables if detected on this page
            if p_num in table_map:
                table_md_block = "\n\n### Extracted Tables:\n" + "\n\n".join(table_map[p_num])
                page_text = f"{page_text}\n{table_md_block}".strip()
                logger.info(f"[Stage 3/3]   Page {p_num}: ✓ Appended {len(table_map[p_num])} extracted table(s)")

            pages.append({
                "page_number": p_num,
                "content": page_text,
                "source_type": "pdf_digital_ocr"
            })

        logger.info(f"[PIPELINE ROUTER] ✓ PDF Processing COMPLETE: {len(pages)} pages ready for chunking")

    elif ext in [".docx", ".doc"]:
        logger.info("[PIPELINE ROUTER] → Route E: Word Document Ingestion Pipeline (.docx/.doc)")
        pages = extract_docx(file_path)
        logger.info(f"[PIPELINE ROUTER] ✓ Word Document Processing COMPLETE: {len(pages)} page(s) ready")

    elif ext in [".pptx", ".ppt"]:
        logger.info("[PIPELINE ROUTER] → Route F: PowerPoint Ingestion Pipeline (.pptx/.ppt)")
        pages = extract_pptx(file_path)
        logger.info(f"[PIPELINE ROUTER] ✓ PowerPoint Processing COMPLETE: {len(pages)} slide(s) ready")

    elif ext in [".xlsx", ".xls"]:
        logger.info("[PIPELINE ROUTER] → Route G: Excel Spreadsheet Ingestion Pipeline (.xlsx/.xls)")
        pages = extract_excel(file_path)
        logger.info(f"[PIPELINE ROUTER] ✓ Excel Processing COMPLETE: {len(pages)} sheet(s) ready")

    elif ext in [".json"]:
        logger.info("[PIPELINE ROUTER] → Route H: Structured JSON Ingestion Pipeline")
        pages = extract_json_file(file_path)
        logger.info(f"[PIPELINE ROUTER] ✓ JSON Processing COMPLETE")

    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".heic"]:
        logger.info("[PIPELINE ROUTER] → Route C: Image File — OpenCV Cleanup + RapidOCR Pipeline")
        logger.info("[Stage 1/1] Running OpenCV + RapidOCR on image...")
        ocr_text = run_ocr(file_path)
        content = ocr_text or f"[Image content from {file_name} — OCR returned no text]"
        pages.append({
            "page_number": 1,
            "content": content,
            "source_type": "image_ocr"
        })
        logger.info(f"[PIPELINE ROUTER] ✓ Image OCR COMPLETE: {len(content)} chars extracted")

    elif ext in [".txt", ".md", ".csv", ".tsv"]:
        logger.info(f"[PIPELINE ROUTER] → Route D: Plain Text/CSV — Direct UTF-8 Read")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages.append({
                "page_number": 1,
                "content": content,
                "source_type": "plain_text"
            })
            logger.info(f"[PIPELINE ROUTER] ✓ Text Read COMPLETE: {len(content)} chars, {content.count(chr(10))+1} lines")
        except Exception as e:
            logger.error(f"[PIPELINE ROUTER] ✗ Error reading text document: {e}")

    else:
        logger.warning(f"[PIPELINE ROUTER] → Route Fallback: Attempting text read for '{ext}'")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages.append({
                "page_number": 1,
                "content": content if content.strip() else f"Document {file_name} uploaded successfully.",
                "source_type": "generic_text"
            })
        except Exception:
            pages.append({
                "page_number": 1,
                "content": f"Document {file_name} uploaded successfully (type: {ext}).",
                "source_type": "generic"
            })

    logger.info("=" * 65)
    return pages
