import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("DocuMind.OCRPipeline")

def render_pdf_page_to_numpy(pdf_path: str, page_number: int = 1) -> Optional[np.ndarray]:
    """
    Renders a specific page of a PDF document into an OpenCV-compatible BGR numpy image array.
    """
    try:
        import pymupdf as fitz
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return None
        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=200)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        doc.close()
        
        # Convert RGB/RGBA to BGR for OpenCV
        import cv2
        if pix.n == 4:
            return cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        elif pix.n == 1:
            return cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        return img_np
    except Exception as e:
        logger.warning(f"Failed to render PDF page {page_number} to image: {e}")
        return None

def preprocess_image_opencv(image_input) -> Optional[np.ndarray]:
    """
    OpenCV Preprocessing Pipeline for Noisy & Degraded Documents:
    1. Grayscale conversion: Standardizes multi-channel noisy scans.
    2. Denoising (cv2.fastNlMeansDenoising): Removes scanner speckles, yellowing & artifact dots.
    3. Adaptive Gaussian / Otsu Thresholding: Isolates faded text from dirty backgrounds.
    4. Deskewing (MinAreaRect): Detects rotation and auto-rotates slanted pages to 0°.
    
    Accepts either a file path string or an in-memory BGR numpy array.
    """
    try:
        import cv2

        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return None
            image = cv2.imread(image_input)
            if image is None:
                return None
        elif isinstance(image_input, np.ndarray):
            image = image_input
        else:
            return None

        # 1. Grayscale Conversion
        if len(image.shape) == 3 and image.shape[2] in [3, 4]:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 2. Denoising: Remove speckles and scanner noise
        try:
            denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        except Exception:
            denoised = cv2.medianBlur(gray, 3)

        # 3. Adaptive Otsu Thresholding to eliminate bleed-through and shadows
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 4. Deskewing using MinAreaRect
        coords = np.column_stack(np.where(thresh == 0))
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

        return thresh
    except Exception as e:
        logger.warning(f"OpenCV preprocessing error: {e}")
        return None

def run_ocr(file_path: str, page_number: int = 1) -> str:
    """
    Runs full OCR pipeline:
    - If PDF: extracts page as image
    - If Image: loads directly
    - Applies 4-step OpenCV cleanup (grayscale, denoise, otsu, deskew)
    - Runs RapidOCR (ONNX-based)
    - Falls back to PyMuPDF text if needed
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Obtain image representation
    if ext == ".pdf":
        raw_img = render_pdf_page_to_numpy(file_path, page_number)
    else:
        raw_img = file_path

    # 2. Run OpenCV cleanup
    cleaned_img = preprocess_image_opencv(raw_img)
    target_for_ocr = cleaned_img if cleaned_img is not None else raw_img

    # 3. Execute RapidOCR
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(target_for_ocr)
        if result:
            ocr_text = "\n".join([line[1] for line in result if line and len(line) > 1])
            if ocr_text.strip():
                logger.info(f"RapidOCR extracted {len(ocr_text)} characters from page {page_number}.")
                return ocr_text.strip()
    except Exception as e:
        logger.info(f"RapidOCR execution note: {e}")

    # 4. Fallback to PyMuPDF native text
    if ext == ".pdf":
        try:
            import pymupdf as fitz
            doc = fitz.open(file_path)
            if 0 <= (page_number - 1) < len(doc):
                page_text = doc[page_number - 1].get_text().strip()
                doc.close()
                if page_text:
                    return page_text
            doc.close()
        except Exception:
            pass

    return ""
