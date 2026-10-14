"""
Latency measurement script for R110.

Measures timing breakdown across RAG pipeline stages:
- S1: Intake (session/settings lookup, parsing)
- S2: Query embedding
- S3: Retrieval queries and fusion (dense + keyword SQL + RRF)
- S4: Reranking (not yet implemented)
- S5: LLM time to first token
- S6: Generation and finalize

Implements measurement method from docs/LATENCY-TARGETS.md sections 6.1-6.3.
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any
from statistics import median

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.embedder import embed_text
from app.rag.retriever import retrieve_hybrid
from app.rag.generator import generate_response_stream, get_formatted_prompt, SYSTEM_PROMPT_TEMPLATE
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StageTimings:
    """Timing measurements for each pipeline stage in milliseconds."""
    request_id: str
    question_id: str
    question_class: str
    
    # Stage timings (milliseconds)
    intake_ms: float
    embed_ms: float
    retrieval_sql_ms: float
    rerank_ms: float  # Not yet implemented
    llm_ttft_ms: float
    ttft_ms: float
    generation_ms: float  # S6: remaining tokens
    total_ms: float
    
    # Configuration
    model_requested: str
    model_used: Optional[str]
    retrieval_strategy: str
    final_top_k: int
    reranker_enabled: bool
    streaming_enabled: bool
    cold: bool
    git_commit: str
    
    # Output metrics
    answer_length_chars: int
    answer_length_tokens: Optional[int]
    num_chunks_retrieved: int
    
    # Status
    success: bool
    error_message: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class LatencyMeasurement:
    """Orchestrates latency measurement across the RAG pipeline."""
    
    def __init__(self, model: str = "gemini-3-8-flash", cold: bool = False):
        self.model = model
        self.cold = cold
        self.git_commit = self._get_git_commit()
        
    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
    
    def measure_single_query(
        self,
        question_id: str,
        question_class: str,
        query: str,
        request_id: Optional[str] = None,
    ) -> StageTimings:
        """
        Measure latency for a single query through the complete pipeline.
        
        Implements timing boundaries from LATENCY-TARGETS.md LT-16.
        """
        if request_id is None:
            request_id = f"{question_id}_{int(time.time()*1000)}"
        
        # Overall timing
        request_start = time.perf_counter()
        
        success = True
        error_message = None
        model_used = None
        answer_text = ""
        num_chunks = 0
        
        try:
            # S1: Intake
            # In a real implementation this would include session/settings lookup
            # For measurement purposes, we start timing here
            intake_start = time.perf_counter()
            # Minimal intake simulation - in production this loads session, parses request
            intake_end = time.perf_counter()
            intake_ms = (intake_end - intake_start) * 1000
            
            # S2: Query embedding
            # Measured inside retrieve_hybrid, but we also time it separately here
            embed_start = time.perf_counter()
            query_embedding = embed_text(query)
            embed_end = time.perf_counter()
            embed_ms = (embed_end - embed_start) * 1000
            
            # S3: Retrieval queries and fusion
            # This includes dense SQL, keyword SQL, RRF fusion, and context formatting
            retrieval_start = time.perf_counter()
            chunks = retrieve_hybrid(query, top_k=6)
            num_chunks = len(chunks)
            
            # Format context
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                source = chunk.source_label or "General"
                context_parts.append(
                    f"[{i}] Source: {chunk.filename} ({source})\n{chunk.content}"
                )
            context = "\n\n".join(context_parts)
            
            retrieval_end = time.perf_counter()
            # Subtract embedding time since we measured it separately
            retrieval_sql_ms = (retrieval_end - retrieval_start) * 1000 - embed_ms
            
            # S4: Reranking
            # Not yet implemented - placeholder
            rerank_ms = 0.0
            
            # Format the prompt
            user_prompt = get_formatted_prompt(query=query, context=context)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE},
                {"role": "user", "content": user_prompt},
            ]
            
            # S5: LLM time to first token
            # Measured from just before the API call to first non-empty content
            llm_start = time.perf_counter()
            
            first_token_time = None
            token_count = 0
            
            # Use streaming to measure TTFT
            from openai import OpenAI
            from app.rag.generator import _resolve_proxy_settings
            
            resolved_base, resolved_key = _resolve_proxy_settings()
            client = OpenAI(base_url=resolved_base, api_key=resolved_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                stream=True,
            )
            
            # Track when first token event is ready to write
            first_token_written = None
            answer_parts = []
            
            for chunk in response:
                if not chunk.choices:
                    continue
                
                # Capture model used from response
                if model_used is None and hasattr(chunk, 'model'):
                    model_used = chunk.model
                
                delta = chunk.choices[0].delta
                content = delta.content
                
                if content:
                    token_count += 1
                    
                    # S5 ends: first non-empty content delta received
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                        llm_ttft_ms = (first_token_time - llm_start) * 1000
                    
                    # LT-17: TTFT measured when first token event is written to response
                    if first_token_written is None:
                        first_token_written = time.perf_counter()
                        ttft_ms = (first_token_written - request_start) * 1000
                    
                    answer_parts.append(content)
            
            # S6: Generation and finalize (remaining tokens after first)
            generation_end = time.perf_counter()
            
            if first_token_time is None:
                # No content received - error case
                raise RuntimeError("No content received from LLM")
            
            generation_ms = (generation_end - first_token_time) * 1000
            answer_text = "".join(answer_parts)
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.exception(f"Error measuring query {question_id}")
            
            # Set default values for failed request
            if 'intake_ms' not in locals():
                intake_ms = 0.0
            if 'embed_ms' not in locals():
                embed_ms = 0.0
            if 'retrieval_sql_ms' not in locals():
                retrieval_sql_ms = 0.0
            if 'llm_ttft_ms' not in locals():
                llm_ttft_ms = 0.0
            if 'ttft_ms' not in locals():
                ttft_ms = 0.0
            if 'generation_ms' not in locals():
                generation_ms = 0.0
        
        # Total time
        request_end = time.perf_counter()
        total_ms = (request_end - request_start) * 1000
        
        return StageTimings(
            request_id=request_id,
            question_id=question_id,
            question_class=question_class,
            intake_ms=intake_ms,
            embed_ms=embed_ms,
            retrieval_sql_ms=retrieval_sql_ms,
            rerank_ms=rerank_ms,
            llm_ttft_ms=llm_ttft_ms,
            ttft_ms=ttft_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,
            model_requested=self.model,
            model_used=model_used,
            retrieval_strategy="hybrid",
            final_top_k=6,
            reranker_enabled=False,
            streaming_enabled=True,
            cold=self.cold,
            git_commit=self.git_commit,
            answer_length_chars=len(answer_text),
            answer_length_tokens=token_count if token_count > 0 else None,
            num_chunks_retrieved=num_chunks,
            success=success,
            error_message=error_message,
        )


def load_benchmark_questions(questions_file: Path) -> List[Dict[str, Any]]:
    """Load questions from JSONL file."""
    questions = []
    with open(questions_file, 'r') as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions


def calculate_percentile(values: List[float], percentile: int) -> float:
    """
    Calculate percentile using nearest-rank method.
    
    Matches scripts/evaluation_report.py implementation.
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    import math
    index = math.ceil(percentile / 100 * n) - 1
    index = max(0, min(index, n - 1))
    
    return sorted_values[index]


