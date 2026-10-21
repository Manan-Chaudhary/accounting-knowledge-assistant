# LLM Backend Candidates (Free-Tier, via LiteLLM)

## 1. Why this exists

Checklist item: "[LLM BACKEND] - Research best free LLM candidates from LiteLLM model catalog." This document narrows the field for the empirical bake-off the `/testing` page is designed to run (see [`TESTING-PAGE-REQUIREMENTS.md`](TESTING-PAGE-REQUIREMENTS.md); results are in `benchmarks/reports/` and [`model_evaluation_report.md`](model_evaluation_report.md), not in an `EvalResult` table, which is never written). It answers the "Generation model" row of the open-decisions table in [`RAG-DESIGN.md`](RAG-DESIGN.md) section 8.

**Implementation Status:** built. `app/rag/generator.py` calls a LiteLLM proxy (a Docker Compose service on port 4000) through the OpenAI-compatible SDK (`OpenAI` / `AsyncOpenAI`, base URL from `LITELLM_API_BASE`, key from `LITELLM_API_KEY` or `LITELLM_MASTER_KEY`), not the `litellm` Python package directly. `litellm/config.yaml` defines four aliases: `gemini-3-8-flash` (`gemini/gemini-3.8-flash`, the default), `groq-gpt-oss-120b`, `openrouter-free` and `free-fallback` (an OpenRouter free model), with fallbacks `gemini-3-8-flash` to `openrouter-free` to `free-fallback`. Cerebras, Mistral, Cohere, GitHub Models and Ollama were researched here but never wired in. The table below is research written before the config and is not updated; it still says `gemini-2.5-flash` where the config uses `gemini-3.8-flash`.

## 2. Constraints this research is scored against

- **Latency:** P95 end-to-end ≤ 8s ([`EVALUATION.md`](EVALUATION.md) section 4, latency row). The agentic multi-hop loop in [`RAG-DESIGN.md`](RAG-DESIGN.md) was never built, so each answer is a single retrieval and a single generation call. Measured P95 is far above 8s on every model tried (see `benchmarks/reports/`).
- **No-training / data-residency:** [`RAG-DESIGN.md`](RAG-DESIGN.md) section 8 states the generation model "must have contractual no-training terms" and calls this "a proposal-level commitment, not a code choice."
- **Cost visibility, free-tier-first:** established pattern in this repo - BGE-M3 embeddings chosen explicitly over OpenAI on cost ([`DATABASE.md`](DATABASE.md), "Why BGE-M3?"), Supabase free tier chosen deliberately, `cost_usd` tracked per query in the `eval_results` schema.
- **Context budget:** no hard ceiling is documented. Retrieval returns the top 5 reranked chunks in the chat route (top 6 in the evaluation harness), each about 1200 characters plus a long, constraint-heavy system prompt plus multi-turn history ([`CHAT-SESSION-REQUIREMENTS.md`](CHAT-SESSION-REQUIREMENTS.md) SS-27, marked `[ASSUMED]`). A few thousand tokens of headroom beyond that is the practical minimum; more is better given the multi-hop design.
- **Domain fit:** SMSF compliance content for a technical accountant audience, strict corpus-separation and citation-or-no-claim rules baked into the system prompt - favors models with strong instruction-following and reliable JSON/function-calling output over raw benchmark scores.

## 3. Candidates evaluated

| Provider | LiteLLM model string | Free tier limits | Context window | RAG / tool-call fit | Latency | Verdict |
|---|---|---|---|---|---|---|
| **Groq** | `groq/openai/gpt-oss-120b` | ~30 RPM / 6-8K TPM / 1,000 RPD, org-level | 131K | Function calling, JSON mode, streaming all supported in LiteLLM | Fastest of all candidates - custom LPU hardware, typically sub-second TTFT | **Primary candidate.** Available as the `groq-gpt-oss-120b` alias; the app default is Gemini (`LITELLM_MODEL`, `gemini-3-8-flash` in the UI). |
| **Google Gemini (AI Studio)** | `gemini/gemini-2.5-flash` | 15 RPM / 1,500 RPD / 1M TPM | 1,000,000 | Function calling, JSON mode, streaming, context caching all supported | Fast, not as fast as Groq's LPU | **Primary candidate**, with a caveat - see section 4. Configured as `gemini-3-8-flash` on `gemini/gemini-3.8-flash`, the default alias. |
| **Cerebras** | `cerebras/gpt-oss-120b` | 1M tokens/day, ~30 RPM, 14.4K RPD | **8K on the free tier only** | Same open weights as Groq's copy of gpt-oss-120b; function calling support via LiteLLM not clearly documented | Fastest raw tokens/sec of any candidate | Conditional. 8K context is a real risk once retrieved chunks + system prompt + history are added up - only worth adopting if that's empirically proven sufficient. |
| **OpenRouter** | `openrouter/<model>:free` | ~20 req/min, 50-1,000 req/day depending on prepaid credit; free catalog rotates week to week | Varies by underlying model (some up to 1M) | Depends entirely on which free model is live | Depends entirely on which free model is live | Not a production default - catalog isn't stable enough. Useful as the harness for the `/testing` page's side-by-side comparison, since one API key reaches many free models. |
| **Mistral (La Plateforme)** | `mistral/mistral-large-latest` | Free "Experiment" tier existed; a September 2026 pricing change removed the published free API allowance and folded it into paid credit | N/A | N/A | N/A | Deprioritize - terms are currently unstable/unpublished. |
| **Cohere** | `cohere/command-r-plus` | Trial key: 1,000 calls/month, 20 RPM. **Trial ToS explicitly excludes production/commercial use.** | 128K | Best-in-class native RAG with inline citations - closest functional match to this project's citation-first requirement | Adequate | Sandbox/eval only. The trial terms disqualify it for the actual firm-facing product, but its citation approach is worth studying when building citation validation in `generator.py`. |
| **GitHub Models** | `github/<model>` | Free with a GitHub PAT; per-model/tier rate limits, resets daily UTC | Up to 131K depending on model | Reasonable | Reasonable | Dev/CI testing only - tied to individual GitHub accounts, not clearly licensed for firm-facing production use. |
| **Ollama (self-hosted)** | `ollama/<model>` | No API cost, but the team hosts the inference compute | Model-dependent | Model-dependent | Bound by whatever hardware runs it - real risk without a GPU host | Not proposed as a first choice - there's no GPU hosting in this project today (Docker Compose + Supabase only). Worth a spike only if data-residency becomes a hard blocker on the hosted options, since self-hosting trivially satisfies "no training." |

