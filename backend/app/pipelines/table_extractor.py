import logging
from typing import List, Dict, Any

logger = logging.getLogger("DocuMind.TableExtractor")

def extract_tables_as_markdown(file_path: str) -> List[Dict[str, Any]]:
    """
    [STAGE 2/3] Structured Table Extraction via pdfplumber + pandas.
    Extracts tables from PDF pages and converts to LLM-friendly Markdown syntax.
    """
    tables_by_page = []
    try:
        import pdfplumber
        import pandas as pd

        logger.info(f"  ┌─ [TableExtractor] Scanning for structured tables in: {file_path}")
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            found_tables = 0

            for page_idx, page in enumerate(pdf.pages):
                extracted_tables = page.extract_tables()
                if not extracted_tables:
                    continue

                logger.info(f"  │  [TableExtractor] Page {page_idx + 1}: found {len(extracted_tables)} table(s)")

                for t_idx, table in enumerate(extracted_tables):
                    if not table or len(table) < 2:
                        logger.info(f"  │    → Table {t_idx + 1}: skipped (< 2 rows)")
                        continue

                    try:
                        # Clean table cells: strip whitespace, replace None
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            cleaned_table.append(cleaned_row)

                        headers = cleaned_table[0]
                        data = cleaned_table[1:]

                        # Replace empty headers with fallback col names
                        valid_headers = [h if h else f"Col_{i+1}" for i, h in enumerate(headers)]
                        df = pd.DataFrame(data, columns=valid_headers)

                        # Convert to Markdown table (LLM-friendly)
                        md_table = df.to_markdown(index=False)

                        tables_by_page.append({
                            "page_number": page_idx + 1,
                            "table_index": t_idx + 1,
                            "markdown": md_table,
                        })
                        found_tables += 1
                        logger.info(f"  │    → Table {t_idx + 1}: converted to Markdown ({df.shape[0]} rows × {df.shape[1]} cols)")

                    except Exception as parse_err:
                        logger.warning(f"  │    → Table {t_idx + 1} on page {page_idx+1}: parse error — {parse_err}")

        logger.info(f"  └─ [TableExtractor] Extraction complete: {found_tables} table(s) found across {total_pages} pages.")

    except Exception as e:
        logger.warning(f"  └─ [TableExtractor] pdfplumber unavailable or encountered error: {e}")

    return tables_by_page
