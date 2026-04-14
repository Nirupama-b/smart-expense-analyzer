"""
NLP categorization service using zero-shot classification (facebook/bart-large-mnli).
"""

import logging

logger = logging.getLogger(__name__)

CATEGORIES = [
    "Groceries",
    "Dining",
    "Transportation",
    "Entertainment",
    "Shopping",
    "Healthcare",
    "Utilities",
    "Travel",
    "Education",
    "Other",
]

# The 9 "real" categories sent to the classifier — "Other" is a fallback.
_CANDIDATE_LABELS = [c for c in CATEGORIES if c != "Other"]


class NLPCategorizationService:
    """Zero-shot receipt text categorization."""

    # Lazy class-level singleton pipeline
    _pipeline = None

    @classmethod
    def _get_pipeline(cls):
        """Return a lazily-initialised zero-shot-classification pipeline."""
        if cls._pipeline is None:
            from transformers import pipeline

            cls._pipeline = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1,  # Force CPU to avoid MPS crashes in forked workers
            )
            logger.info("Loaded zero-shot-classification pipeline")
        return cls._pipeline

    @classmethod
    def categorize(cls, text: str):
        """
        Classify *text* into one of the expense categories.

        Returns:
            (category, confidence)  where confidence is between 0 and 1.
            Falls back to ("Other", <score>) when the top score is below 0.5.
        """
        if not text or not text.strip():
            return ("Other", 0.0)

        pipe = cls._get_pipeline()
        result = pipe(text, candidate_labels=_CANDIDATE_LABELS)

        top_label = result["labels"][0]
        top_score = result["scores"][0]

        if top_score < 0.5:
            return ("Other", top_score)

        return (top_label, top_score)
