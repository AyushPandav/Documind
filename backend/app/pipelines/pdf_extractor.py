import pymupdf as fitz
import logging
from typing import List, Dict, Any

logger = logging.getLogger("DocuMind.PDFExtractor")


def _extract_page_blocks(page) -> str:
    """
    Extract text from a page using spatial block ordering for better coverage.
    Falls back to plain text if blocks mode yields nothing.
    """
    try:
        blocks = page.get_text("blocks", sort=True)
        lines = []
        for block in blocks:
            # block = (x0, y0, x1, y1, text, block_no, block_type)
            if len(block) >= 5 and block[6] == 0:  # type 0 = text block
                txt = block[4].strip()
                if txt:
                    lines.append(txt)
        result = "\n".join(lines).strip()
        if result:
            return result
    except Exception:
        pass

    # Fallback: plain text
    return page.get_text("text").strip()


def extract_text_pymupdf(file_path: str) -> List[Dict[str, Any]]:
    """
    [STAGE 1/3] Digital PDF Text Extraction via PyMuPDF (fitz).
    Uses block-level spatial extraction for richer text coverage.
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
            text = _extract_page_blocks(page)

            # Only flag as scanned if very little text was recovered (< 20 chars)
            is_scanned = len(text) < 20

            status = "⚠ SCANNED/EMPTY" if is_scanned else f"✓ {len(text)} chars"
            logger.info(f"  │  [PyMuPDF] Page {page_num + 1}/{total_pages}: {status}")

            pages_data.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
                "is_scanned": is_scanned
            })

        doc.close()
        scanned_count = sum(1 for p in pages_data if p["is_scanned"])
        logger.info(
            f"  └─ [PyMuPDF] Extraction complete: {total_pages - scanned_count} digital pages, "
            f"{scanned_count} scanned pages."
        )

    except Exception as e:
        logger.error(f"  └─ [PyMuPDF] ERROR extracting PDF with PyMuPDF: {e}")

    return pages_data