def generate_report(
    results: List[StageTimings],
    output_file: Path,
    warm_only: bool = True,
) -> Dict[str, Any]:
    """
    Generate latency breakdown report.
    
    Implements reporting requirements from LATENCY-TARGETS.md LT-29 to LT-31.
    """
    # Filter to warm samples if requested
    samples = [r for r in results if not r.cold] if warm_only else results
    cold_samples = [r for r in results if r.cold]
    
    # Calculate stage statistics
    def stage_stats(stage_name: str, budget_p50: float, budget_p95: float) -> Dict[str, Any]:
        values = [getattr(r, stage_name) for r in samples if r.success]
        if not values:
            return {
                "n": 0,
                "p50_ms": 0,
                "p95_ms": 0,
                "max_ms": 0,
                "budget_p50_ms": budget_p50,
                "budget_p95_ms": budget_p95,
                "over_budget_count": 0,
            }
        
        p50 = calculate_percentile(values, 50)
        p95 = calculate_percentile(values, 95)
        
        over_budget = sum(1 for v in values if v > budget_p95)
        
        return {
            "n": len(values),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "max_ms": round(max(values), 2),
            "budget_p50_ms": budget_p50,
            "budget_p95_ms": budget_p95,
            "over_budget_count": over_budget,
            "p50_vs_budget": f"{p50 - budget_p50:+.1f}ms",
            "p95_vs_budget": f"{p95 - budget_p95:+.1f}ms",
        }
    
    # LT-7 to LT-12: Stage budgets from LATENCY-TARGETS.md section 5.2
    stage_table = {
        "S1_intake": stage_stats("intake_ms", budget_p50=50, budget_p95=100),
        "S2_embedding": stage_stats("embed_ms", budget_p50=450, budget_p95=900),
        "S3_retrieval_sql": stage_stats("retrieval_sql_ms", budget_p50=300, budget_p95=500),
        "S4_reranking": stage_stats("rerank_ms", budget_p50=300, budget_p95=600),
        "S5_llm_ttft": stage_stats("llm_ttft_ms", budget_p50=1400, budget_p95=2400),
        "S6_generation": stage_stats("generation_ms", budget_p50=2500, budget_p95=3500),
    }
    
    # End-to-end metrics
    ttft_values = [r.ttft_ms for r in samples if r.success]
    total_values = [r.total_ms for r in samples if r.success]
    
    ttft_p50 = calculate_percentile(ttft_values, 50) if ttft_values else 0
    ttft_p95 = calculate_percentile(ttft_values, 95) if ttft_values else 0
    total_p50 = calculate_percentile(total_values, 50) if total_values else 0
    total_p95 = calculate_percentile(total_values, 95) if total_values else 0
    
    # LT-1 and LT-2: End-to-end targets
    end_to_end = {
        "ttft": {
            "n": len(ttft_values),
            "p50_ms": round(ttft_p50, 2),
            "p95_ms": round(ttft_p95, 2),
            "target_p50_ms": 2500,  # LT-1
            "target_p95_ms": 4500,  # LT-1
            "p50_pass": ttft_p50 <= 2500,
            "p95_pass": ttft_p95 <= 4500,
        },
        "total": {
            "n": len(total_values),
            "p50_ms": round(total_p50, 2),
            "p95_ms": round(total_p95, 2),
            "target_p50_ms": 5000,  # LT-2
            "target_p95_ms": 8000,  # LT-2 (gate)
            "p50_pass": total_p50 <= 5000,
            "p95_pass": total_p95 <= 8000,
        },
    }
    
    # Failure analysis
    failures = [r for r in samples if not r.success]
    failure_rate = len(failures) / len(samples) if samples else 0
    
    # LT-6: 30s timeout failures
    timeout_failures = [r for r in samples if not r.success and r.ttft_ms > 30000]
    
    # Cold samples analysis (LT-4)
    cold_analysis = {}
    if cold_samples:
        cold_ttft = [r.ttft_ms for r in cold_samples if r.success]
        if cold_ttft:
            cold_analysis = {
                "n": len(cold_ttft),
                "max_ttft_ms": round(max(cold_ttft), 2),
                "target_max_ms": 15000,  # LT-4
                "pass": max(cold_ttft) <= 15000,
            }
    
    # Configuration
    if samples:
        sample_config = samples[0]
        config = {
            "model_requested": sample_config.model_requested,
            "retrieval_strategy": sample_config.retrieval_strategy,
            "final_top_k": sample_config.final_top_k,
            "reranker_enabled": sample_config.reranker_enabled,
            "streaming_enabled": sample_config.streaming_enabled,
            "git_commit": sample_config.git_commit,
            "measurement_date": time.strftime("%Y-%m-%d"),
        }
    else:
        config = {}
    
    # Identify slowest stage
    slowest_stage = None
    max_overrun = 0
    for stage_name, stats in stage_table.items():
        if stats["n"] > 0:
            overrun = stats["p95_ms"] - stats["budget_p95_ms"]
            if overrun > max_overrun:
                max_overrun = overrun
                slowest_stage = stage_name
    
    report = {
        "configuration": config,
        "summary": {
            "total_samples": len(results),
            "warm_samples": len(samples),
            "cold_samples": len(cold_samples),
            "success_count": len([r for r in samples if r.success]),
            "failure_count": len(failures),
            "failure_rate": round(failure_rate * 100, 2),
        },
        "end_to_end_metrics": end_to_end,
        "stage_breakdown": stage_table,
        "cold_samples": cold_analysis,
        "pass_fail": {
            "ttft_p50_pass": end_to_end["ttft"]["p50_pass"],
            "ttft_p95_pass": end_to_end["ttft"]["p95_pass"],
            "total_p50_pass": end_to_end["total"]["p50_pass"],
            "total_p95_pass": end_to_end["total"]["p95_pass"],  # LT-2 gate
            "failure_rate_pass": failure_rate <= 0.05,  # LT-30
            "overall_pass": (
                end_to_end["ttft"]["p50_pass"] and
                end_to_end["ttft"]["p95_pass"] and
                end_to_end["total"]["p95_pass"] and
                failure_rate <= 0.05
            ),
        },
        "findings": {
            "slowest_stage": slowest_stage,
            "slowest_stage_overrun_ms": round(max_overrun, 2),
            "stages_over_budget": [
                stage for stage, stats in stage_table.items()
                if stats["over_budget_count"] > 0
            ],
        },
        "failures": [
            {
                "request_id": f.request_id,
                "question_id": f.question_id,
                "error": f.error_message,
                "elapsed_ms": f.total_ms,
            }
            for f in failures
        ],
    }
    
    # Write JSON report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report


