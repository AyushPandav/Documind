import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("DocuMind.OCRPipeline")

def render_pdf_page_to_numpy(pdf_path: str, page_number: int = 1) -> Optional[np.ndarray]:
    """
    Renders a specific PDF page into an OpenCV-compatible BGR numpy image array at 200 DPI.
    """
    try:
        import pymupdf as fitz
        logger.info(f"  │    [OCR] Rendering PDF page {page_number} → numpy image at 200 DPI...")
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            logger.warning(f"  │    [OCR] Page {page_number} out of range (doc has {len(doc)} pages)")
            return None
        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=200)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        doc.close()

        import cv2
        if pix.n == 4:
            return cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        elif pix.n == 1:
            return cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        return img_np

    except Exception as e:
        logger.warning(f"  │    [OCR] Failed to render PDF page {page_number} to image: {e}")
        return None


def preprocess_image_opencv(image_input) -> Optional[np.ndarray]:
    """
    [STAGE 3/3 - Sub A] OpenCV 4-Step Preprocessing Pipeline for Noisy/Degraded Documents:
      Step 1. Grayscale conversion    — normalizes multi-channel scans
      Step 2. NlMeans Denoising       — removes scanner speckles, yellowing, artifact dots
      Step 3. Otsu Thresholding       — isolates faded text from dirty backgrounds
      Step 4. Deskewing (MinAreaRect) — detects & corrects page rotation to 0°
    """
    try:
        import cv2

        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return None
            image = cv2.imread(image_input)
            if image is None:
                return None
            logger.info(f"  │    [OpenCV] Loaded image from disk: {image.shape[1]}x{image.shape[0]}px")
        elif isinstance(image_input, np.ndarray):
            image = image_input
            logger.info(f"  │    [OpenCV] Received in-memory image: {image.shape[1]}x{image.shape[0]}px")
        else:
            return None

        # Step 1: Grayscale Conversion
        if len(image.shape) == 3 and image.shape[2] in [3, 4]:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        logger.info(f"  │    [OpenCV] Step 1/4: Grayscale conversion ✓")

        # Step 2: Denoising — remove scanner speckles and noise
        try:
            denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
            logger.info(f"  │    [OpenCV] Step 2/4: NlMeans Denoising ✓")
        except Exception:
            denoised = cv2.medianBlur(gray, 3)
            logger.info(f"  │    [OpenCV] Step 2/4: Median Blur (fallback) ✓")

        # Step 3: Adaptive Otsu Thresholding — eliminate bleed-through/shadows
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        logger.info(f"  │    [OpenCV] Step 3/4: Otsu Adaptive Threshold ✓")

        # Step 4: Deskewing using MinAreaRect
        coords = np.column_stack(np.where(thresh == 0))
        angle_corrected = 0.0
        if len(coords) > 60:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            if abs(angle) > 0.5 and abs(angle) < 45.0:
                (h, w) = thresh.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                angle_corrected = round(angle, 2)

        logger.info(f"  │    [OpenCV] Step 4/4: Deskew ✓ (rotation corrected: {angle_corrected}°)")
        return thresh

    except Exception as e:
        logger.warning(f"  │    [OpenCV] Preprocessing error: {e}")
        return None


def run_ocr(file_path: str, page_number: int = 1) -> str:
    """
    [STAGE 3/3 - Sub B] Full OCR Execution Pipeline:
      1. Render PDF page → numpy image (if PDF)
      2. OpenCV 4-step cleanup (grayscale → denoise → threshold → deskew)
      3. RapidOCR (ONNX-based, no C++ binaries required)
      4. Fallback: PyMuPDF native text extraction
    """
    ext = os.path.splitext(file_path)[1].lower()
    logger.info(f"  ┌─ [OCR] Starting OCR pipeline for: {os.path.basename(file_path)} (page {page_number})")

    # Step 1: Obtain image representation
    if ext == ".pdf":
        raw_img = render_pdf_page_to_numpy(file_path, page_number)
    else:
        logger.info(f"  │  [OCR] Direct image file detected: {ext}")
        raw_img = file_path

    # Step 2: Run OpenCV cleanup pipeline
    logger.info(f"  │  [OCR] Running OpenCV 4-step preprocessing pipeline...")
    cleaned_img = preprocess_image_opencv(raw_img)
    target_for_ocr = cleaned_img if cleaned_img is not None else raw_img

    if cleaned_img is not None:
        logger.info(f"  │  [OCR] OpenCV preprocessing complete — using cleaned image for OCR")
    else:
        logger.warning(f"  │  [OCR] OpenCV unavailable — using raw image directly")

    # Step 3: Execute RapidOCR (ONNX-based, pure Python)
    try:
        from rapidocr_onnxruntime import RapidOCR
        logger.info(f"  │  [OCR] Running RapidOCR (ONNX) engine...")
        engine = RapidOCR()
        result, elapse = engine(target_for_ocr)
        if result:
            ocr_text = "\n".join([line[1] for line in result if line and len(line) > 1])
            if ocr_text.strip():
                logger.info(f"  └─ [OCR] RapidOCR SUCCESS: {len(result)} text regions, {len(ocr_text)} chars extracted (elapsed: {elapse:.2f}s)")
                return ocr_text.strip()
            else:
                logger.warning(f"  │  [OCR] RapidOCR returned empty text, falling back...")
        else:
            logger.warning(f"  │  [OCR] RapidOCR returned no results, falling back...")
    except Exception as e:
        logger.info(f"  │  [OCR] RapidOCR not available ({e}), falling back to PyMuPDF...")

    # Step 4: Fallback to PyMuPDF native text
    if ext == ".pdf":
        try:
            import pymupdf as fitz
            logger.info(f"  │  [OCR] Fallback: PyMuPDF native text extraction...")
            doc = fitz.open(file_path)
            if 0 <= (page_number - 1) < len(doc):
                page_text = doc[page_number - 1].get_text().strip()
                doc.close()
                if page_text:
                    logger.info(f"  └─ [OCR] PyMuPDF fallback SUCCESS: {len(page_text)} chars extracted")
                    return page_text
            doc.close()
        except Exception as fitz_err:
            logger.error(f"  │  [OCR] PyMuPDF fallback also failed: {fitz_err}")

    logger.warning(f"  └─ [OCR] All OCR engines exhausted — returning empty string for page {page_number}")
    return ""
