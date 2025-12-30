"""
Compare multiple LLM models on variant classification.

Usage:
    python scripts/compare_models.py --models openai/gpt-4o google/gemini-2.5-flash
    python scripts/compare_models.py --results-dir results/  # Compare existing results
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, RESULTS_DIR, CONCURRENCY_LIMIT, CLASSIFICATION_LABELS, DIRECTION_LABELS
from classify import AIVAClient, classify_batch, load_variants
from metrics import (
    load_results,
    normalize_classification,
    get_direction,
    calculate_class_metrics,
    calculate_direction_metrics,
    calculate_macro_f1,
    extract_ground_truth_and_predictions
)


def calculate_model_summary(results: list[dict]) -> dict:
    """Calculate summary metrics for a single model's results."""
    total = len(results)
    errors = sum(1 for r in results if r.get("error"))

    ground_truth, predictions, ground_dirs, pred_dirs = \
        extract_ground_truth_and_predictions(results)

    n_valid = len(ground_truth)
    exact_matches = sum(1 for g, p in zip(ground_truth, predictions) if g == p)
    directional_matches = sum(1 for g, p in zip(ground_dirs, pred_dirs) if g == p)

    valid = [r for r in results if not r.get("error") and r.get("aiva_classification")]
    exec_times = [r["execution_time_ms"] for r in valid if r.get("execution_time_ms")]

    return {
        "total": total,
        "errors": errors,
        "error_rate": round(errors / total, 4) if total > 0 else 0,
        "exact_accuracy": round(exact_matches / n_valid, 4) if n_valid > 0 else 0,
        "directional_accuracy": round(directional_matches / n_valid, 4) if n_valid > 0 else 0,
        "avg_time_ms": round(sum(exec_times) / len(exec_times), 1) if exec_times else 0
    }


async def run_model(
    client: AIVAClient,
    variants: list[dict],
    model: str,
    concurrency: int
) -> list[dict]:
    """Run classification for a single model."""
    print(f"\n{'='*60}")
    print(f"Running model: {model}")
    print(f"{'='*60}")

    def show_progress(completed: int, total: int):
        pct = 100 * completed / total
        print(f"\r  Progress: {completed}/{total} ({pct:.1f}%)", end="", flush=True)

    results = await classify_batch(
        client, variants,
        concurrency=concurrency,
        model=model,
        progress_callback=show_progress
    )

    print()  # Newline after progress
    return results


