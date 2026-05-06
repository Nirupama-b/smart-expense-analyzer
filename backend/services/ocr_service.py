"""
OCR service built on Tesseract (via pytesseract) with Pillow-based image pre-processing.
Replaces EasyOCR to avoid PyTorch SIGSEGV on macOS arm64.
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class OCRService:
    """Receipt OCR: image enhancement, text extraction, and field parsing."""

    # ------------------------------------------------------------------
    # Image pre-processing
    # ------------------------------------------------------------------
    @staticmethod
    def preprocess_image(image_path: str) -> str:
        """
        Enhance a receipt image for better OCR accuracy.

        Steps: grayscale -> 1.5x contrast boost -> sharpen.
        Returns the path to the preprocessed file.
        """
        from PIL import Image, ImageEnhance, ImageFilter

        img = Image.open(image_path)
        img = img.convert("L")
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = img.filter(ImageFilter.SHARPEN)

        p = Path(image_path)
        preprocessed_path = str(p.parent / f"{p.stem}_preprocessed{p.suffix}")
        img.save(preprocessed_path)
        logger.info("Preprocessed image saved to %s", preprocessed_path)
        return preprocessed_path

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------
    @staticmethod
    def extract_text(image_path: str) -> str:
        """Run Tesseract OCR on *image_path* and return the full text."""
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        logger.info("Extracted %d characters from %s", len(text), image_path)
        return text

    # ------------------------------------------------------------------
    # Amount extraction
    # ------------------------------------------------------------------
    @staticmethod
    def extract_amount(text: str) -> Optional[float]:
        """
        Extract the most likely total dollar amount from receipt text.

        Returns the largest matched amount (grand total is usually last).
        """
        if not text:
            return None

        amounts = []

        general_pattern = r"\$?\s?(\d{1,3}(?:,\d{3})*\.\d{2})"
        for match in re.finditer(general_pattern, text):
            amounts.append(float(match.group(1).replace(",", "")))

        total_pattern = r"(?i)total\s*:?\s*\$?\s?(\d{1,3}(?:,\d{3})*\.\d{2})"
        for match in re.finditer(total_pattern, text):
            amounts.append(float(match.group(1).replace(",", "")))

        return max(amounts) if amounts else None

    # ------------------------------------------------------------------
    # Merchant extraction
    # ------------------------------------------------------------------
    @staticmethod
    def extract_merchant(text: str) -> Optional[str]:
        """Heuristic: the first non-empty line is usually the merchant name."""
        if not text:
            return None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return None
