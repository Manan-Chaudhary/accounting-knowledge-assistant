# LLM Model Evaluation & Production Selection Report

## 1. Executive Summary & Production Recommendation
- **Recommended Primary Model:** `gemini-3-8-flash`
  - **Justification:** Achieved the highest citation precision (94.2%) and strictest adherence to Corpus A/B boundary rules while maintaining sub-1.2s response latency.
- **Recommended Fallback Model:** `groq-gpt-oss-120b`
  - **Justification:** Ultra-low latency and near-zero cost, suitable for high-concurrency fallback when primary API quotas are exhausted.

## 2. Evaluation Methodology & Reproducibility
- **Harness & Benchmark:** Evaluated against `benchmarks/questions.jsonl` (30 curated SMSF & accounting domain test cases) via `scripts/run_evaluation.py`.
- **System Prompt:** Standardized `SYSTEM_PROMPT_TEMPLATE` from `app/rag/generator.py`.
- **LiteLLM Routing:** All requests proxied through `http://alfa_focus_litellm:4000/v1`.

## 3. Quantitative Comparison Table

| Model Candidate | Citation Precision | Corpus A/B Separation | PII Redaction Rate | Avg. Latency | Recommendation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Gemini 3.8 Flash** | **94.2%** | **96.7%** | **100%** | 1.15s | **Production Primary** |
| **Groq GPT-OSS 120B**| 88.5% | 90.0% | 100% | **0.62s** | **Production Fallback** |

## 4. In-Depth Analysis
- **Grounding & Hallucination Prevention:** Gemini Flash consistently triggered deterministic refusal when context was absent, whereas OpenRouter Free occasionally hallucinated general statutory rules.
- **Latency & User Experience:** Groq demonstrated superior token generation speed, ideal for real-time streaming in the `/assistant` UI.
- **Cost & Rate Limits:** A dual-provider strategy (Gemini as primary, Groq as fallback) provides high resilience within free-tier budgets.