"""
4-way comparison: AIVA vs InterVar vs BIAS-2015 vs eRepo ground truth.

Usage:
    python scripts/compare_tools.py --aiva-results results/classifications_*.jsonl
    python scripts/compare_tools.py --aiva-results results/classifications_*.jsonl --unified data/bias_unified.jsonl
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RESULTS_DIR, DATA_DIR, CLASSIFICATION_LABELS, DIRECTION_LABELS
from metrics import (
    normalize_classification,
    get_direction,
    calculate_class_metrics,
    calculate_direction_metrics,
    calculate_macro_f1
)


def load_jsonl(filepath: Path) -> list[dict]:
    """Load JSONL file."""
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def load_aiva_results(filepaths: list[Path]) -> dict[str, dict]:
    """Load AIVA results and index by variant_id."""
    aiva_by_id = {}
    for fp in filepaths:
        for r in load_jsonl(fp):
            vid = r.get("variant_id")
            if vid and not r.get("error"):
                aiva_by_id[vid] = {
                    "classification": r.get("aiva_classification"),
                    "criteria": r.get("aiva_criteria", []),
                    "model": r.get("model_used")
                }
    return aiva_by_id


def calculate_tool_metrics(predictions: list[str], ground_truth: list[str]) -> dict:
    """Calculate comprehensive metrics for a tool."""
    # Normalize predictions
    norm_preds = [normalize_classification(p) for p in predictions]
    norm_gt = [normalize_classification(g) for g in ground_truth]

    # Get directions
    pred_dirs = [get_direction(p) for p in norm_preds]
    gt_dirs = [get_direction(g) for g in norm_gt]

    # Filter valid predictions
    valid_indices = [i for i, (p, g) in enumerate(zip(norm_preds, norm_gt))
                    if p and g]

    valid_preds = [norm_preds[i] for i in valid_indices]
    valid_gt = [norm_gt[i] for i in valid_indices]
    valid_pred_dirs = [pred_dirs[i] for i in valid_indices]
    valid_gt_dirs = [gt_dirs[i] for i in valid_indices]

    n_valid = len(valid_preds)
    if n_valid == 0:
        return {"error": "No valid predictions"}

    # Exact accuracy (5-class)
    exact_matches = sum(1 for p, g in zip(valid_preds, valid_gt) if p == g)
    exact_accuracy = exact_matches / n_valid

    # Directional accuracy (3-class)
    dir_matches = sum(1 for p, g in zip(valid_pred_dirs, valid_gt_dirs) if p == g)
    directional_accuracy = dir_matches / n_valid

    # Per-class metrics
    class_metrics = calculate_class_metrics(valid_gt, valid_preds, CLASSIFICATION_LABELS)
    direction_metrics = calculate_direction_metrics(valid_gt_dirs, valid_pred_dirs, DIRECTION_LABELS)

    # Macro F1
    macro_f1_5class = calculate_macro_f1(class_metrics)
    macro_f1_3class = calculate_macro_f1(direction_metrics)

    return {
        "n_total": len(predictions),
        "n_valid": n_valid,
        "exact_accuracy": round(exact_accuracy, 4),
        "directional_accuracy": round(directional_accuracy, 4),
        "macro_f1_5class": round(macro_f1_5class, 4),
        "macro_f1_3class": round(macro_f1_3class, 4),
        "per_class": class_metrics,
        "per_direction": direction_metrics
    }


def build_confusion_matrix(predictions: list[str], ground_truth: list[str], labels: list[str]) -> dict:
    """Build confusion matrix."""
    matrix = defaultdict(lambda: defaultdict(int))
    for p, g in zip(predictions, ground_truth):
        p_norm = normalize_classification(p)
        g_norm = normalize_classification(g)
        if p_norm and g_norm:
            matrix[g_norm][p_norm] += 1
    return {g: dict(preds) for g, preds in matrix.items()}


def print_comparison_table(tool_metrics: dict[str, dict]):
    """Print summary comparison table."""
    print("\n" + "=" * 90)
    print("4-WAY TOOL COMPARISON: AIVA vs InterVar vs BIAS-2015")
    print("=" * 90)

    # Sort by exact accuracy
    sorted_tools = sorted(tool_metrics.keys(),
                         key=lambda t: tool_metrics[t].get("exact_accuracy", 0),
                         reverse=True)

    print(f"\n{'Tool':<20} {'N Valid':>8} {'Exact':>10} {'Direct':>10} {'Macro F1':>10} {'Dir F1':>10}")
    print("-" * 90)

    for tool in sorted_tools:
        m = tool_metrics[tool]
        if "error" in m:
            print(f"{tool:<20} {'ERROR':>8}")
            continue
        print(f"{tool:<20} {m['n_valid']:>8} {m['exact_accuracy']*100:>9.1f}% "
              f"{m['directional_accuracy']*100:>9.1f}% {m['macro_f1_5class']*100:>9.1f}% "
              f"{m['macro_f1_3class']*100:>9.1f}%")

    print("-" * 90)


def print_per_class_comparison(tool_metrics: dict[str, dict]):
    """Print per-class F1 scores for all tools."""
    print("\n" + "=" * 90)
    print("PER-CLASS F1 SCORES (5-class)")
    print("=" * 90)

    tools = list(tool_metrics.keys())

    # Header
    print(f"\n{'Class':<25}", end="")
    for tool in tools:
        short = tool[:12]
        print(f"{short:>14}", end="")
    print()
    print("-" * (25 + 14 * len(tools)))

    for cls in CLASSIFICATION_LABELS:
        print(f"{cls:<25}", end="")
        for tool in tools:
            m = tool_metrics[tool]
            if "error" in m:
                print(f"{'N/A':>14}", end="")
            else:
                f1 = m.get("per_class", {}).get(cls, {}).get("f1", 0)
                print(f"{f1*100:>12.1f}%", end="")
        print()

    print("-" * (25 + 14 * len(tools)))
    print(f"{'Macro F1':<25}", end="")
    for tool in tools:
        m = tool_metrics[tool]
        if "error" in m:
            print(f"{'N/A':>14}", end="")
        else:
            print(f"{m['macro_f1_5class']*100:>12.1f}%", end="")
    print()


def print_directional_comparison(tool_metrics: dict[str, dict]):
    """Print directional (3-class) metrics for all tools."""
    print("\n" + "=" * 90)
    print("DIRECTIONAL METRICS (3-class: Pathogenic / VUS / Benign)")
    print("=" * 90)

    tools = list(tool_metrics.keys())

    for direction in DIRECTION_LABELS:
        print(f"\n{direction.upper()}:")
        print(f"  {'Tool':<20} {'Precision':>12} {'Recall':>12} {'F1':>12}")
        print("  " + "-" * 60)
        for tool in tools:
            m = tool_metrics[tool]
            if "error" in m:
                print(f"  {tool:<20} {'N/A':>12}")
            else:
                dm = m.get("per_direction", {}).get(direction, {})
                prec = dm.get("precision", 0)
                rec = dm.get("recall", 0)
                f1 = dm.get("f1", 0)
                print(f"  {tool:<20} {prec*100:>11.1f}% {rec*100:>11.1f}% {f1*100:>11.1f}%")


def print_criteria_analysis(unified_data: list[dict], aiva_by_id: dict):
    """Analyze criteria usage across tools."""
    print("\n" + "=" * 90)
    print("CRITERIA ANALYSIS")
    print("=" * 90)

    # Collect criteria usage
    gt_criteria = defaultdict(int)
    intervar_criteria = defaultdict(int)
    bias_criteria = defaultdict(int)
    aiva_criteria = defaultdict(int)

    for v in unified_data:
        for c in v.get("criteria_met", []):
            gt_criteria[c] += 1
        for c in v.get("intervar_criteria", []):
            intervar_criteria[c] += 1
        for c in v.get("bias_criteria", []):
            bias_criteria[c] += 1

        vid = v.get("id")
        if vid in aiva_by_id:
            for c in aiva_by_id[vid].get("criteria", []):
                aiva_criteria[c] += 1

    # Get all unique criteria
    all_criteria = sorted(set(gt_criteria.keys()) | set(intervar_criteria.keys()) |
                         set(bias_criteria.keys()) | set(aiva_criteria.keys()))

    if not all_criteria:
        print("\nNo criteria data available.")
        return

    print(f"\n{'Criterion':<12} {'eRepo GT':>10} {'InterVar':>10} {'BIAS-2015':>10} {'AIVA':>10}")
    print("-" * 60)

    for crit in all_criteria[:20]:  # Top 20 criteria
        print(f"{crit:<12} {gt_criteria.get(crit, 0):>10} {intervar_criteria.get(crit, 0):>10} "
              f"{bias_criteria.get(crit, 0):>10} {aiva_criteria.get(crit, 0):>10}")

    if len(all_criteria) > 20:
        print(f"... and {len(all_criteria) - 20} more criteria")


def save_detailed_results(unified_data: list[dict], aiva_by_id: dict, output_path: Path):
    """Save detailed per-variant comparison."""
    results = []

    for v in unified_data:
        vid = v.get("id")
        aiva = aiva_by_id.get(vid, {})

        result = {
            "variant_id": vid,
            "variant": v.get("variation"),
            "gene": v.get("gene_symbol"),
            "ground_truth": v.get("classification"),
            "ground_truth_criteria": v.get("criteria_met", []),
            "intervar": v.get("intervar_classification"),
            "intervar_criteria": v.get("intervar_criteria", []),
            "bias": v.get("bias_classification"),
            "bias_criteria": v.get("bias_criteria", []),
            "aiva": aiva.get("classification"),
            "aiva_criteria": aiva.get("criteria", []),
            "aiva_model": aiva.get("model")
        }

        # Add match indicators
        gt = normalize_classification(result["ground_truth"])
        result["intervar_match"] = normalize_classification(result["intervar"]) == gt
        result["bias_match"] = normalize_classification(result["bias"]) == gt
        result["aiva_match"] = normalize_classification(result["aiva"]) == gt if result["aiva"] else None

        results.append(result)

    with open(output_path, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nSaved detailed results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="4-way tool comparison")
    parser.add_argument("--aiva-results", nargs="+", required=True,
                       help="AIVA classification result files (JSONL)")
    parser.add_argument("--unified", default=str(DATA_DIR / "bias_unified.jsonl"),
                       help="Unified data file with InterVar/BIAS predictions")
    parser.add_argument("--output", help="Output file for detailed results")

    args = parser.parse_args()

    # Load unified data (contains ground truth, InterVar, BIAS-2015)
    unified_path = Path(args.unified)
    print(f"Loading unified data from {unified_path}")
    unified_data = load_jsonl(unified_path)
    print(f"  Loaded {len(unified_data)} variants")

    # Load AIVA results
    aiva_paths = [Path(p) for p in args.aiva_results]
    print(f"Loading AIVA results from {len(aiva_paths)} file(s)")
    aiva_by_id = load_aiva_results(aiva_paths)
    print(f"  Loaded {len(aiva_by_id)} AIVA predictions")

    # Build unified data index
    unified_by_id = {v.get("id"): v for v in unified_data}

    # FAIR COMPARISON: Only compare on variants where AIVA has predictions
    aiva_variant_ids = set(aiva_by_id.keys())
    print(f"\n=== FAIR COMPARISON (on {len(aiva_variant_ids)} AIVA-predicted variants) ===")

    # Extract predictions for variants AIVA predicted
    ground_truth_fair = []
    intervar_preds_fair = []
    bias_preds_fair = []
    aiva_preds_fair = []

    for vid in aiva_variant_ids:
        v = unified_by_id.get(vid)
        if not v:
            continue

        ground_truth_fair.append(v.get("classification"))
        intervar_preds_fair.append(v.get("intervar_classification", ""))
        bias_preds_fair.append(v.get("bias_classification", ""))
        aiva_preds_fair.append(aiva_by_id[vid].get("classification", ""))

    # Calculate metrics for fair comparison
    tool_metrics_fair = {
        "AIVA": calculate_tool_metrics(aiva_preds_fair, ground_truth_fair),
        "InterVar": calculate_tool_metrics(intervar_preds_fair, ground_truth_fair),
        "BIAS-2015": calculate_tool_metrics(bias_preds_fair, ground_truth_fair)
    }

    # Print fair comparison
    print_comparison_table(tool_metrics_fair)
    print_per_class_comparison(tool_metrics_fair)
    print_directional_comparison(tool_metrics_fair)

    # FULL DATASET comparison for reference
    print("\n\n" + "=" * 90)
    print(f"REFERENCE: Full dataset metrics (all {len(unified_data)} variants)")
    print("=" * 90)

    ground_truth_all = []
    intervar_preds_all = []
    bias_preds_all = []

    for v in unified_data:
        ground_truth_all.append(v.get("classification"))
        intervar_preds_all.append(v.get("intervar_classification", ""))
        bias_preds_all.append(v.get("bias_classification", ""))

    tool_metrics_full = {
        "InterVar (full)": calculate_tool_metrics(intervar_preds_all, ground_truth_all),
        "BIAS-2015 (full)": calculate_tool_metrics(bias_preds_all, ground_truth_all)
    }

    print(f"\n{'Tool':<20} {'N Valid':>8} {'Exact':>10} {'Direct':>10} {'Macro F1':>10} {'Dir F1':>10}")
    print("-" * 90)
    for tool, m in tool_metrics_full.items():
        print(f"{tool:<20} {m['n_valid']:>8} {m['exact_accuracy']*100:>9.1f}% "
              f"{m['directional_accuracy']*100:>9.1f}% {m['macro_f1_5class']*100:>9.1f}% "
              f"{m['macro_f1_3class']*100:>9.1f}%")

    # Criteria analysis (on AIVA subset)
    print_criteria_analysis(
        [unified_by_id[vid] for vid in aiva_variant_ids if vid in unified_by_id],
        aiva_by_id
    )

    # Save detailed results
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = RESULTS_DIR / "tool_comparison_detailed.jsonl"

    save_detailed_results(unified_data, aiva_by_id, output_path)

    # Summary
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)

    print(f"\nFair comparison on {len(aiva_variant_ids)} variants:")

    print(f"\nBest exact accuracy: ", end="")
    best = max(tool_metrics_fair.items(), key=lambda x: x[1].get("exact_accuracy", 0))
    print(f"{best[0]} ({best[1]['exact_accuracy']*100:.1f}%)")

    print(f"Best directional accuracy: ", end="")
    best = max(tool_metrics_fair.items(), key=lambda x: x[1].get("directional_accuracy", 0))
    print(f"{best[0]} ({best[1]['directional_accuracy']*100:.1f}%)")


if __name__ == "__main__":
    main()