## 4. Flag: no-training requirement vs. current Gemini usage

[`RAG-DESIGN.md`](RAG-DESIGN.md) section 8 requires contractual no-training terms for the generation model. Google's own AI Studio free-tier documentation states that free-tier inputs/outputs may be used to improve Google's models - this conflicts with that requirement as written. Two ways to resolve it:

- Move Gemini calls to **Vertex AI** (paid, contractually no-training) once the project has a billing path, keeping AI Studio's free `gemini-2.5-flash` as dev/eval only, or
- Treat `gemini-2.5-flash` via AI Studio as a dev/eval-phase model only, and confirm a no-training-compliant option before anything client-facing ships.

Groq's own data-use terms for its free tier were not confirmed during this research and should be checked directly against Groq's terms of service before treating `gpt-oss-120b` as satisfying the no-training requirement for production.

## 5. Recommendation for the testing/bake-off phase

Shortlist to wire through LiteLLM for the `/testing` page's multi-model comparison:

1. `groq/openai/gpt-oss-120b` - fast, ample context.
2. Gemini (the config uses `gemini/gemini-3.8-flash`) - largest context by far; confirm the no-training caveat in section 4 before using it beyond eval.
3. One rotating `openrouter` free entry - gives a third, independent data point without committing to a specific model that may not stay free.

What actually happened: the comparison that was run used three Groq models (gpt-oss-120b, qwen3.8-27b, gpt-oss-20b), not this shortlist, and no Gemini versus Groq comparison was completed ([`model_evaluation_report.md`](model_evaluation_report.md)). The no-training question in section 4 is still unresolved.

Do not add Cohere's trial key or unauthenticated GitHub Models to the production shortlist. Keep them only as reference points - Cohere for its citation approach, GitHub Models for quick dev-time comparisons.

## 6. What this document does not decide

Per [`RAG-DESIGN.md`](RAG-DESIGN.md) section 8's own instruction ("Do not assume; measure"), the actual generation model should be settled by running the three shortlisted candidates against the SMSF eval set through the `EvalResult` scorers (correctness, citation validity, latency, cost per query) (both now exist). This document narrows the field; it does not pick a winner, and neither has any evaluation so far.

## Sources

- [LiteLLM supported providers](https://docs.litellm.ai/docs/providers)
- [LiteLLM Groq provider docs](https://docs.litellm.ai/docs/providers/groq)
- [LiteLLM Gemini provider docs](https://docs.litellm.ai/docs/providers/gemini)
- [LiteLLM OpenRouter provider docs](https://docs.litellm.ai/docs/providers/openrouter)
- [Groq API Free Tier Limits in 2026](https://www.grizzlypeaksoftware.com/articles/p/groq-api-free-tier-limits-in-2026-what-you-actually-get-uwysd6mb)
- [Groq Free Tier 2026: 1,000 Requests a Day](https://klymentiev.com/blog/groq-pricing)
- [Gemini API Rate Limits 2026](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Google AI Studio Free Tier: Models, Rate Limits & Pricing 2026](https://turion.ai/blog/google-ai-studio-2026-features-guide/)
- [OpenRouter Free Models](https://openrouter.ai/openrouter/free)
- [OpenRouter Free Tier 2026: Rate Limits, Free Models Tested](https://klymentiev.com/blog/openrouter-free-tier)
- [Cerebras Free Tier: 1M Tokens/Day, API Limits](https://adam.holter.com/cerebras-opens-a-free-1m-tokens-per-day-inference-tier-and-ccerebras-now-offers-free-inference-with-1m-tokens-per-day-real-speed-benchmarks-show-2600-tokens-sec-on-llama4scout-here-are-the-actual-n/)
- [Cerebras Rate Limits docs](https://inference-docs.cerebras.ai/support/rate-limits)
- [Mistral AI Free Tier 2026: Limits, Pricing & What Changed](https://agentdeals.dev/vendor/mistral-ai)
- [Cohere Free API: 1000 Calls/Month Trial Guide (2026)](https://aicreditmart.com/ai-credits-providers/cohere-free-api-1000-calls-month-trial-guide-2026/)
- [Cohere Review 2026: Command R+, Pricing & Enterprise RAG](https://aiagentsquare.com/agents/cohere)