def print_report_summary(report: Dict[str, Any]):
    """Print human-readable report summary."""
    print("\n" + "="*80)
    print("LATENCY BREAKDOWN REPORT")
    print("="*80)
    
    config = report["configuration"]
    print(f"\nConfiguration:")
    print(f"  Model: {config.get('model_requested', 'unknown')}")
    print(f"  Strategy: {config.get('retrieval_strategy', 'unknown')}")
    print(f"  Top-k: {config.get('final_top_k', 'unknown')}")
    print(f"  Reranker: {config.get('reranker_enabled', False)}")
    print(f"  Streaming: {config.get('streaming_enabled', False)}")
    print(f"  Git commit: {config.get('git_commit', 'unknown')}")
    print(f"  Date: {config.get('measurement_date', 'unknown')}")
    
    summary = report["summary"]
    print(f"\nSample Size:")
    print(f"  Warm samples: {summary['warm_samples']}")
    print(f"  Cold samples: {summary['cold_samples']}")
    print(f"  Failures: {summary['failure_count']} ({summary['failure_rate']}%)")
    
    print(f"\n{'='*80}")
    print("END-TO-END METRICS (vs targets)")
    print("="*80)
    
    e2e = report["end_to_end_metrics"]
    ttft = e2e["ttft"]
    total = e2e["total"]
    
    print(f"\nTime to First Token (LT-1):")
    print(f"  P50: {ttft['p50_ms']:>8.1f} ms  (target: {ttft['target_p50_ms']:>6} ms)  {'✓ PASS' if ttft['p50_pass'] else '✗ FAIL'}")
    print(f"  P95: {ttft['p95_ms']:>8.1f} ms  (target: {ttft['target_p95_ms']:>6} ms)  {'✓ PASS' if ttft['p95_pass'] else '✗ FAIL'}")
    
    print(f"\nTotal Response Time (LT-2):")
    print(f"  P50: {total['p50_ms']:>8.1f} ms  (target: {total['target_p50_ms']:>6} ms)  {'✓ PASS' if total['p50_pass'] else '✗ FAIL'}")
    print(f"  P95: {total['p95_ms']:>8.1f} ms  (target: {total['target_p95_ms']:>6} ms)  {'✓ PASS' if total['p95_pass'] else '✗ FAIL'} [GATE]")
    
    print(f"\n{'='*80}")
    print("STAGE BREAKDOWN (vs budgets)")
    print("="*80)
    
    stage_names = {
        "S1_intake": "S1 Intake",
        "S2_embedding": "S2 Query Embedding",
        "S3_retrieval_sql": "S3 Retrieval SQL",
        "S4_reranking": "S4 Reranking",
        "S5_llm_ttft": "S5 LLM TTFT",
        "S6_generation": "S6 Generation",
    }
    
    print(f"\n{'Stage':<25} {'P50':<12} {'P95':<12} {'Budget P95':<12} {'Status'}")
    print("-" * 80)
    
    stages = report["stage_breakdown"]
    for stage_key, display_name in stage_names.items():
        stats = stages[stage_key]
        if stats["n"] > 0:
            p50_str = f"{stats['p50_ms']:.1f} ms"
            p95_str = f"{stats['p95_ms']:.1f} ms"
            budget_str = f"{stats['budget_p95_ms']} ms"
            status = "✓" if stats["over_budget_count"] == 0 else f"✗ ({stats['over_budget_count']} over)"
            print(f"{display_name:<25} {p50_str:<12} {p95_str:<12} {budget_str:<12} {status}")
    
    print(f"\n{'='*80}")
    print("FINDINGS")
    print("="*80)
    
    findings = report["findings"]
    print(f"\nSlowest Stage: {findings['slowest_stage']}")
    print(f"  Overrun: {findings['slowest_stage_overrun_ms']:.1f} ms over budget")
    
    if findings["stages_over_budget"]:
        print(f"\nStages Over Budget:")
        for stage in findings["stages_over_budget"]:
            print(f"  - {stage_names.get(stage, stage)}")
    
    pf = report["pass_fail"]
    print(f"\n{'='*80}")
    print(f"OVERALL: {'✓ PASS' if pf['overall_pass'] else '✗ FAIL'}")
    print("="*80)
    
    if not pf["overall_pass"]:
        print("\nRecommendation:")
        slowest = findings['slowest_stage']
        if slowest == "S2_embedding":
            print("  → Optimize query embedding: consider local model or caching")
        elif slowest == "S3_retrieval_sql":
            print("  → Optimize retrieval: add full-text index, tune database config")
        elif slowest == "S5_llm_ttft":
            print("  → Optimize LLM: consider faster model, reduce context, or paid tier")
        elif slowest == "S6_generation":
            print("  → Reduce generation time: add max_tokens cap, use shorter system prompt")
        else:
            print(f"  → Investigate {slowest} performance")
    
    print()


