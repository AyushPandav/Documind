import logging
from typing import List, Dict, Any

logger = logging.getLogger("DocuMind.TableExtractor")

def extract_tables_as_markdown(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts structured tables from PDF pages using pdfplumber and converts them
    to LLM-friendly Markdown table syntax using pandas.
    """
    tables_by_page = []
    try:
        import pdfplumber
        import pandas as pd

        with pdfplumber.open(file_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                extracted_tables = page.extract_tables()
                if not extracted_tables:
                    continue

                for t_idx, table in enumerate(extracted_tables):
                    if not table or len(table) < 2:
                        continue
                    
                    try:
                        # Clean table cells
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            cleaned_table.append(cleaned_row)
                            
                        headers = cleaned_table[0]
                        data = cleaned_table[1:]
                        
                        # Replace empty headers with col names
                        valid_headers = [h if h else f"Col_{i+1}" for i, h in enumerate(headers)]
                        df = pd.DataFrame(data, columns=valid_headers)
                        
                        # Convert to Markdown table
                        md_table = df.to_markdown(index=False)
                        
                        tables_by_page.append({
                            "page_number": page_idx + 1,
                            "table_index": t_idx + 1,
                            "markdown": md_table,
                        })
                    except Exception as parse_err:
                        logger.warning(f"Could not convert table {t_idx} on page {page_idx+1}: {parse_err}")
    except Exception as e:
        logger.warning(f"pdfplumber table extraction skipped or encountered: {e}")

    return tables_by_page
