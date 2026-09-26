import os
import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from PIL import Image
import pymupdf

from app.rag.clip_embeddings import clip_service

logger = logging.getLogger("DocuMind.ImageClassifier")

# Document classification categories requested
DOC_CATEGORIES = {
    "chart_diagram": "a chart, pie chart, bar graph, statistical plot, flowchart, or technical diagram",
    "table_financial": "a financial spreadsheet, tabular grid, balance sheet, or structured data table",
    "stamped_invoice": "an invoice, official bill, purchase order, receipt with stamps, seals, or signatures",
    "form_id_card": "an official identification card, passport, driver license, or employee badge with photo",
    "handwritten_note": "a handwritten document, cursive letter, diary entry, or handwritten memo",
    "digital_text": "a clean printed document page with standard paragraphs of corporate or academic text"
}


def _detect_visual_features(image_cv: np.ndarray) -> Dict[str, Any]:
    """
    Extracts structural computer vision features from the document image:
    1. Grid line density (tables)
    2. Saturated red/blue ink blobs (stamps/seals)
    3. Circular contours (official stamps)
    4. Edge / graphic variance (charts)
    """
    h, w = image_cv.shape[:2]
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY) if len(image_cv.shape) == 3 else image_cv

    # 1. Table Grid Line Detection
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, -2)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, w // 25), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, h // 25)))

    h_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)

    h_contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    v_contours, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    grid_lines_count = len(h_contours) + len(v_contours)
    has_grid = grid_lines_count >= 8

    # 2. Colored Stamp / Seal Detection (HSV color space)
    has_stamp = False
    stamp_score = 0.0
    if len(image_cv.shape) == 3:
        hsv = cv2.cvtColor(image_cv, cv2.COLOR_BGR2HSV)
        # Red stamps (two ranges in HSV)
        red_mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
        red_mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        # Blue/Purple stamps
        blue_mask = cv2.inRange(hsv, np.array([100, 70, 50]), np.array([140, 255, 255]))

        stamp_mask = red_mask1 | red_mask2 | blue_mask
        stamp_pixels = cv2.countNonZero(stamp_mask)
        total_pixels = h * w
        stamp_ratio = stamp_pixels / max(1, total_pixels)

        # Check for circular/elliptical shapes in stamp mask
        contours, _ = cv2.findContours(stamp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        circular_contours = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 300 < area < (total_pixels * 0.1):
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * (area / (perimeter * perimeter))
                    if circularity > 0.45:
                        circular_contours += 1

        if stamp_ratio > 0.003 or circular_contours > 0:
            has_stamp = True
            stamp_score = round(min(1.0, stamp_ratio * 50 + circular_contours * 0.3), 3)

    return {
        "grid_lines_count": grid_lines_count,
        "has_grid": has_grid,
        "has_stamp": has_stamp,
        "stamp_score": stamp_score
    }


def classify_document_page(image_path_or_array: Any) -> Dict[str, Any]:
    """
    Intelligent Content-Aware Document Image Classifier:
    Uses zero-shot ViT (CLIP) + morphological computer vision heuristics
    to classify document pages into:
      - chart_diagram
      - table_financial
      - stamped_invoice
      - form_id_card
      - handwritten_note
      - digital_text

    Enables intelligent routing before parsing or OCR.
    """
    result = {
        "predicted_category": "digital_text",
        "confidence": 0.5,
        "all_scores": {},
        "suggested_route": "digital_text",
        "visual_features": {}
    }

    try:
        # Load image for CV heuristics
        if isinstance(image_path_or_array, str):
            if not os.path.exists(image_path_or_array):
                return result
            img_cv = cv2.imread(image_path_or_array)
        elif isinstance(image_path_or_array, np.ndarray):
            img_cv = image_path_or_array
        elif isinstance(image_path_or_array, Image.Image):
            img_cv = cv2.cvtColor(np.array(image_path_or_array), cv2.COLOR_RGB2BGR)
        else:
            return result

        if img_cv is None:
            return result

        # 1. Structural visual feature extraction
        features = _detect_visual_features(img_cv)
        result["visual_features"] = features

        # 2. Vision-Transformer (CLIP) Zero-Shot Classification
        labels = list(DOC_CATEGORIES.keys())
        prompts = [DOC_CATEGORIES[k] for k in labels]
        raw_probs = clip_service.zero_shot_classify(img_cv, prompts)

        # Map back to category names
        scores = {}
        for k, prompt in DOC_CATEGORIES.items():
            scores[k] = raw_probs.get(prompt, 0.0)

        # 3. Boost scores with structural CV evidence
        if features["has_grid"]:
            scores["table_financial"] = scores.get("table_financial", 0) + 0.35

        if features["has_stamp"]:
            scores["stamped_invoice"] = scores.get("stamped_invoice", 0) + 0.30

        # Normalize boosted scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: round(v / total, 3) for k, v in scores.items()}

        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]

        result["predicted_category"] = best_category
        result["confidence"] = confidence
        result["all_scores"] = scores

        # Determine suggested pipeline route
        route_map = {
            "chart_diagram": "chart_pipeline",
            "table_financial": "table_pipeline",
            "stamped_invoice": "invoice_pipeline",
            "form_id_card": "id_card_pii",
            "handwritten_note": "handwritten_ocr",
            "digital_text": "digital_text"
        }
        result["suggested_route"] = route_map.get(best_category, "digital_text")

        logger.info(
            f"[ImageClassifier] 🎯 Document Classified: '{best_category}' "
            f"(confidence={confidence:.2f}, route='{result['suggested_route']}')"
        )

    except Exception as e:
        logger.error(f"[ImageClassifier] ✗ Classification failed: {e}")

    return result


def classify_pdf_first_page(pdf_path: str) -> Dict[str, Any]:
    """Renders page 1 of a PDF to pixmap and runs content-aware classifier."""
    try:
        doc = pymupdf.open(pdf_path)
        if len(doc) == 0:
            return {"predicted_category": "digital_text", "confidence": 0.5, "suggested_route": "digital_text"}

        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        doc.close()
        return classify_document_page(img_np)
    except Exception as e:
        logger.warning(f"[ImageClassifier] ⚠ Could not render PDF page 1 for classification: {e}")
        return {"predicted_category": "digital_text", "confidence": 0.5, "suggested_route": "digital_text"}
