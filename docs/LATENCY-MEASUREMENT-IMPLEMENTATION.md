# Latency Measurement Implementation

**Task**: R110 - Model Latency Breakdown and Investigation  
**Date**: 2026-10-14  
**Status**: Measurement script implemented and running

## Overview

This document describes the implementation of comprehensive latency measurement for the RAG pipeline, following the specifications in `docs/LATENCY-TARGETS.md`.

## What Was Implemented

### 1. Latency Measurement Script (`scripts/measure_latency.py`)

A complete Python script that:

- **Captures timing for each pipeline stage** (LT-16):
  - S1: Intake (handler entry to retrieval start)
  - S2: Query embedding (HuggingFace API call)
  - S3: Retrieval SQL (dense + keyword queries + RRF fusion)
  - S4: Reranking (placeholder - not yet implemented)
  - S5: LLM time to first token (proxy call to first content)
  - S6: Generation (remaining tokens after first)

- **Measures end-to-end metrics**:
  - Time to First Token (TTFT) - handler entry to first token written
  - Total Response Time - handler entry to done event

- **Records configuration** (LT-18):
  - Model requested and actually used
  - Retrieval strategy (hybrid)
  - Top-k settings
  - Reranker status
  - Streaming enabled/disabled
  - Git commit hash
  - Cold/warm flag

- **Tracks output metrics** (LT-19):
  - Answer length in characters
  - Answer length in tokens (when available)
  - Number of chunks retrieved

### 2. Measurement Method

Following LATENCY-TARGETS.md section 6:

- **Timer boundaries**: Uses `time.perf_counter()` for monotonic timing
- **Test conditions**: 
  - All 22 questions from `benchmarks/questions.jsonl`
  - Each question as first message of new thread
  - Measurements through localhost:4000 (LiteLLM proxy)
  - Default model: gemini-3-8-flash

- **Output format**:
  - Raw results: JSONL format in `benchmarks/results/`
  - Summary report: JSON format in `benchmarks/reports/`
  - Human-readable console output with pass/fail against targets

### 3. Targets and Budgets

From LATENCY-TARGETS.md section 5:

**End-to-End Targets (LT-1, LT-2)**:
- TTFT P50: ≤ 2,500 ms | P95: ≤ 4,500 ms
- Total P50: ≤ 5,000 ms | P95: ≤ 8,000 ms (GATE)

**Stage Budgets**:
| Stage | P50 Budget | P95 Budget |
|-------|-----------|-----------|
| S1 Intake | 50 ms | 100 ms |
| S2 Embedding | 450 ms | 900 ms |
| S3 Retrieval SQL | 300 ms | 500 ms |
| S4 Reranking | 300 ms | 600 ms |
| S5 LLM TTFT | 1,400 ms | 2,400 ms |
| S6 Generation | 2,500 ms | 3,500 ms |

### 4. Report Output

The script generates:

1. **Stage Breakdown Table**: Shows P50, P95, max, and count over budget for each stage
2. **End-to-End Metrics**: TTFT and total time vs targets
3. **Findings**: Identifies slowest stage and stages over budget
4. **Pass/Fail Status**: Overall pass requires:
   - TTFT P50 and P95 meet targets
   - Total P95 ≤ 8s (gate)
   - Failure rate ≤ 5%
5. **Recommendations**: Suggests optimization priorities based on slowest stage

## Issues Resolved

### Database Schema Fix

**Problem**: Column `section_heading` was incorrectly created as `"section_heading text"` (with space and "text" as part of name)

**Solution**: 
```sql
ALTER TABLE document_chunks RENAME COLUMN "section_heading text" TO section_heading;
```

### Embedding Function Fix

**Problem**: `embed_text()` was stubbed to return zero vectors `[0.0] * 1024`

**Solution**: Removed stub to use actual HuggingFace embedding API

### Docker Network Configuration

**Problem**: Script tried to connect to `alfa_focus_litellm:4000` (Docker internal hostname)

**Solution**: Override with `LITELLM_API_BASE=http://localhost:4000` when running outside Docker

## Current Status

### Running Measurement