def main():
    """Run latency measurement suite."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Measure RAG pipeline latency breakdown"
    )
    parser.add_argument(
        "--model",
        default="gemini-3-8-flash",
        help="Model to test (default: gemini-3-8-flash)",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("benchmarks/questions.jsonl"),
        help="Path to questions JSONL file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=None,
        help="Output path for markdown report (default: benchmarks/reports/latency_<model>_<date>.md)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to test",
    )
    parser.add_argument(
        "--cold-run",
        action="store_true",
        help="Mark this as a cold run (first 2 requests after startup)",
    )
    
    args = parser.parse_args()
    
    # Load questions
    questions = load_benchmark_questions(args.questions)
    if args.limit:
        questions = questions[:args.limit]
    
    print(f"Measuring latency for {len(questions)} questions using model: {args.model}")
    print("This may take several minutes...")
    
    # Run measurement
    measurer = LatencyMeasurement(model=args.model, cold=args.cold_run)
    results = []
    
    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] {q['id']}: {q['question'][:60]}...")
        
        try:
            timing = measurer.measure_single_query(
                question_id=q["id"],
                question_class=q["class"],
                query=q["question"],
            )
            results.append(timing)
            
            if timing.success:
                print(f"  ✓ TTFT: {timing.ttft_ms:.1f}ms, Total: {timing.total_ms:.1f}ms")
            else:
                print(f"  ✗ FAILED: {timing.error_message}")
        
        except KeyboardInterrupt:
            print("\n\nMeasurement interrupted by user")
            break
        except Exception as e:
            logger.exception(f"Unexpected error measuring {q['id']}")
            continue
    
    if not results:
        print("No results collected")
        return 1
    
    # Save raw results
    args.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d_%H%M%S")
    results_file = args.output_dir / f"latency_{args.model}_{timestamp}.jsonl"
    
    with open(results_file, 'w') as f:
        for r in results:
            f.write(json.dumps(r.to_dict()) + "\n")
    
    print(f"\nRaw results saved to: {results_file}")
    
    # Generate report
    if args.output_report:
        report_file = args.output_report
    else:
        report_dir = Path("benchmarks/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"latency_{args.model}_{timestamp}.json"
    
    report = generate_report(results, report_file, warm_only=not args.cold_run)
    print(f"Report saved to: {report_file}")
    
    # Print summary
    print_report_summary(report)
    
    return 0 if report["pass_fail"]["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
