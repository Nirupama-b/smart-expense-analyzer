"""Tests for the regex-based field extractors in OCRService.

These tests deliberately exercise only the pure-Python helpers
(`extract_amount`, `extract_merchant`) so they run without the
EasyOCR model weights or any image I/O.
"""

import sys
from pathlib import Path

# Ensure `services/...` resolves when running pytest from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ocr_service import OCRService  # noqa: E402


class TestExtractAmount:
    def test_returns_none_for_empty_text(self):
        assert OCRService.extract_amount("") is None
        assert OCRService.extract_amount(None) is None

    def test_returns_none_when_no_amounts_present(self):
        assert OCRService.extract_amount("Thank you for shopping") is None

    def test_extracts_simple_dollar_amount(self):
        assert OCRService.extract_amount("Coffee $4.50") == 4.50

    def test_extracts_amount_without_dollar_sign(self):
        assert OCRService.extract_amount("Subtotal 12.99") == 12.99

    def test_picks_largest_when_multiple_amounts(self):
        # Receipts list line items then a grand total — the total is the max.
        text = "Latte 4.50\nMuffin 3.25\nTotal: $7.75"
        assert OCRService.extract_amount(text) == 7.75

    def test_handles_comma_grouped_thousands(self):
        assert OCRService.extract_amount("Grand Total $1,234.56") == 1234.56

    def test_total_keyword_is_case_insensitive(self):
        assert OCRService.extract_amount("TOTAL: 19.95") == 19.95

    def test_ignores_integers_without_decimals(self):
        # Phone numbers / store IDs shouldn't be picked up.
        assert OCRService.extract_amount("Store 12345 phone 5551234") is None


class TestExtractMerchant:
    def test_returns_none_for_empty_text(self):
        assert OCRService.extract_merchant("") is None
        assert OCRService.extract_merchant(None) is None

    def test_returns_first_non_empty_line(self):
        text = "WHOLE FOODS MARKET\n123 Main St\nTotal: $42.10"
        assert OCRService.extract_merchant(text) == "WHOLE FOODS MARKET"

    def test_skips_leading_blank_lines(self):
        text = "\n\n   \nTrader Joe's\nReceipt"
        assert OCRService.extract_merchant(text) == "Trader Joe's"

    def test_strips_surrounding_whitespace(self):
        assert OCRService.extract_merchant("   Starbucks   \nMore text") == "Starbucks"
