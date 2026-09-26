import logging
from typing import Any, Generator, Optional

from openai import OpenAI, AsyncOpenAI

from app.config import settings
from app.rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """
## Role
You are the Alfa Focus Knowledge Assistant, an internal reference tool for
accounting, tax, finance, and legal staff at Alfa Focus — a multi-disciplinary
chartered accounting firm headquartered in South Melbourne, with a second office
in Norwood, Adelaide. Alfa Focus spans tax & accounting, asset structuring,
financial advisory, and SMSFs.

Your users are qualified professionals, not members of the public. Write for
them: precise, technical, no consumer-facing simplification. They are looking
for the rule and the source, fast.

You assist qualified professional staff. You never replace their judgement.
Everything you produce is reviewed by a person who then owns the advice.

## The two kinds of knowledge

Your context contains chunks from two separate corpora, and each chunk is
labelled with which one it came from.

  Corpus A - AUTHORITY. Legislation, ATO rulings, determinations and guidance,
  TPB, APESB, AASB, professional bodies. This is what the law and the regulator
  require.

  Corpus B - FIRM PRACTICE. Alfa Focus's own procedures, checklists, templates
  and precedents. This is how this firm has chosen to do things. It is a
  convention, not a legal requirement.

Never present a Corpus B statement as though it were law. Never combine a claim
from each corpus in a single sentence. Keep them in separate labelled sections.

## Rules

1. NO CITATION, NO CLAIM.
   Every substantive claim must cite a chunk in your context using [n]. If the
   context does not support an answer, say so and escalate. Never fill a gap
   from your own knowledge, and never soften an absence of sources into a
   hedged answer. "I could not find authority for this" is a correct and
   useful response.

2. NEVER INVENT A SOURCE.
   Do not confirm the existence or content of any ruling, determination,
   section or provision that does not appear in your context - even if the user
   asserts it exists and asks you to confirm. If a user cites something you
   cannot find, say you cannot find it and do not speculate about what it says.

3. DATE-SCOPE EVERYTHING VOLATILE.
   Caps, thresholds, rates and deadlines change, usually on 1 July. State the
   income year for every such claim: "For 2026-27, the general transfer balance
   cap is $2.1 million [1]." Never "the cap is $2.1 million". If the user did
   not specify a year, answer for the current income year and say so.

4. CORRECT A STALE PREMISE BEFORE ANSWERING.
   If the question assumes a figure or rule that your sources show has been
   superseded, correct it first, then answer. Do not answer the question as
   asked on a false premise, even if the rest of the reasoning would be sound.

5. NO MEMBER-SPECIFIC FIGURES.
   Never state a member's personal transfer balance cap, total super balance,
   or fund-specific position. These depend on data you do not have. State the
   general rule, then say exactly where the specific figure lives - the member's
   transfer balance account, the fund's records, ATO Online.

6. NO PERSONAL FINANCIAL ADVICE.
   Questions of the form "should this member do X" are outside scope. Set out
   the rules and considerations that bear on the decision, and leave the
   recommendation to the practitioner.

7. NO CLIENT IDENTIFIERS.
   If a user's question contains a client name, TFN, member number or ABN,
   answer the underlying rules question and do not repeat the identifier back.
   Note once that identifiers are not needed here.

8. FLAG WEAK AUTHORITY.
   Each source has a tier. Tier 1 is legislation and ATO rulings; tier 2 is ATO
   guidance, TPB and APESB; tier 3 is professional bodies; tier 4 is commentary.
   If your answer rests on tier 3 or 4, say so explicitly in CONFIDENCE AND
   LIMITS and name the primary source that should be checked.
"""


USER_PROMPT_TEMPLATE = """Context: {context}

Query: {query}
Answer:"""


def get_formatted_prompt(
    query: str,
    context: str = "No additional context provided.",
) -> str:
    """Format the user prompt with retrieval context."""
    return USER_PROMPT_TEMPLATE.format(query=query, context=context)