def print_comparison_report(model_results: dict[str, list[dict]]):
    """Print side-by-side comparison of model performance."""
    print("\n" + "=" * 80)
    print("MODEL COMPARISON REPORT")
    print("=" * 80)

    # Calculate summaries
    summaries = {}
    for model, results in model_results.items():
        summaries[model] = calculate_model_summary(results)

    # Sort by exact accuracy (descending)
    sorted_models = sorted(summaries.keys(), key=lambda m: summaries[m]["exact_accuracy"], reverse=True)

    # Print comparison table
    print(f"\n{'Model':<40} {'Exact':>8} {'Direct':>8} {'Errors':>8} {'Avg Time':>10}")
    print("-" * 80)

    for model in sorted_models:
        s = summaries[model]
        print(f"{model:<40} {s['exact_accuracy']*100:>7.1f}% {s['directional_accuracy']*100:>7.1f}% "
              f"{s['errors']:>7} {s['avg_time_ms']:>9.0f}ms")

    # Find best model
    best_exact = sorted_models[0]
    best_directional = max(sorted_models, key=lambda m: summaries[m]["directional_accuracy"])

    print("\n" + "-" * 80)
    print(f"Best Exact Match:    {best_exact} ({summaries[best_exact]['exact_accuracy']*100:.1f}%)")
    print(f"Best Directional:    {best_directional} ({summaries[best_directional]['directional_accuracy']*100:.1f}%)")

    # Per-class metrics (5-class)
    print(f"\n{'='*80}")
    print("PER-CLASS METRICS BY MODEL (5-class)")
    print("=" * 80)

    # Calculate per-class metrics for each model using shared function
    class_metrics_by_model = {}
    for model, results in model_results.items():
        ground_truth, predictions, _, _ = extract_ground_truth_and_predictions(results)
        class_metrics_by_model[model] = calculate_class_metrics(ground_truth, predictions, CLASSIFICATION_LABELS)

    # Print per-class F1 comparison
    print(f"\n{'Class':<25}", end="")
    for model in sorted_models:
        short_name = model.split("/")[-1][:12]
        print(f"{short_name:>14}", end="")
    print()
    print("-" * (25 + 14 * len(sorted_models)))

    for cls in CLASSIFICATION_LABELS:
        print(f"{cls:<25}", end="")
        for model in sorted_models:
            f1 = class_metrics_by_model[model].get(cls, {}).get("f1", 0)
            print(f"{f1*100:>12.1f}% F1", end="")
        print()

    # Macro F1 per model
    print("-" * (25 + 14 * len(sorted_models)))
    print(f"{'Macro F1':<25}", end="")
    for model in sorted_models:
        macro_f1 = calculate_macro_f1(class_metrics_by_model[model])
        print(f"{macro_f1*100:>12.1f}% F1", end="")
    print()

    # Per-direction metrics (3-class)
    print(f"\n{'='*80}")
    print("DIRECTIONAL METRICS BY MODEL (3-class: Pathogenic/VUS/Benign)")
    print("=" * 80)

    direction_metrics_by_model = {}
    for model, results in model_results.items():
        _, _, ground_dirs, pred_dirs = extract_ground_truth_and_predictions(results)
        direction_metrics_by_model[model] = calculate_direction_metrics(ground_dirs, pred_dirs, DIRECTION_LABELS)

    # Print directional metrics table
    print(f"\n{'Direction':<15}", end="")
    for model in sorted_models:
        short_name = model.split("/")[-1][:10]
        print(f"  {short_name:^30}", end="")
    print()

    print(f"{'':<15}", end="")
    for _ in sorted_models:
        print(f"  {'Prec':>8} {'Recall':>8} {'F1':>8}  ", end="")
    print()
    print("-" * (15 + 32 * len(sorted_models)))

    for d in DIRECTION_LABELS:
        print(f"{d:<15}", end="")
        for model in sorted_models:
            m = direction_metrics_by_model[model].get(d, {})
            print(f"  {m.get('precision', 0)*100:>7.1f}% {m.get('recall', 0)*100:>7.1f}% {m.get('f1', 0)*100:>7.1f}%  ", end="")
        print()

    # Macro F1 for directional
    print("-" * (15 + 32 * len(sorted_models)))
    print(f"{'Macro F1':<15}", end="")
    for model in sorted_models:
        macro_f1 = calculate_macro_f1(direction_metrics_by_model[model])
        print(f"  {'':>8} {'':>8} {macro_f1*100:>7.1f}%  ", end="")
    print()

    # Agreement analysis between models
    if len(sorted_models) >= 2:
        print(f"\n{'='*80}")
        print("MODEL AGREEMENT ANALYSIS")
        print("=" * 80)

        # Compare each pair of models
        for i, model1 in enumerate(sorted_models):
            for model2 in sorted_models[i+1:]:
                results1 = {r["variant_id"]: r for r in model_results[model1] if not r.get("error")}
                results2 = {r["variant_id"]: r for r in model_results[model2] if not r.get("error")}

                common_ids = set(results1.keys()) & set(results2.keys())
                agreements = 0
                for vid in common_ids:
                    c1 = normalize_classification(results1[vid].get("aiva_classification", ""))
                    c2 = normalize_classification(results2[vid].get("aiva_classification", ""))
                    if c1 == c2:
                        agreements += 1

                if common_ids:
                    agreement_rate = agreements / len(common_ids)
                    short1 = model1.split("/")[-1][:20]
                    short2 = model2.split("/")[-1][:20]
                    print(f"  {short1} vs {short2}: {agreement_rate*100:.1f}% agreement ({agreements}/{len(common_ids)})")

    print("\n" + "=" * 80)

    return summaries