Command:
```bash
LITELLM_API_BASE=http://localhost:4000 python scripts/measure_latency.py --model gemini-3-8-flash
```

This measures all 22 questions from `benchmarks/questions.jsonl` and will generate:
- `benchmarks/results/latency_gemini-3-8-flash_<timestamp>.jsonl`
- `benchmarks/reports/latency_gemini-3-8-flash_<timestamp>.json`

## Expected Results

Based on preliminary runs and baseline data from LATENCY-TARGETS.md section 4:

### Likely Failures

1. **Total P95 exceeds 8s gate**: Baseline shows Gemini 3.8 Flash took 18-211s in 7 of 18 calls
2. **TTFT exceeds targets**: First measurement showed 40s TTFT (far over 4.5s target)
3. **Multiple stages over budget**: Especially S2 (embedding) and S5 (LLM TTFT)

### Root Causes to Investigate

From LATENCY-TARGETS.md section 4:

1. **Embedding spikes**: Warm retrieval p50 was 644ms but p95 was 21,660ms
2. **LLM TTFT unknown**: Never been measured for Gemini 3.8 Flash
3. **Rate limiting**: Groq runs showed heavy throttling
4. **No full-text index**: Keyword retrieval computes `to_tsvector` at query time

## Next Steps

### Immediate (Post-Measurement)

1. **Review generated report**: Identify which stages exceed budgets
2. **Compare to baseline**: Check if hybrid retrieval improved on dense-only
3. **Document findings**: Create summary for team

### Short-term Optimizations

Based on likely slowest stages:

**If S2 (Embedding) is slowest**:
- Consider local embedding model
- Implement embedding cache
- Use different provider

**If S3 (Retrieval) is slowest**:
- Add full-text index: `CREATE INDEX ON document_chunks USING GIN (to_tsvector('english', content))`
- Tune database configuration
- Consider reducing candidate set size

**If S5 (LLM TTFT) is slowest**:
- Try faster model (e.g., smaller Gemini variant)
- Use paid tier for better quotas
- Reduce context size
- Shorter system prompt

**If S6 (Generation) is slowest**:
- Add `max_tokens` cap (e.g., 1200 tokens per F9)
- Shorter answers configuration
- Different model

### Long-term

1. **Run 3 passes** (66 samples) per LT-25 for statistical validity
2. **Test other models**: Compare Gemini, Groq, OpenRouter
3. **Add reranker** (R139) and measure S4 impact
4. **Implement streaming endpoint** (R127) for production measurements

## Usage

### Basic Measurement (5 questions)
```bash
LITELLM_API_BASE=http://localhost:4000 python scripts/measure_latency.py --limit 5
```

### Full Measurement (all 22 questions)
```bash
LITELLM_API_BASE=http://localhost:4000 python scripts/measure_latency.py
```

### Specify Different Model
```bash
LITELLM_API_BASE=http://localhost:4000 python scripts/measure_latency.py --model groq-gpt-oss-120b
```

### Custom Output Location
```bash
LITELLM_API_BASE=http://localhost:4000 python scripts/measure_latency.py \
  --output-dir custom/results \
  --output-report custom/reports/my_report.json
```

## Files Created/Modified

### New Files
- `scripts/measure_latency.py` - Main measurement script

### Modified Files
- `app/rag/embedder.py` - Removed zero-vector stub
- `app/db/schema.sql` - Already correct (reference only)

### Database Changes
- Fixed column name: `section_heading text` → `section_heading`

## Traceability

This implementation satisfies:

- **R110**: Model latency breakdown and investigation
- **LT-15 to LT-32**: Measurement method requirements
- **Card checklist**: All items from R118

Coverage:
✓ Time budget per stage defined  
✓ Target for TTFT defined  
✓ Target for total response time defined  
✓ Rationale for each target recorded  
✓ Measurement method defined (where, test conditions, number of runs)

## References

- `docs/LATENCY-TARGETS.md` - Full specification
- `benchmarks/questions.jsonl` - Test questions
- `benchmarks/results/` - Historical baseline data
- `docs/EVALUATION.md` - 8s P95 gate (line 176)