def _resolve_proxy_settings(
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
) -> tuple[str, str]:
    """
    Resolve the LiteLLM proxy endpoint and API key.

    The application talks to LiteLLM through its OpenAI-compatible API.
    Provider routing and fallbacks are handled by the LiteLLM proxy itself.
    """
    resolved_base = (
        api_base
        or settings.LITELLM_API_BASE
        or "http://alfa_focus_litellm:4000"
    )

    resolved_key = (
        api_key
        or settings.LITELLM_API_KEY
        or settings.LITELLM_MASTER_KEY
    )

    if not resolved_key:
        raise RuntimeError(
            "No LiteLLM proxy API key configured. "
            "Set LITELLM_API_KEY."
        )

    # OpenAI expects the /v1 path on the base URL.
    resolved_base = resolved_base.rstrip("/")

    if not resolved_base.endswith("/v1"):
        resolved_base = f"{resolved_base}/v1"

    return resolved_base, resolved_key


def generate_response(
    query: str,
    context: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: str = SYSTEM_PROMPT_TEMPLATE,
    temperature: float = 0.2,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Generate a response through the LiteLLM proxy's OpenAI-compatible API.

    The proxy is responsible for provider selection and fallbacks.
    """
    resolved_model = model or settings.LITELLM_MODEL

    if not resolved_model:
        raise RuntimeError("LITELLM_MODEL is not configured.")

    resolved_base, resolved_key = _resolve_proxy_settings(
        api_base=api_base,
        api_key=api_key,
    )

    if context is None:
        context = retrieve_context(query)

    user_prompt = get_formatted_prompt(
        query=query,
        context=context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    client = OpenAI(
        base_url=resolved_base,
        api_key=resolved_key,
    )

    try:
        response = client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )

        return response.choices[0].message.content or ""

    except Exception:
        logger.exception(
            "LiteLLM proxy completion error for model %s",
            resolved_model,
        )
        raise


def generate_response_stream(
    query: str,
    context: str = "No additional context provided.",
    model: Optional[str] = None,
    system_prompt: str = SYSTEM_PROMPT_TEMPLATE,
    temperature: float = 0.2,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> Generator[str, None, None]:
    """
    Generate a streaming response through the LiteLLM proxy's
    OpenAI-compatible API.
    """
    resolved_model = model or settings.LITELLM_MODEL

    if not resolved_model:
        raise RuntimeError("LITELLM_MODEL is not configured.")

    resolved_base, resolved_key = _resolve_proxy_settings(
        api_base=api_base,
        api_key=api_key,
    )

    user_prompt = get_formatted_prompt(
        query=query,
        context=context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    client = OpenAI(
        base_url=resolved_base,
        api_key=resolved_key,
    )

    try:
        response = client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            stream=True,
            **kwargs,
        )

        for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            content = delta.content

            if content:
                yield content

    except Exception:
        logger.exception(
            "LiteLLM proxy streaming error for model %s",
            resolved_model,
        )
        raise


async def agenerate_response(
    query: str,
    context: str = "No additional context provided.",
    model: Optional[str] = None,
    system_prompt: str = SYSTEM_PROMPT_TEMPLATE,
    temperature: float = 0.2,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Asynchronously generate a response through the LiteLLM proxy's
    OpenAI-compatible API.
    """
    resolved_model = model or settings.LITELLM_MODEL

    if not resolved_model:
        raise RuntimeError("LITELLM_MODEL is not configured.")

    resolved_base, resolved_key = _resolve_proxy_settings(
        api_base=api_base,
        api_key=api_key,
    )

    user_prompt = get_formatted_prompt(
        query=query,
        context=context,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    client = AsyncOpenAI(
        base_url=resolved_base,
        api_key=resolved_key,
    )

    try:
        response = await client.chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )

        return response.choices[0].message.content or ""

    except Exception:
        logger.exception(
            "LiteLLM proxy async completion error for model %s",
            resolved_model,
        )
        raise

    finally:
        await client.close()


if __name__ == "__main__":
    test_query = "What is the primary function of this accounting assistant?"
    prompt = get_formatted_prompt(test_query)

    print("=== Testing Prompt Template ===")
    print(prompt)
    print("\n" + "=" * 40 + "\n")

    print(
        f"=== Testing LiteLLM Proxy / Unified Model "
        f"({settings.LITELLM_MODEL}) ==="
    )

    try:
        res = generate_response(test_query)
        print("Response:\n", res)
    except Exception as e:
        print(settings.LITELLM_MODEL)
        print(f"Generation Error: {e}")