import re
import uuid
from typing import List, Dict, Any
from app.config import settings

def recursive_chunk_text(
    text: str,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP
) -> List[str]:
    """
    Recursively splits text on paragraph breaks, sentences, and whitespaces.
    """
    if not text or not text.strip():
        return []

    # Clean redundant whitespace
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            # If paragraph itself is larger than chunk size, split by sentences
            if len(para) > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_chunk = ""
                for sent in sentences:
                    if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {sent}".strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = sent
                if sub_chunk:
                    current_chunk = sub_chunk
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def chunk_document_pages(
    doc_id: str,
    doc_name: str,
    pages_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Chunks pages while preserving page numbers, section boundaries, and source metadata.
    """
    all_chunks = []
    chunk_counter = 1

    for page_item in pages_data:
        p_num = page_item.get("page_number", 1)
        raw_text = page_item.get("content", "")

        clip_emb = page_item.get("clip_embedding", [])
        page_meta = page_item.get("metadata", {})

        text_chunks = recursive_chunk_text(raw_text)
        if not text_chunks and raw_text:
            text_chunks = [raw_text]
        elif not text_chunks:
            text_chunks = [f"[Visual content from {doc_name} page {p_num}]"]

        for text in text_chunks:
            chunk_id = f"{doc_id}-chunk-{chunk_counter}"
            all_chunks.append({
                "id": chunk_id,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page_number": p_num,
                "chunk_index": chunk_counter,
                "content": text,
                "source_tag": f"[DOC: {doc_name} | PAGE: {p_num}]",
                "clip_embedding": clip_emb,
                "metadata": page_meta
            })
            chunk_counter += 1

    return all_chunks
