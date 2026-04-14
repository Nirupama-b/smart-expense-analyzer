"""
OCR service built on EasyOCR with Pillow-based image pre-processing.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class OCRService:
    """Receipt OCR: image enhancement, text extraction, and field parsing."""

    # Lazy class-level singleton — created once per process
    _reader = None

    @classmethod
    def _get_reader(cls):
        """Return a lazily-initialised EasyOCR reader."""
        if cls._reader is None:
            import easyocr

            cls._reader = easyocr.Reader(["en"], gpu=False)
        return cls._reader

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

        # Convert to grayscale
        img = img.convert("L")

        # Boost contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # Save alongside the original
        p = Path(image_path)
        preprocessed_path = str(p.parent / f"{p.stem}_preprocessed{p.suffix}")
        img.save(preprocessed_path)
        logger.info("Preprocessed image saved to %s", preprocessed_path)
        return preprocessed_path

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------
    @classmethod
    def extract_text(cls, image_path: str) -> str:
        """Run EasyOCR on *image_path* and return the full text."""
        reader = cls._get_reader()
        results = reader.readtext(image_path, detail=0)
        text = "\n".join(results)
        logger.info("Extracted %d characters from %s", len(text), image_path)
        return text

    # ------------------------------------------------------------------
    # Amount extraction
    # ------------------------------------------------------------------
    @staticmethod
    def extract_amount(text: str) -> Optional[float]:
        """
        Extract the most likely total dollar amount from receipt text.

        Looks for patterns like ``$12.99``, ``12.99``, ``1,234.56``,
        or amounts prefixed by ``total:``.  Returns the **largest** match
        (receipts usually show line items then a grand total).
        """
        if not text:
            return None

        amounts = []

        # Pattern: optional $ sign, digits with optional comma grouping, decimal
        general_pattern = r"\$?\s?(\d{1,3}(?:,\d{3})*\.\d{2})"
        for match in re.finditer(general_pattern, text):
            raw = match.group(1).replace(",", "")
            amounts.append(float(raw))

        # Pattern: "total" keyword followed by an amount (case-insensitive)
        total_pattern = r"(?i)total\s*:?\s*\$?\s?(\d{1,3}(?:,\d{3})*\.\d{2})"
        for match in re.finditer(total_pattern, text):
            raw = match.group(1).replace(",", "")
            amounts.append(float(raw))

        if not amounts:
            return None

        return max(amounts)

    # ------------------------------------------------------------------
    # Merchant extraction
    # ------------------------------------------------------------------
    @staticmethod
    def extract_merchant(text: str) -> Optional[str]:
        """
        Heuristic: the first non-empty line of a receipt is usually the
        merchant / store name.
        """
        if not text:
            return None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return None
