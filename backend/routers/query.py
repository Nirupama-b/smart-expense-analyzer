import logging
import re
from collections import defaultdict
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import create_client

from config import get_settings
from middleware.auth import get_current_user
from models.schemas import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


def _get_admin_supabase():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _fetch_user_expenses(user_id: str):
    """Fetch all expenses for a user (used as context for answering)."""
    supabase = _get_admin_supabase()
    try:
        res = (
            supabase.table("expenses")
            .select("*, categories(name)")
            .eq("user_id", user_id)
            .order("date", desc=True)
            .limit(500)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        logger.error("Failed to fetch expenses for query: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Rule-based fallback handler
# ---------------------------------------------------------------------------

def _rule_based_answer(question: str, expenses: list[dict]) -> QueryResponse:
    """Handle common queries without LLM using keyword matching."""

    q = question.lower().strip()

    # Normalise category names from joined rows
    for exp in expenses:
        if exp.get("categories") and isinstance(exp["categories"], dict):
            exp["_cat"] = exp["categories"].get("name", "Other")
        else:
            exp["_cat"] = "Other"

    amounts = [float(e.get("amount", 0)) for e in expenses]
    total = sum(amounts)

    # --- total / sum queries ---
    if any(kw in q for kw in ["total", "sum", "how much", "all expenses", "overall"]):
        # Check for category-specific totals
        for exp in expenses:
            cat = exp["_cat"].lower()
            if cat in q:
                cat_total = sum(
                    float(e.get("amount", 0))
                    for e in expenses
                    if e["_cat"].lower() == cat
                )
                return QueryResponse(
                    answer=f"Your total spending on {exp['_cat']} is ${cat_total:,.2f}.",
                    data={"category": exp["_cat"], "total": round(cat_total, 2)},
                )

        return QueryResponse(
            answer=f"Your total spending across all expenses is ${total:,.2f} ({len(expenses)} expenses).",
            data={"total": round(total, 2), "count": len(expenses)},
        )

    # --- category breakdown ---
    if any(kw in q for kw in ["categor", "breakdown", "by category", "spending by"]):
        cat_totals: dict[str, float] = defaultdict(float)
        for e in expenses:
            cat_totals[e["_cat"]] += float(e.get("amount", 0))
        sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
        lines = [f"  - {cat}: ${amt:,.2f}" for cat, amt in sorted_cats]
        answer_text = "Here is your spending by category:\n" + "\n".join(lines)
        return QueryResponse(
            answer=answer_text,
            data={"categories": {cat: round(amt, 2) for cat, amt in sorted_cats}},
        )

    # --- average ---
    if any(kw in q for kw in ["average", "avg", "mean"]):
        avg = total / len(amounts) if amounts else 0
        return QueryResponse(
            answer=f"Your average expense is ${avg:,.2f} (across {len(expenses)} expenses).",
            data={"average": round(avg, 2), "count": len(expenses)},
        )

    # --- largest / most expensive ---
    if any(kw in q for kw in ["largest", "biggest", "most expensive", "highest", "max"]):
        if not expenses:
            return QueryResponse(answer="You have no expenses recorded.", data=None)
        top = max(expenses, key=lambda e: float(e.get("amount", 0)))
        return QueryResponse(
            answer=(
                f"Your largest expense is ${float(top.get('amount', 0)):,.2f}"
                f" at {top.get('merchant', 'Unknown')} on {top.get('date', 'N/A')}."
            ),
            data={
                "amount": float(top.get("amount", 0)),
                "merchant": top.get("merchant"),
                "date": top.get("date"),
            },
        )

    # --- smallest / cheapest ---
    if any(kw in q for kw in ["smallest", "cheapest", "least expensive", "lowest", "min"]):
        if not expenses:
            return QueryResponse(answer="You have no expenses recorded.", data=None)
        bottom = min(expenses, key=lambda e: float(e.get("amount", 0)))
        return QueryResponse(
            answer=(
                f"Your smallest expense is ${float(bottom.get('amount', 0)):,.2f}"
                f" at {bottom.get('merchant', 'Unknown')} on {bottom.get('date', 'N/A')}."
            ),
            data={
                "amount": float(bottom.get("amount", 0)),
                "merchant": bottom.get("merchant"),
                "date": bottom.get("date"),
            },
        )

    # --- recent ---
    if any(kw in q for kw in ["recent", "latest", "last"]):
        count_match = re.search(r"(\d+)", q)
        n = int(count_match.group(1)) if count_match else 5
        recent = expenses[:n]
        lines = [
            f"  - ${float(e.get('amount', 0)):,.2f} at {e.get('merchant', 'Unknown')} ({e.get('date', 'N/A')})"
            for e in recent
        ]
        return QueryResponse(
            answer=f"Your {len(recent)} most recent expenses:\n" + "\n".join(lines),
            data={"expenses": recent[:n]},
        )

    # --- count ---
    if any(kw in q for kw in ["how many", "count", "number of"]):
        return QueryResponse(
            answer=f"You have {len(expenses)} expenses recorded.",
            data={"count": len(expenses)},
        )

    # Fallback
    return QueryResponse(
        answer=(
            f"I found {len(expenses)} expenses totaling ${total:,.2f}. "
            "Could you rephrase your question? I can help with totals, "
            "averages, category breakdowns, largest/smallest expenses, and recent transactions."
        ),
        data={"total": round(total, 2), "count": len(expenses)},
    )


# ---------------------------------------------------------------------------
# LangChain-powered answer (best effort)
# ---------------------------------------------------------------------------

def _try_langchain_answer(
    question: str, expenses: list[dict]
) -> Optional[QueryResponse]:
    """Attempt to use LangChain for a richer answer. Returns None on failure."""
    try:
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        from langchain_community.llms import HuggingFacePipeline

        # Build a concise expense summary as context
        summary_lines = []
        for e in expenses[:50]:  # cap context size
            cat = "Other"
            if e.get("categories") and isinstance(e["categories"], dict):
                cat = e["categories"].get("name", "Other")
            summary_lines.append(
                f"${float(e.get('amount', 0)):.2f} | {e.get('merchant', 'Unknown')} | "
                f"{cat} | {e.get('date', 'N/A')}"
            )

        context = "\n".join(summary_lines)

        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=(
                "You are a helpful financial assistant. Based on the following expense records, "
                "answer the user's question concisely.\n\n"
                "Expenses (Amount | Merchant | Category | Date):\n{context}\n\n"
                "Question: {question}\n"
                "Answer:"
            ),
        )

        llm = HuggingFacePipeline.from_model_id(
            model_id="distilgpt2",
            task="text-generation",
            pipeline_kwargs={"max_new_tokens": 200},
        )

        chain = LLMChain(llm=llm, prompt=prompt)
        result = chain.run(context=context, question=question)

        return QueryResponse(answer=result.strip(), data=None)

    except Exception as exc:
        logger.warning("LangChain answer failed, falling back to rules: %s", exc)
        return None


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------
@router.post("/", response_model=QueryResponse)
async def natural_language_query(
    payload: QueryRequest,
    user_id: str = Depends(get_current_user),
):
    """Answer a natural-language question about the user's expenses."""

    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )

    expenses = _fetch_user_expenses(user_id)

    if not expenses:
        return QueryResponse(
            answer="You don't have any expenses yet. Start by uploading a receipt or adding an expense.",
            data=None,
        )

    # Try LangChain first
    lc_result = _try_langchain_answer(payload.question, expenses)
    if lc_result is not None:
        return lc_result

    # Fall back to rule-based handler
    return _rule_based_answer(payload.question, expenses)
