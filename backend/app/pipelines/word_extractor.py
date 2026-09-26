"""
DocuMind Pipeline — Word & Office Document Extractor
======================================================
Extracts text, headings, and structured tables from Microsoft Word (.docx),
PowerPoint (.pptx), Excel (.xlsx), and JSON documents.
Zero external C-binary dependency — parses OpenXML archives directly via zipfile + XML.
"""

import os
import zipfile
import json
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

logger = logging.getLogger("DocuMind.WordExtractor")

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
A_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
P_NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


def extract_docx(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts structured content from a Word document (.docx).
    Parses paragraphs and tables from word/document.xml.
    Groups sections into virtual pages (~2000 chars per page).
    """
    logger.info(f"[WordExtractor] ▶ Extracting Word document: {os.path.basename(file_path)}")
    sections: List[str] = []

    try:
        with zipfile.ZipFile(file_path) as z:
            if "word/document.xml" not in z.namelist():
                logger.warning("[WordExtractor] word/document.xml not found in archive")
                return [{"page_number": 1, "content": f"[Word document: {os.path.basename(file_path)}]", "source_type": "docx"}]

            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)

            body = tree.find("w:body", W_NS)
            if body is None:
                body = tree

            for elem in body:
                tag = elem.tag.split("}")[-1]

                if tag == "p":  # Paragraph
                    texts = [node.text for node in elem.iterfind(".//w:t", W_NS) if node.text]
                    para_text = "".join(texts).strip()
                    if para_text:
                        # Check if paragraph has heading style
                        pStyle = elem.find(".//w:pPr/w:pStyle", W_NS)
                        style_val = pStyle.attrib.get(f"{{{W_NS['w']}}}val", "") if pStyle is not None else ""
                        if "heading" in style_val.lower():
                            sections.append(f"\n## {para_text}\n")
                        else:
                            sections.append(para_text)

                elif tag == "tbl":  # Table
                    rows = []
                    for row in elem.iterfind(".//w:tr", W_NS):
                        cells = []
                        for cell in row.iterfind(".//w:tc", W_NS):
                            cell_texts = [node.text for node in cell.iterfind(".//w:t", W_NS) if node.text]
                            cells.append(" ".join("".join(cell_texts).split()))
                        if cells:
                            rows.append(cells)

                    if rows:
                        # Build markdown table
                        col_count = max(len(r) for r in rows)
                        # Pad rows
                        padded_rows = [r + [""] * (col_count - len(r)) for r in rows]
                        headers = padded_rows[0]
                        separator = ["---"] * col_count
                        data_rows = padded_rows[1:] if len(padded_rows) > 1 else []

                        md_lines = [
                            "| " + " | ".join(h if h else f"Col {i+1}" for i, h in enumerate(headers)) + " |",
                            "| " + " | ".join(separator) + " |"
                        ]
                        for r in data_rows:
                            md_lines.append("| " + " | ".join(r) + " |")

                        sections.append("\n" + "\n".join(md_lines) + "\n")

        full_text = "\n\n".join(sections).strip()
        logger.info(f"[WordExtractor] ✓ Extracted {len(sections)} sections ({len(full_text)} characters)")

        # Paginate content into pages of ~2000 characters
        pages = []
        page_size = 2000
        paragraphs = full_text.split("\n\n")
        current_page = []
        current_len = 0
        page_num = 1

        for p in paragraphs:
            if current_len + len(p) > page_size and current_page:
                pages.append({
                    "page_number": page_num,
                    "content": "\n\n".join(current_page),
                    "source_type": "docx"
                })
                page_num += 1
                current_page = [p]
                current_len = len(p)
            else:
                current_page.append(p)
                current_len += len(p)

        if current_page:
            pages.append({
                "page_number": page_num,
                "content": "\n\n".join(current_page),
                "source_type": "docx"
            })

        return pages if pages else [{"page_number": 1, "content": full_text or "[Empty Word Document]", "source_type": "docx"}]

    except Exception as e:
        logger.error(f"[WordExtractor] Error extracting DOCX: {e}")
        # Plain text fallback
        return [{"page_number": 1, "content": f"[Word document: {os.path.basename(file_path)} — Error parsing: {e}]", "source_type": "docx"}]


def extract_pptx(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts slide-by-slide text from PowerPoint (.pptx).
    Each slide maps to a distinct page number.
    """
    logger.info(f"[WordExtractor] ▶ Extracting PowerPoint presentation: {os.path.basename(file_path)}")
    pages = []
    try:
        with zipfile.ZipFile(file_path) as z:
            slide_files = sorted(
                [f for f in z.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")],
                key=lambda x: int("".join(filter(str.isdigit, x)) or 0)
            )

            for idx, slide_file in enumerate(slide_files):
                slide_xml = z.read(slide_file)
                tree = ET.fromstring(slide_xml)
                texts = [node.text for node in tree.iterfind(".//a:t", A_NS) if node.text]
                slide_content = "\n".join(texts).strip()
                if not slide_content:
                    slide_content = f"[Slide {idx + 1} - Image or Visual Content]"
                pages.append({
                    "page_number": idx + 1,
                    "content": f"### Slide {idx + 1}\n\n{slide_content}",
                    "source_type": "pptx"
                })

        logger.info(f"[WordExtractor] ✓ Extracted {len(pages)} slide(s)")
        return pages if pages else [{"page_number": 1, "content": "[Empty PowerPoint presentation]", "source_type": "pptx"}]
    except Exception as e:
        logger.error(f"[WordExtractor] Error extracting PPTX: {e}")
        return [{"page_number": 1, "content": f"[PowerPoint presentation: {os.path.basename(file_path)}]", "source_type": "pptx"}]


def extract_excel(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts tables from Excel (.xlsx) files and converts sheets to Markdown tables.
    """
    logger.info(f"[WordExtractor] ▶ Extracting Excel spreadsheet: {os.path.basename(file_path)}")
    try:
        import pandas as pd
        excel_file = pd.ExcelFile(file_path)
        pages = []
        for idx, sheet_name in enumerate(excel_file.sheet_names):
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            md_table = df.to_markdown(index=False) if hasattr(df, "to_markdown") else str(df)
            pages.append({
                "page_number": idx + 1,
                "content": f"### Sheet: {sheet_name}\n\n{md_table}",
                "source_type": "xlsx"
            })
        logger.info(f"[WordExtractor] ✓ Extracted {len(pages)} sheet(s) from Excel")
        return pages if pages else [{"page_number": 1, "content": "[Empty spreadsheet]", "source_type": "xlsx"}]
    except Exception as e:
        logger.warning(f"[WordExtractor] pandas read_excel failed ({e}), attempting fallback...")
        return [{"page_number": 1, "content": f"[Excel spreadsheet: {os.path.basename(file_path)}]", "source_type": "xlsx"}]


def extract_json_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses structured JSON files into readable Markdown representation.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        formatted = json.dumps(data, indent=2)
        return [{
            "page_number": 1,
            "content": f"```json\n{formatted}\n```",
            "source_type": "json"
        }]
    except Exception as e:
        return [{"page_number": 1, "content": f"[JSON file parse error: {e}]", "source_type": "json"}]
