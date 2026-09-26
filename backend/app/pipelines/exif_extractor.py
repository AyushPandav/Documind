import os
import logging
from typing import Dict, Any, Optional
from PIL import Image, ExifTags
import pymupdf

logger = logging.getLogger("DocuMind.ExifExtractor")


def _clean_exif_val(val: Any) -> Any:
    """Sanitizes binary or unprintable EXIF byte values into serializable formats."""
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8", errors="ignore").strip("\x00 \t\r\n")
        except Exception:
            return str(val)
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)


def extract_image_exif(file_path: str) -> Dict[str, Any]:
    """
    Extracts forensic camera, scanner, and digital document metadata
    from scanned image files (.png, .jpg, .jpeg, .tiff, .webp).

    Identifies scanner model, capture timestamp, resolution (DPI),
    color profile, and software version for tamper-proof source attribution.
    """
    metadata: Dict[str, Any] = {
        "has_metadata": False,
        "media_type": "image",
        "width": 0,
        "height": 0,
        "megapixels": 0.0,
        "format": "Unknown",
        "color_space": "Unknown",
        "dpi": 72,
        "scanner_make": None,
        "scanner_model": None,
        "software": None,
        "scan_date": None,
        "orientation": 1,
        "raw_tags": {}
    }

    if not os.path.exists(file_path):
        return metadata

    try:
        with Image.open(file_path) as img:
            w, h = img.size
            metadata["width"] = w
            metadata["height"] = h
            metadata["megapixels"] = round((w * h) / 1_000_000.0, 2)
            metadata["format"] = img.format or "JPEG"
            metadata["color_space"] = img.mode  # RGB, RGBA, L (Grayscale), CMYK

            # Extract DPI
            dpi_info = img.info.get("dpi")
            if dpi_info and isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 1:
                metadata["dpi"] = int(round(dpi_info[0]))
            elif "jfif_density" in img.info:
                metadata["dpi"] = int(img.info["jfif_density"][0])

            # Extract EXIF tags
            exif_data = img.getexif()
            if exif_data:
                tag_map = {}
                for tag_id, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    tag_map[tag_name] = _clean_exif_val(value)

                metadata["raw_tags"] = tag_map
                metadata["has_metadata"] = True

                # Standard tags
                metadata["scanner_make"] = tag_map.get("Make")
                metadata["scanner_model"] = tag_map.get("Model")
                metadata["software"] = tag_map.get("Software")
                metadata["scan_date"] = (
                    tag_map.get("DateTimeOriginal")
                    or tag_map.get("DateTimeDigitized")
                    or tag_map.get("DateTime")
                )
                metadata["orientation"] = tag_map.get("Orientation", 1)

                if "XResolution" in tag_map:
                    try:
                        metadata["dpi"] = int(float(str(tag_map["XResolution"])))
                    except Exception:
                        pass

        logger.info(
            f"[ExifExtractor] ✓ Image Metadata ({metadata['format']}, {metadata['width']}x{metadata['height']}, "
            f"{metadata['dpi']} DPI, Scanner: {metadata['scanner_make'] or 'N/A'} {metadata['scanner_model'] or ''})"
        )
    except Exception as e:
        logger.warning(f"[ExifExtractor] ⚠ Error reading image EXIF for {file_path}: {e}")

    return metadata


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extracts forensic PDF document metadata: producer, creator, creation date,
    modification date, title, author, and encryption flag.
    """
    metadata: Dict[str, Any] = {
        "has_metadata": False,
        "media_type": "pdf",
        "title": None,
        "author": None,
        "creator": None,
        "producer": None,
        "creation_date": None,
        "mod_date": None,
        "page_count": 0,
        "is_encrypted": False
    }

    if not os.path.exists(file_path):
        return metadata

    try:
        doc = pymupdf.open(file_path)
        metadata["page_count"] = len(doc)
        metadata["is_encrypted"] = doc.is_encrypted

        pdf_meta = doc.metadata or {}
        if pdf_meta:
            metadata["has_metadata"] = True
            metadata["title"] = pdf_meta.get("title") or None
            metadata["author"] = pdf_meta.get("author") or None
            metadata["creator"] = pdf_meta.get("creator") or None
            metadata["producer"] = pdf_meta.get("producer") or None
            metadata["creation_date"] = pdf_meta.get("creationDate") or None
            metadata["mod_date"] = pdf_meta.get("modDate") or None

        doc.close()
        logger.info(
            f"[ExifExtractor] ✓ PDF Metadata ({metadata['page_count']} pages, "
            f"Creator: {metadata['creator'] or 'N/A'}, Producer: {metadata['producer'] or 'N/A'})"
        )
    except Exception as e:
        logger.warning(f"[ExifExtractor] ⚠ Error reading PDF metadata for {file_path}: {e}")

    return metadata


def extract_file_metadata(file_path: str) -> Dict[str, Any]:
    """Unified dispatcher for EXIF / Digital forensics extraction."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_pdf_metadata(file_path)
    elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
        return extract_image_exif(file_path)
    else:
        return {
            "has_metadata": False,
            "media_type": ext.lstrip("."),
            "file_size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