def calculate_detailed_metrics(model_results: dict[str, list[dict]]) -> dict:
    """Calculate detailed per-class and per-direction metrics for all models."""
    detailed = {}

    for model, results in model_results.items():
        ground_truth, predictions, ground_dirs, pred_dirs = \
            extract_ground_truth_and_predictions(results)

        # Per-class metrics
        class_metrics = calculate_class_metrics(ground_truth, predictions, CLASSIFICATION_LABELS)

        # Per-direction metrics
        direction_metrics = calculate_direction_metrics(ground_dirs, pred_dirs, DIRECTION_LABELS)

        # Macro F1 scores
        macro_f1_5class = calculate_macro_f1(class_metrics)
        macro_f1_3class = calculate_macro_f1(direction_metrics)

        detailed[model] = {
            "per_class": class_metrics,
            "per_direction": direction_metrics,
            "macro_f1_5class": round(macro_f1_5class, 4),
            "macro_f1_3class": round(macro_f1_3class, 4)
        }

    return detailed


def save_comparison(model_results: dict[str, list[dict]], summaries: dict, output_dir: Path):
    """Save comparison results to files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Calculate detailed metrics
    detailed_metrics = calculate_detailed_metrics(model_results)

    # Save summary
    summary_path = output_dir / f"comparison_{timestamp}.json"
    comparison_data = {
        "timestamp": datetime.now().isoformat(),
        "models": list(model_results.keys()),
        "summaries": summaries,
        "detailed_metrics": detailed_metrics
    }

    with open(summary_path, "w") as f:
        json.dump(comparison_data, f, indent=2)

    print(f"\nSaved comparison to {summary_path}")

    return summary_path


async def main():
    parser = argparse.ArgumentParser(description="Compare LLM models on variant classification")
    parser.add_argument("--models", nargs="+",
                        help="Models to compare (e.g., openai/gpt-4o google/gemini-2.5-flash)")
    parser.add_argument("--input", help="Input JSONL file with variants")
    parser.add_argument("--results-dir", help="Directory with existing results to compare")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY_LIMIT,
                        help=f"Max concurrent requests (default: {CONCURRENCY_LIMIT})")
    parser.add_argument("--limit", type=int, help="Limit number of variants")

    args = parser.parse_args()

    model_results = {}

    if args.results_dir:
        # Load existing results from directory
        results_dir = Path(args.results_dir)
        result_files = list(results_dir.glob("classifications_*.jsonl"))

        if not result_files:
            print(f"Error: No classification files found in {results_dir}")
            sys.exit(1)

        print(f"Found {len(result_files)} result files")

        for filepath in result_files:
            results = load_results(filepath)
            if results:
                # Try to get model from first result
                model = results[0].get("model_used", filepath.stem)
                if model:
                    model_results[model] = results
                    print(f"  Loaded {len(results)} results for {model}")

    elif args.models:
        # Run classification for each model
        if args.input:
            input_path = Path(args.input)
        else:
            sample_files = list(DATA_DIR.glob("sample_*.jsonl"))
            if not sample_files:
                print("Error: No sample files found. Run parse_erepo.py first.")
                sys.exit(1)
            input_path = max(sample_files, key=lambda p: p.stat().st_mtime)

        print(f"Loading variants from {input_path}")
        variants = load_variants(input_path)

        if args.limit:
            variants = variants[:args.limit]

        print(f"Testing {len(variants)} variants across {len(args.models)} models")

        async with AIVAClient() as client:
            for model in args.models:
                results = await run_model(client, variants, model, args.concurrency)
                model_results[model] = results

                # Save individual results
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                model_slug = model.replace("/", "_")
                output_path = RESULTS_DIR / f"classifications_{model_slug}_{timestamp}.jsonl"

                with open(output_path, "w") as f:
                    for r in results:
                        f.write(json.dumps(r) + "\n")
                print(f"  Saved to {output_path}")

    else:
        print("Error: Provide either --models or --results-dir")
        parser.print_help()
        sys.exit(1)

    if len(model_results) < 1:
        print("Error: No results to compare")
        sys.exit(1)

    # Print comparison report
    summaries = print_comparison_report(model_results)

    # Save comparison
    save_comparison(model_results, summaries, RESULTS_DIR)


if __name__ == "__main__":
    asyncio.run(main())
