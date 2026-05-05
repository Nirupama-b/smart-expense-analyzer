"""Single source of truth for expense category names.

These match the rows seeded by `migrations/001_initial_schema.sql`.
Both the NLP zero-shot classifier and the expenses router import this
list so OCR-categorized receipts always resolve to a real category_id.
"""

CATEGORIES: list[str] = [
    "Groceries",
    "Dining",
    "Transport",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Education",
    "Travel",
    "Other",
]
