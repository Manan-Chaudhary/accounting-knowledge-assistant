import argparse

from app.evaluation.harness import (
    DEFAULT_MODEL,
    DEFAULT_RETRIEVAL_STRATEGY,
    DEFAULT_TOP_K,
    RETRIEVAL_STRATEGIES,
    run_suite,
)
from scripts.evaluation_report import write_report


def main():
    parser = argparse.ArgumentParser(
        description="Run the accounting RAG evaluation harness."
    )

    parser.add_argument(
        "--questions",
        default="benchmarks/questions.jsonl",
    )

    parser.add_argument(
        "--output",
        default="benchmarks/results/sample_results.jsonl",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
    )

    parser.add_argument(
        "--strategy",
        choices=sorted(RETRIEVAL_STRATEGIES),
        default=DEFAULT_RETRIEVAL_STRATEGY,
        help=(
            "RAG retrieval strategy to evaluate: "
            "dense, keyword, or hybrid."
        ),
    )

    parser.add_argument(
        "--judge",
        default=None,
        help="LiteLLM model used as an LLM judge for correctness and faithfulness.",
    )

    parser.add_argument(
        "--report",
        default=None,
        help="Write a markdown report for this run to the given path.",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep cases already saved in --output and run only the missing or failed ones.",
    )

    args = parser.parse_args()

    results = run_suite(
        questions_path=args.questions,
        output_path=args.output,
        model=args.model,
        top_k=args.top_k,
        judge_model=args.judge,
        resume=args.resume,
        retrieval_strategy=args.strategy,
    )

    print()
    print("=" * 60)
    print(f"Evaluation complete: {len(results)} cases")
    print(f"Retrieval strategy: {args.strategy}")
    print(f"Model: {args.model}")
    print(f"Results saved to: {args.output}")

    if args.report:
        report = write_report(
            [args.output],
            args.report,
            title=(
                f"Evaluation report: "
                f"{args.model} "
                f"({args.strategy} retrieval)"
            ),
        )
        print(f"Report saved to: {report}")

    print("=" * 60)


if __name__ == "__main__":
    main()