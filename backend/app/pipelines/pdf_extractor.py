import pymupdf as fitz
from typing import List, Dict, Any
import logging

logger = logging.getLogger("DocuMind.PDFExtractor")

def extract_text_pymupdf(file_path: str) -> List[Dict[str, Any]]:
    """
    [STAGE 1/3] Digital PDF Text Extraction via PyMuPDF (fitz).
    Extracts native text, page numbers, character count, and scan-detection flag.
    Returns list of dicts: {"page_number": int, "text": str, "char_count": int, "is_scanned": bool}
    """
    pages_data = []
    try:
        logger.info(f"  ┌─ [PyMuPDF] Opening PDF: {file_path}")
        doc = fitz.open(file_path)
        total_pages = len(doc)
        logger.info(f"  │  [PyMuPDF] PDF loaded — {total_pages} pages detected.")

        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text").strip()
            is_scanned = len(text) < 40

            status = "⚠ SCANNED/EMPTY" if is_scanned else f"✓ {len(text)} chars"
            logger.info(f"  │  [PyMuPDF] Page {page_num + 1}/{total_pages}: {status}")

            pages_data.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
                "is_scanned": is_scanned  # if almost no text, likely a scanned image
            })

        doc.close()
        scanned_count = sum(1 for p in pages_data if p["is_scanned"])
        logger.info(f"  └─ [PyMuPDF] Extraction complete: {total_pages - scanned_count} digital pages, {scanned_count} scanned pages.")

    except Exception as e:
        logger.error(f"  └─ [PyMuPDF] ERROR extracting PDF with PyMuPDF: {e}")

    return pages_data
