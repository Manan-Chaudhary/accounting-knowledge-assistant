"""
scripts/verify_grounding_rules.py
Verifies the Grounding Gate across three mandatory criteria:
1. Answered: Valid SMSF factual question with citations.
2. Unanswerable: Obscure query with 0 retrieved chunks.
3. Declined: Personal financial advice query.
"""

from dataclasses import dataclass
from app.rag.grounding import (
    evaluate_grounding_gate,
    verify_and_clean_citations,
    MIN_RETRIEVED_CHUNKS,
)

@dataclass
class MockChunk:
    id: int
    content: str
    filename: str

def run_tests():
    print("=" * 60)
    print("RUNNING GROUNDING GATE VERIFICATION")
    print("=" * 60)

    # Case 1: Declined (Personal Financial Advice)
    q1 = "Should I invest all my SMSF money into residential property in Melbourne?"
    gate1 = evaluate_grounding_gate(q1, [MockChunk(1, "text", "doc.pdf")])
    print("\n[Case 1: Declined (Personal Advice)]")
    print(f"Query: {q1}")
    print(f"Gate Triggered: {gate1['status']} ({gate1['reason']})")
    print(f"Output: {gate1['output']}")
    assert gate1["status"] == "declined"

    # Case 2: Unanswerable (0 Chunks Retrieved)
    q2 = "What are the rules for quantum computing grants in Australia under SIS Act?"
    gate2 = evaluate_grounding_gate(q2, [])
    print("\n[Case 2: Unanswerable (No Retrieved Chunks)]")
    print(f"Query: {q2}")
    print(f"Gate Triggered: {gate2['status']} ({gate2['reason']})")
    print(f"Output: {gate2['output']}")
    assert gate2["status"] == "unanswerable"

    # Case 3: Answered + Citation Verification
    q3 = "What is the sole purpose test under SIS Act?"
    mock_chunks = [
        MockChunk(1, "Sole purpose test under Section 62...", "sis-act.pdf"),
        MockChunk(2, "ATO guidance on investment rules...", "ato-guide.txt"),
    ]
    gate3 = evaluate_grounding_gate(q3, mock_chunks)
    print("\n[Case 3: Answered (Passed Grounding Gate)]")
    print(f"Query: {q3}")
    print(f"Gate Status: {'PASSED' if gate3 is None else 'BLOCKED'}")
    assert gate3 is None

    # Test Citation Verification with a Hallucinated Citation [3]
    raw_response = (
        "Under Section 62, the fund must be maintained for retirement [1]. "
        "ATO requires compliance [2], but imaginary rules apply [3]."
    )
    cleaned, valid, invalid = verify_and_clean_citations(raw_response, len(mock_chunks))
    print(f"Raw Output: {raw_response}")
    print(f"Cleaned Output: {cleaned}")
    print(f"Valid Citations: {valid}, Invalid Citations: {invalid}")
    assert invalid == [3]

    print("\n" + "=" * 60)
    print("ALL 3 CASES PASSED GROUNDING GATE CRITERIA")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()