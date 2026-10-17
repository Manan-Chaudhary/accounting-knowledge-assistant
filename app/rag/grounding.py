import re
from typing import Any, Dict, List, Optional, Tuple

# --- Configurable Thresholds & Standard Copy ---------------------------------

# Minimum number of chunks required to attempt an answer
MIN_RETRIEVED_CHUNKS = 1

# Approved refusal copy when context does not support the query (Rules 1 & 2)
UNANSWERABLE_REFUSAL_MESSAGE = (
    "I could not find authority or relevant document chunks in the approved context "
    "to answer this query. Please escalate this matter to a qualified practitioner "
    "or refer directly to primary legislation."
)

# Approved refusal copy for personal financial advice queries (Rule 6)
PERSONAL_ADVICE_REFUSAL_MESSAGE = (
    "Under Alfa Focus compliance guidelines and statutory requirements, I cannot provide "
    "personal financial, tax, or investment advice (such as recommending specific actions "
    "for an individual or fund). I can only outline the governing rules and compliance "
    "considerations."
)

# Regex patterns identifying personal financial / directive advice queries
PERSONAL_ADVICE_PATTERNS = [
    r"\bshould\s+(i|we|my\s+client|the\s+member|the\s+trustee)\b",
    r"\bis\s+it\s+(advisable|best|recommended)\s+for\s+(me|my\s+client|the\s+member)\b",
    r"\bwhat\s+should\s+(i|the\s+member)\s+invest\s+in\b",
    r"\bcan\s+i\s+put\s+all\s+(my|the)\s+money\b",
]


def is_personal_advice_query(query: str) -> bool:
    """Detect whether a query asks for personal financial advice."""
    q_lower = query.strip().lower()
    return any(re.search(pattern, q_lower) for pattern in PERSONAL_ADVICE_PATTERNS)


def verify_and_clean_citations(
    answer: str,
    retrieved_chunk_count: int,
) -> Tuple[str, List[int], List[int]]:
    """
    Check citations [n] in the answer text against the actual retrieved chunks.
    Valid range: 1 <= n <= retrieved_chunk_count.
    Unmatched citations are replaced with '[unverified citation: n]' or flagged.
    """
    valid_citations: List[int] = []
    invalid_citations: List[int] = []

    def replace_citation(match: re.Match) -> str:
        idx_str = match.group(1)
        try:
            idx = int(idx_str)
            if 1 <= idx <= retrieved_chunk_count:
                if idx not in valid_citations:
                    valid_citations.append(idx)
                return match.group(0)  # Keep valid citation
            else:
                if idx not in invalid_citations:
                    invalid_citations.append(idx)
                return f"[unverified citation: {idx}]"
        except ValueError:
            return match.group(0)

    # Match patterns like [1], [2], [12]
    cleaned_answer = re.sub(r"\[(\d+)\]", replace_citation, answer)
    return cleaned_answer, sorted(valid_citations), sorted(invalid_citations)


def evaluate_grounding_gate(
    query: str,
    retrieved_chunks: List[Any],
) -> Optional[Dict[str, Any]]:
    """
    Pre-generation evaluation gate.
    Returns a refusal payload if blocked, or None if safe to proceed to LLM.
    """
    # 1. Check Personal Financial Advice Gate
    if is_personal_advice_query(query):
        return {
            "status": "declined",
            "reason": "personal_advice",
            "output": PERSONAL_ADVICE_REFUSAL_MESSAGE,
            "sources": [],
        }

    # 2. Check Retrieval / Grounding Threshold Gate
    if len(retrieved_chunks) < MIN_RETRIEVED_CHUNKS:
        return {
            "status": "unanswerable",
            "reason": "no_grounding_context",
            "output": UNANSWERABLE_REFUSAL_MESSAGE,
            "sources": [],
        }

    return None