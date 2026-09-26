import os
import mimetypes
import logging
from typing import List, Dict, Any
from app.pipelines.pdf_extractor import extract_text_pymupdf
from app.pipelines.table_extractor import extract_tables_as_markdown
from app.pipelines.ocr_pipeline import run_ocr

logger = logging.getLogger("DocuMind.PipelineRouter")

def process_document(file_path: str, file_name: str) -> List[Dict[str, Any]]:
    """
    Intelligent 3-way Multi-Pipeline Document Router:
    1. Digital PDFs: Uses PyMuPDF for native text, fonts, and headers.
    2. Tables: Injects markdown-converted tables from pdfplumber & pandas.
    3. Scanned PDFs/Images: Triggers OpenCV cleanup + OCR when pages lack digital text.
    
    Returns structured pages:
    [{"page_number": int, "content": str, "source_type": str}]
    """
    ext = os.path.splitext(file_name)[1].lower()
    pages: List[Dict[str, Any]] = []

    if ext == ".pdf":
        logger.info(f"Routing {file_name} to Digital PDF & Table Ingestion Pipeline...")
        # 1. Native text extraction
        pdf_pages = extract_text_pymupdf(file_path)
        
        # 2. Extract tables as markdown
        tables = extract_tables_as_markdown(file_path)
        table_map = {}
        for t in tables:
            p_num = t["page_number"]
            table_map.setdefault(p_num, []).append(t["markdown"])

        for page in pdf_pages:
            p_num = page["page_number"]
            page_text = page["text"]
            
            # If page is empty or scanned, route through OCR pipeline
            if page.get("is_scanned", False):
                logger.info(f"Page {p_num} in {file_name} has little/no text. Running OCR Pipeline...")
                ocr_text = run_ocr(file_path, page_number=p_num)
                if ocr_text:
                    page_text = ocr_text

            # Append structured markdown tables if present on this page
            if p_num in table_map:
                table_md_block = "\n\n### Extracted Tables:\n" + "\n\n".join(table_map[p_num])
                page_text = f"{page_text}\n{table_md_block}".strip()

            pages.append({
                "page_number": p_num,
                "content": page_text,
                "source_type": "pdf_digital_ocr"
            })

    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
        logger.info(f"Routing image {file_name} to OpenCV Cleanup + OCR Pipeline...")
        ocr_text = run_ocr(file_path)
        pages.append({
            "page_number": 1,
            "content": ocr_text or f"Image content from {file_name}",
            "source_type": "image_ocr"
        })

    elif ext in [".txt", ".md", ".csv"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            pages.append({
                "page_number": 1,
                "content": content,
                "source_type": "plain_text"
            })
        except Exception as e:
            logger.error(f"Error reading text document: {e}")
    else:
        # Fallback
        pages.append({
            "page_number": 1,
            "content": f"Document {file_name} uploaded successfully.",
            "source_type": "generic"
        })

    return pages
