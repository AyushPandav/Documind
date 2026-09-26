import pymupdf as fitz
from typing import List, Dict, Any
import logging

logger = logging.getLogger("DocuMind.PDFExtractor")

def extract_text_pymupdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text, page numbers, and structural blocks using PyMuPDF (fitz).
    Returns list of dicts: {"page_number": int, "text": str, "char_count": int}
    """
    pages_data = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            
            pages_data.append({
                "page_number": page_num + 1,
                "text": text,
                "char_count": len(text),
                "is_scanned": len(text) < 40  # if almost no text, likely a scan
            })
        doc.close()
    except Exception as e:
        logger.error(f"Error extracting PDF with PyMuPDF: {e}")
        
    return pages_data
