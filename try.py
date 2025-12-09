import os
import re
from typing import Dict, List

import cv2
import numpy as np
from PIL import Image
import pytesseract


# =============== CONFIG ====================

# Change this if Tesseract is installed in a different path
# (For Linux/Mac, you usually don't need this line.)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

IMAGES_DIR = "images"
OUTPUT_DIR = "outputs"

# Tesseract config: LSTM OCR engine, assume a block of text.
TESS_CONFIG = r"--oem 3 --psm 6"

# ==========================================


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def preprocess_image(img_bgr: np.ndarray) -> np.ndarray:
    """
    Basic preprocessing:
    - convert to gray
    - denoise
    - adaptive threshold
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Light denoising
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold to handle uneven lighting
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )

    return thresh


def ocr_with_boxes(preprocessed_img: np.ndarray) -> Dict:
    """
    Run Tesseract OCR and return the detailed data dictionary
    (text, confidences, bounding boxes).
    """
    data = pytesseract.image_to_data(
        preprocessed_img,
        output_type=pytesseract.Output.DICT,
        config=TESS_CONFIG,
    )
    return data


def build_full_text(ocr_data: Dict) -> str:
    words = [w for w in ocr_data["text"] if w.strip() != ""]
    return " ".join(words)


def detect_pii(text: str) -> Dict[str, List[str]]:
    """
    Simple rule/regex-based PII detection.
    You can extend this as you like.
    """
    pii = {}

    # Common patterns for this document type
    patient_name = re.findall(
        r"Patient\s*Name[:\-]?\s*([A-Za-z\s]+)", text, flags=re.IGNORECASE
    )
    if patient_name:
        pii["patient_name"] = [n.strip() for n in patient_name]

    ipd_no = re.findall(
        r"IPD\s*No\.?\s*[:\-]?\s*([A-Za-z0-9/]+)", text, flags=re.IGNORECASE
    )
    if ipd_no:
        pii["ipd_no"] = ipd_no

    uhid = re.findall(
        r"UHID\s*No\.?\s*[:\-]?\s*([A-Za-z0-9/]+)", text, flags=re.IGNORECASE
    )
    if uhid:
        pii["uhid"] = uhid

    age = re.findall(r"Age\s*[:\-]?\s*(\d{1,3})", text, flags=re.IGNORECASE)
    if age:
        pii["age"] = age

    sex = re.findall(r"Sex\s*[:\-]?\s*([MFmf])", text)
    if sex:
        pii["sex"] = [s.upper() for s in sex]

    # Dates like 11/11/25, 10/4/25 etc.
    dates = re.findall(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        text,
    )
    if dates:
        pii["dates"] = list(set(dates))

    # Long numeric IDs (>= 6 digits)
    long_numbers = re.findall(r"\b\d{6,}\b", text)
    if long_numbers:
        pii.setdefault("long_numbers", list(set(long_numbers)))

    # 10-digit phone-like numbers (if any)
    phone = re.findall(r"\b\d{10}\b", text)
    if phone:
        pii["phone"] = list(set(phone))

    return pii


def build_pii_token_set(pii: Dict[str, List[str]]) -> set:
    """
    From PII strings make a set of individual tokens (words/numbers)
    so that we can match them to OCR words for redaction.
    """
    tokens = set()
    for values in pii.values():
        for v in values:
            for tok in re.findall(r"\w+", str(v)):
                tokens.add(tok.lower())
    return tokens


def redact_image(original_img: np.ndarray, ocr_data: Dict, pii_tokens: set) -> np.ndarray:
    """
    Black out words which match any PII token.
    """
    redacted = original_img.copy()
    n_boxes = len(ocr_data["text"])

    for i in range(n_boxes):
        word = ocr_data["text"][i]
        if not word or word.strip() == "":
            continue

        # Confidence filter: skip very low-confidence words
        try:
            conf = float(ocr_data["conf"][i])
        except ValueError:
            conf = -1

        if conf < 40:
            continue

        clean_word = re.sub(r"\W+", "", word).lower()
        if clean_word == "":
            continue

        if clean_word in pii_tokens:
            x = ocr_data["left"][i]
            y = ocr_data["top"][i]
            w = ocr_data["width"][i]
            h = ocr_data["height"][i]

            # Fill rectangle with black
            cv2.rectangle(redacted, (x, y), (x + w, y + h), (0, 0, 0), -1)

    return redacted


def process_single_image(image_path: str):
    print(f"\nProcessing: {image_path}")
    base_name = os.path.splitext(os.path.basename(image_path))[0]

    # Read original image in BGR (OpenCV format)
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        print("  [!] Could not read image, skipping.")
        return

    preprocessed = preprocess_image(img_bgr)

    # For Tesseract we need RGB or grayscale; we'll use the thresholded image.
    ocr_data = ocr_with_boxes(preprocessed)
    extracted_text = build_full_text(ocr_data)
    pii = detect_pii(extracted_text)
    pii_tokens = build_pii_token_set(pii)

    # Redact image using original (better for visualization)
    redacted = redact_image(img_bgr, ocr_data, pii_tokens)

    # ---- Save outputs ----
    text_path = os.path.join(OUTPUT_DIR, f"{base_name}_text.txt")
    pii_path = os.path.join(OUTPUT_DIR, f"{base_name}_pii.txt")
    redacted_path = os.path.join(OUTPUT_DIR, f"{base_name}_redacted.jpg")

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)

    with open(pii_path, "w", encoding="utf-8") as f:
        f.write("Detected PII:\n")
        for key, vals in pii.items():
            f.write(f"{key}: {', '.join(vals)}\n")

    cv2.imwrite(redacted_path, redacted)

    print(f"  Saved text      -> {text_path}")
    print(f"  Saved PII       -> {pii_path}")
    print(f"  Saved redacted  -> {redacted_path}")


def main():
    ensure_output_dir()

    if not os.path.isdir(IMAGES_DIR):
        print(f"[!] Images folder '{IMAGES_DIR}' not found.")
        print("    Create it and put your .jpg images inside.")
        return

    image_files = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not image_files:
        print(f"[!] No .jpg/.jpeg/.png files found in '{IMAGES_DIR}'.")
        return

    for img_name in image_files:
        img_path = os.path.join(IMAGES_DIR, img_name)
        process_single_image(img_path)

    print("\nDone. Check the 'outputs' folder for results.")


if __name__ == "__main__":
    main()
