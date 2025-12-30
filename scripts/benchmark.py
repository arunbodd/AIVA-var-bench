"""
Calculate benchmark metrics from classification results.

Usage:
    python scripts/benchmark.py                                    # Use latest results
    python scripts/benchmark.py --input results/classifications_xxx.jsonl
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    RESULTS_DIR, CLASSIFICATION_LABELS, CLASSIFICATION_TO_DIRECTION, DIRECTION_LABELS
)


def load_results(filepath: Path) -> list[dict]:
    """Load classification results from JSONL file."""
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def normalize_classification(classification: str) -> str:
    """Normalize classification string for comparison."""
    if not classification:
        return ""

    c = classification.strip()
    lower = c.lower()

    # Check VUS patterns FIRST (before pathogenic/benign which are substrings)
    # AIVA returns "VUS (leaning pathogenic)" or "VUS (leaning benign)"
    if lower.startswith("vus") or "uncertain significance" in lower:
        return "Uncertain Significance"

    # Then check compound terms before simple ones
    if "likely pathogenic" in lower:
        return "Likely Pathogenic"
    if "likely benign" in lower:
        return "Likely Benign"

    # Finally check simple terms
    if "pathogenic" in lower:
        return "Pathogenic"
    if "benign" in lower:
        return "Benign"

    return c


def get_direction(classification: str) -> str:
    """Get directional category (pathogenic/vus/benign)."""
    normalized = normalize_classification(classification)
    return CLASSIFICATION_TO_DIRECTION.get(normalized, "unknown")


def normalize_criterion(criterion: str) -> str:
    """
    Normalize ACMG criterion code by stripping strength modifiers.

    Examples:
        PM2_Supporting -> PM2
        PS3_Moderate -> PS3
        PVS1_moderate -> PVS1
        PP4_Moderate -> PP4
    """
    if not criterion:
        return ""

    # Common strength modifiers (case-insensitive)
    modifiers = [
        "_supporting", "_moderate", "_strong", "_very_strong",
        "_very", "_standalone"
    ]

    c = criterion.strip()
    lower = c.lower()

    for mod in modifiers:
        if mod in lower:
            # Find the position and remove the modifier
            idx = lower.find(mod)
            c = c[:idx]
            break

    # Uppercase the base code for consistency
    return c.upper()


def get_criterion_type(criterion: str) -> str:
    """
    Get the evidence direction for an ACMG criterion.

    Returns:
        'pathogenic' for PVS, PS, PM, PP criteria
        'benign' for BA, BS, BP criteria
        'unknown' for unrecognized criteria
    """
    base = normalize_criterion(criterion)

    if base.startswith(('PVS', 'PS', 'PM', 'PP')):
        return 'pathogenic'
    elif base.startswith(('BA', 'BS', 'BP')):
        return 'benign'
    return 'unknown'


def calculate_criteria_metrics(results: list[dict]) -> dict:
    """
    Calculate detailed ACMG criteria metrics.

    Returns metrics including:
    - Per-criterion precision/recall/F1
    - Normalized Jaccard similarity
    - Evidence direction agreement
    """
    # Collect all criteria
    all_gt_criteria = set()
    all_pred_criteria = set()

    # For per-criterion metrics
    criterion_tp = Counter()  # True positives per criterion
    criterion_fp = Counter()  # False positives per criterion
    criterion_fn = Counter()  # False negatives per criterion

    # For Jaccard with normalized criteria
    jaccard_scores = []

    # For direction agreement
    direction_matches = 0
    direction_total = 0

    for r in results:
        if r.get("error"):
            continue

        gt_raw = r.get("ground_truth_criteria", [])
        pred_raw = r.get("aiva_criteria", [])

        # Normalize criteria
        gt_normalized = set(normalize_criterion(c) for c in gt_raw if c)
        pred_normalized = set(normalize_criterion(c) for c in pred_raw if c)

        all_gt_criteria.update(gt_normalized)
        all_pred_criteria.update(pred_normalized)

        # Calculate Jaccard for this sample
        if gt_normalized or pred_normalized:
            intersection = len(gt_normalized & pred_normalized)
            union = len(gt_normalized | pred_normalized)
            jaccard = intersection / union if union > 0 else 0
            jaccard_scores.append(jaccard)

        # Per-criterion TP/FP/FN
        for c in gt_normalized & pred_normalized:
            criterion_tp[c] += 1
        for c in pred_normalized - gt_normalized:
            criterion_fp[c] += 1
        for c in gt_normalized - pred_normalized:
            criterion_fn[c] += 1

        # Direction agreement: compare pathogenic vs benign evidence counts
        gt_path = sum(1 for c in gt_normalized if get_criterion_type(c) == 'pathogenic')
        gt_benign = sum(1 for c in gt_normalized if get_criterion_type(c) == 'benign')
        pred_path = sum(1 for c in pred_normalized if get_criterion_type(c) == 'pathogenic')
        pred_benign = sum(1 for c in pred_normalized if get_criterion_type(c) == 'benign')

        # Direction matches if both lean the same way (or both neutral)
        gt_direction = 'pathogenic' if gt_path > gt_benign else ('benign' if gt_benign > gt_path else 'neutral')
        pred_direction = 'pathogenic' if pred_path > pred_benign else ('benign' if pred_benign > pred_path else 'neutral')

        if gt_direction == pred_direction:
            direction_matches += 1
        direction_total += 1

    # Calculate per-criterion precision/recall/F1
    all_criteria = sorted(all_gt_criteria | all_pred_criteria)
    per_criterion = {}

    for c in all_criteria:
        tp = criterion_tp[c]
        fp = criterion_fp[c]
        fn = criterion_fn[c]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        per_criterion[c] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": tp + fn,  # Times it appeared in ground truth
            "predicted": tp + fp,  # Times AIVA predicted it
            "type": get_criterion_type(c)
        }

    # Aggregate by criterion type (pathogenic vs benign)
    path_criteria = [c for c in all_criteria if get_criterion_type(c) == 'pathogenic']
    benign_criteria = [c for c in all_criteria if get_criterion_type(c) == 'benign']

    def aggregate_metrics(criteria_list):
        if not criteria_list:
            return {"precision": 0, "recall": 0, "f1": 0}
        total_tp = sum(criterion_tp[c] for c in criteria_list)
        total_fp = sum(criterion_fp[c] for c in criteria_list)
        total_fn = sum(criterion_fn[c] for c in criteria_list)
        p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0
        return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)}

    return {
        "avg_jaccard_normalized": round(sum(jaccard_scores) / len(jaccard_scores), 4) if jaccard_scores else 0,
        "direction_agreement": round(direction_matches / direction_total, 4) if direction_total > 0 else 0,
        "samples_evaluated": len(jaccard_scores),
        "unique_criteria_in_ground_truth": len(all_gt_criteria),
        "unique_criteria_in_predictions": len(all_pred_criteria),
        "pathogenic_evidence_metrics": aggregate_metrics(path_criteria),
        "benign_evidence_metrics": aggregate_metrics(benign_criteria),
        "per_criterion": per_criterion
    }


def calculate_metrics(results: list[dict]) -> dict:
    """Calculate all benchmark metrics."""
    total = len(results)
    errors = sum(1 for r in results if r.get("error"))
    successful = total - errors

    # Filter successful results
    valid_results = [r for r in results if not r.get("error") and r.get("aiva_classification")]

    # Exact match accuracy
    exact_matches = 0
    directional_matches = 0

    ground_truth = []
    predictions = []
    ground_directions = []
    pred_directions = []

    for r in valid_results:
        gt = normalize_classification(r.get("ground_truth", ""))
        pred = normalize_classification(r.get("aiva_classification", ""))

        if gt and pred:
            ground_truth.append(gt)
            predictions.append(pred)

            if gt == pred:
                exact_matches += 1

            gt_dir = get_direction(gt)
            pred_dir = get_direction(pred)
            ground_directions.append(gt_dir)
            pred_directions.append(pred_dir)

            if gt_dir == pred_dir:
                directional_matches += 1

    n_compared = len(ground_truth)

    # Per-class metrics (5-class)
    per_class = {}
    for cls in CLASSIFICATION_LABELS:
        tp = sum(1 for g, p in zip(ground_truth, predictions) if g == cls and p == cls)
        fp = sum(1 for g, p in zip(ground_truth, predictions) if g != cls and p == cls)
        fn = sum(1 for g, p in zip(ground_truth, predictions) if g == cls and p != cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        per_class[cls] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for g in ground_truth if g == cls),
            "predicted": sum(1 for p in predictions if p == cls),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn
        }

    # Confusion matrix (5-class)
    confusion_5class = {gt: {pred: 0 for pred in CLASSIFICATION_LABELS} for gt in CLASSIFICATION_LABELS}
    for g, p in zip(ground_truth, predictions):
        if g in confusion_5class and p in CLASSIFICATION_LABELS:
            confusion_5class[g][p] += 1

    # Directional metrics (3-class)
    per_direction = {}
    for d in DIRECTION_LABELS:
        tp = sum(1 for g, p in zip(ground_directions, pred_directions) if g == d and p == d)
        fp = sum(1 for g, p in zip(ground_directions, pred_directions) if g != d and p == d)
        fn = sum(1 for g, p in zip(ground_directions, pred_directions) if g == d and p != d)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        per_direction[d] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for g in ground_directions if g == d)
        }

    # Directional confusion matrix (3-class)
    confusion_3class = {g: {p: 0 for p in DIRECTION_LABELS} for g in DIRECTION_LABELS}
    for g, p in zip(ground_directions, pred_directions):
        if g in confusion_3class and p in DIRECTION_LABELS:
            confusion_3class[g][p] += 1

    # Detailed criteria analysis
    criteria_metrics = calculate_criteria_metrics(results)

    # Execution time stats
    exec_times = [r["execution_time_ms"] for r in valid_results if r.get("execution_time_ms")]
    avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0
    max_exec_time = max(exec_times) if exec_times else 0
    min_exec_time = min(exec_times) if exec_times else 0

    # Error analysis
    error_types = Counter(r.get("error", "")[:50] for r in results if r.get("error"))

    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_variants": total,
            "successful": successful,
            "errors": errors,
            "compared": n_compared,
            "error_rate": round(errors / total, 4) if total > 0 else 0,
        },
        "accuracy": {
            "exact_match": round(exact_matches / n_compared, 4) if n_compared > 0 else 0,
            "directional": round(directional_matches / n_compared, 4) if n_compared > 0 else 0,
            "exact_matches": exact_matches,
            "directional_matches": directional_matches,
        },
        "per_class_metrics": per_class,
        "per_direction_metrics": per_direction,
        "confusion_matrix_5class": confusion_5class,
        "confusion_matrix_3class": confusion_3class,
        "criteria_analysis": criteria_metrics,
        "execution_time": {
            "avg_ms": round(avg_exec_time, 1),
            "min_ms": min_exec_time,
            "max_ms": max_exec_time
        },
        "error_types": dict(error_types.most_common(10))
    }


def print_report(metrics: dict):
    """Print human-readable benchmark report."""
    print("\n" + "=" * 70)
    print("AIVA VARIANT CLASSIFICATION BENCHMARK RESULTS")
    print("=" * 70)

    s = metrics["summary"]
    print(f"\nDataset: {s['total_variants']} variants")
    print(f"  Successful: {s['successful']} | Errors: {s['errors']} ({s['error_rate']*100:.1f}%)")
    print(f"  Compared: {s['compared']}")

    a = metrics["accuracy"]
    print(f"\n{'='*30} ACCURACY {'='*30}")
    print(f"  EXACT MATCH (5-class):    {a['exact_match']*100:6.2f}%  ({a['exact_matches']}/{s['compared']})")
    print(f"  DIRECTIONAL (3-class):    {a['directional']*100:6.2f}%  ({a['directional_matches']}/{s['compared']})")

    print(f"\n{'='*30} PER-CLASS METRICS {'='*21}")
    print(f"  {'Class':<25} {'Prec':>8} {'Recall':>8} {'F1':>8} {'Support':>8}")
    print(f"  {'-'*60}")
    for cls in CLASSIFICATION_LABELS:
        m = metrics["per_class_metrics"].get(cls, {})
        print(f"  {cls:<25} {m.get('precision', 0):>8.3f} {m.get('recall', 0):>8.3f} {m.get('f1', 0):>8.3f} {m.get('support', 0):>8}")

    # Macro averages
    class_metrics = metrics["per_class_metrics"]
    valid_classes = [c for c in CLASSIFICATION_LABELS if class_metrics.get(c, {}).get("support", 0) > 0]
    if valid_classes:
        macro_p = sum(class_metrics[c]["precision"] for c in valid_classes) / len(valid_classes)
        macro_r = sum(class_metrics[c]["recall"] for c in valid_classes) / len(valid_classes)
        macro_f1 = sum(class_metrics[c]["f1"] for c in valid_classes) / len(valid_classes)
        print(f"  {'-'*60}")
        print(f"  {'Macro Average':<25} {macro_p:>8.3f} {macro_r:>8.3f} {macro_f1:>8.3f}")

    print(f"\n{'='*30} DIRECTIONAL METRICS {'='*19}")
    print(f"  {'Direction':<15} {'Prec':>8} {'Recall':>8} {'F1':>8} {'Support':>8}")
    print(f"  {'-'*50}")
    for d in DIRECTION_LABELS:
        m = metrics["per_direction_metrics"].get(d, {})
        print(f"  {d:<15} {m.get('precision', 0):>8.3f} {m.get('recall', 0):>8.3f} {m.get('f1', 0):>8.3f} {m.get('support', 0):>8}")

    print(f"\n{'='*30} CONFUSION MATRIX (3-class) {'='*12}")
    print("                    Predicted")
    print(f"  {'Actual':<12}", end="")
    for d in DIRECTION_LABELS:
        print(f"{d:>12}", end="")
    print()
    print(f"  {'-'*48}")
    for gt in DIRECTION_LABELS:
        print(f"  {gt:<12}", end="")
        for pred in DIRECTION_LABELS:
            val = metrics["confusion_matrix_3class"].get(gt, {}).get(pred, 0)
            print(f"{val:>12}", end="")
        print()

    ca = metrics["criteria_analysis"]
    print(f"\n{'='*30} CRITERIA ANALYSIS {'='*21}")
    print(f"  Avg Jaccard (normalized): {ca['avg_jaccard_normalized']:.3f}")
    print(f"  Evidence Direction Agreement: {ca['direction_agreement']*100:.1f}%")
    print(f"  Samples evaluated: {ca['samples_evaluated']}")
    print(f"  Unique criteria - Ground truth: {ca['unique_criteria_in_ground_truth']} | AIVA: {ca['unique_criteria_in_predictions']}")

    print(f"\n  Aggregate by Evidence Type:")
    pm = ca['pathogenic_evidence_metrics']
    bm = ca['benign_evidence_metrics']
    print(f"    Pathogenic (PVS/PS/PM/PP): P={pm['precision']:.3f} R={pm['recall']:.3f} F1={pm['f1']:.3f}")
    print(f"    Benign (BA/BS/BP):         P={bm['precision']:.3f} R={bm['recall']:.3f} F1={bm['f1']:.3f}")

    # Show top criteria by support
    per_crit = ca.get('per_criterion', {})
    if per_crit:
        # Sort by support (times in ground truth)
        sorted_criteria = sorted(per_crit.items(), key=lambda x: x[1]['support'], reverse=True)
        print(f"\n  Per-Criterion Metrics (top 15 by support):")
        print(f"  {'Criterion':<10} {'Type':<6} {'Prec':>6} {'Recall':>6} {'F1':>6} {'TP':>4} {'FP':>4} {'FN':>4} {'Supp':>4}")
        print(f"  {'-'*62}")
        for crit, m in sorted_criteria[:15]:
            ctype = 'PATH' if m['type'] == 'pathogenic' else ('BEN' if m['type'] == 'benign' else '?')
            print(f"  {crit:<10} {ctype:<6} {m['precision']:>6.3f} {m['recall']:>6.3f} {m['f1']:>6.3f} {m['tp']:>4} {m['fp']:>4} {m['fn']:>4} {m['support']:>4}")

    et = metrics["execution_time"]
    print(f"\n{'='*30} EXECUTION TIME {'='*24}")
    print(f"  Average: {et['avg_ms']:.0f}ms | Min: {et['min_ms']}ms | Max: {et['max_ms']}ms")

    if metrics.get("error_types"):
        print(f"\n{'='*30} ERROR TYPES {'='*27}")
        for err, count in metrics["error_types"].items():
            print(f"  {count:>4}x {err[:60]}")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Calculate benchmark metrics")
    parser.add_argument("--input", help="Input JSONL file with classification results")
    parser.add_argument("--output", help="Output JSON file for metrics")
    parser.add_argument("--quiet", action="store_true", help="Don't print report")

    args = parser.parse_args()

    # Find input file
    if args.input:
        input_path = Path(args.input)
    else:
        # Find most recent results file
        result_files = list(RESULTS_DIR.glob("classifications_*.jsonl"))
        if not result_files:
            print("Error: No result files found. Run classify.py first.")
            sys.exit(1)
        input_path = max(result_files, key=lambda p: p.stat().st_mtime)
        print(f"Using most recent results: {input_path}")

    # Load results
    results = load_results(input_path)
    print(f"Loaded {len(results)} results")

    # Calculate metrics
    metrics = calculate_metrics(results)

    # Print report
    if not args.quiet:
        print_report(metrics)

    # Save metrics
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = RESULTS_DIR / f"metrics_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved metrics to {output_path}")


if __name__ == "__main__":
    main()
