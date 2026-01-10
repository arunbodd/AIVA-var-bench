#!/usr/bin/env python3
"""
Calculate BIAS-2015 style metrics (Sensitivity, Specificity, Precision, F1)
stratified by disease category for each model, including BIAS-2015 and InterVar baselines.

Usage:
    python scripts/metrics_by_category.py Results_500_benchmarked/classifications_*.jsonl
    python scripts/metrics_by_category.py Results_500_benchmarked/classifications_*.jsonl --output-dir Results_500_benchmarked
    python scripts/metrics_by_category.py Results_500_benchmarked/classifications_*.jsonl --unified data/bias_unified.jsonl
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DIRECTION_LABELS, DATA_DIR

# =============================================================================
# ClinGen Expert Panel (VCEP) to Broader Disease Category Mapping
# =============================================================================

VCEP_TO_CATEGORY = {
    # Cancer Predisposition
    "Myeloid Malignancy VCEP": "Cancer Predisposition",
    "CDH1 VCEP": "Cancer Predisposition",
    "PTEN VCEP": "Cancer Predisposition",
    "TP53 VCEP": "Cancer Predisposition",
    "VHL VCEP": "Cancer Predisposition",
    "Hereditary Breast, Ovarian and Pancreatic Cancer VCEP": "Cancer Predisposition",
    "ENIGMA BRCA1 and BRCA2 VCEP": "Cancer Predisposition",
    "InSiGHT Hereditary Colorectal Cancer/Polyposis VCEP": "Cancer Predisposition",
    "DICER1 and miRNA-Processing Gene VCEP": "Cancer Predisposition",
    
    # Metabolic Disorders
    "Monogenic Diabetes VCEP": "Metabolic Disorders",
    "Phenylketonuria VCEP": "Metabolic Disorders",
    "Familial Hypercholesterolemia VCEP": "Metabolic Disorders",
    "Lysosomal Diseases VCEP": "Metabolic Disorders",
    "Cerebral Creatine Deficiency Syndromes VCEP": "Metabolic Disorders",
    "ACADVL VCEP": "Metabolic Disorders",
    "Mitochondrial Diseases VCEP": "Metabolic Disorders",
    
    # Cardiovascular Disorders
    "Cardiomyopathy VCEP": "Cardiovascular Disorders",
    "FBN1 VCEP": "Cardiovascular Disorders",
    "Pulmonary Hypertension VCEP": "Cardiovascular Disorders",
    
    # Hematologic Disorders
    "Platelet Disorders VCEP": "Hematologic Disorders",
    "von Willebrand Disease  VCEP": "Hematologic Disorders",
    "Coagulation Factor Deficiency VCEP": "Hematologic Disorders",
    "Thrombosis VCEP": "Hematologic Disorders",
    
    # Immunodeficiency Disorders
    "Severe Combined Immunodeficiency Disease  VCEP": "Immunodeficiency Disorders",
    
    # Neurodevelopmental Disorders
    "Rett and Angelman-like Disorders VCEP": "Neurodevelopmental Disorders",
    
    # Neuromuscular Disorders
    "Malignant Hyperthermia Susceptibility VCEP": "Neuromuscular Disorders",
    "Congenital Myopathies VCEP": "Neuromuscular Disorders",
    "Limb Girdle Muscular Dystrophy VCEP": "Neuromuscular Disorders",
    
    # Ophthalmologic Disorders
    "Glaucoma VCEP": "Ophthalmologic Disorders",
    "Leber Congenital Amaurosis/early onset Retinal Dystrophy VCEP": "Ophthalmologic Disorders",
    "X-linked Inherited Retinal Disease VCEP": "Ophthalmologic Disorders",
    "ABCA4 VCEP": "Ophthalmologic Disorders",
    
    # Hearing Disorders
    "Hearing Loss VCEP": "Hearing Disorders",
    
    # RASopathies
    "RASopathy VCEP": "RASopathies",
}

CATEGORY_ORDER = [
    "Cancer Predisposition",
    "Metabolic Disorders",
    "Cardiovascular Disorders",
    "Hematologic Disorders",
    "Immunodeficiency Disorders",
    "Neurodevelopmental Disorders",
    "Neuromuscular Disorders",
    "Ophthalmologic Disorders",
    "Hearing Disorders",
    "RASopathies",
    "Other",
]


def normalize_classification(cls: str) -> str:
    """Normalize classification string."""
    if not cls:
        return ""
    cls_lower = cls.lower().strip()
    
    # Handle VUS variants
    if "uncertain" in cls_lower or cls_lower.startswith("vus"):
        return "Uncertain Significance"
    if "pathogenic" in cls_lower and "likely" in cls_lower:
        return "Likely Pathogenic"
    if "benign" in cls_lower and "likely" in cls_lower:
        return "Likely Benign"
    if "pathogenic" in cls_lower:
        return "Pathogenic"
    if "benign" in cls_lower:
        return "Benign"
    return cls


def get_direction(cls: str) -> str:
    """Get 3-class direction from 5-class classification."""
    cls_norm = normalize_classification(cls)
    if cls_norm in ["Pathogenic", "Likely Pathogenic"]:
        return "pathogenic"
    elif cls_norm in ["Benign", "Likely Benign"]:
        return "benign"
    elif cls_norm == "Uncertain Significance":
        return "vus"
    return "unknown"


def get_category(expert_panel: str) -> str:
    """Map Expert Panel to disease category."""
    if not expert_panel:
        return "Other"
    return VCEP_TO_CATEGORY.get(expert_panel.strip(), "Other")


def calculate_metrics(tp: int, fp: int, fn: int, tn: int) -> Dict[str, float]:
    """Calculate sensitivity, specificity, precision, F1."""
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1 = 2 * precision * sensitivity / (precision + sensitivity) if (precision + sensitivity) > 0 else 0
    
    return {
        "sensitivity": round(sensitivity * 100, 2),
        "specificity": round(specificity * 100, 2),
        "precision": round(precision * 100, 2),
        "f1": round(f1 * 100, 2),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn
    }


def calculate_category_metrics(variants: List[Dict], model: str, pred_field: str = "aiva_classification") -> Dict[str, Dict[str, Dict]]:
    """
    Calculate BIAS-style metrics for each category for a given model/tool.
    
    Args:
        variants: List of variant dictionaries
        model: Model name to filter by (or None for baseline tools)
        pred_field: Field name containing the prediction (e.g., "aiva_classification", "bias_classification", "intervar_classification")
    
    Returns: {category: {direction: {metrics}}}
    """
    # Group variants by category
    by_category = defaultdict(list)
    for v in variants:
        # For AIVA models, filter by model_used
        if model and pred_field == "aiva_classification":
            if v.get("model_used") != model:
                continue
        
        cat = get_category(v.get("expert_panel", ""))
        by_category[cat].append(v)
    
    results = {}
    
    for cat, cat_variants in by_category.items():
        # Get predictions and ground truth (both normalized and directional)
        predictions_dir = []
        ground_truths_dir = []
        predictions_exact = []
        ground_truths_exact = []
        
        for v in cat_variants:
            pred = v.get(pred_field, "")
            gt = v.get("ground_truth", "") or v.get("classification", "")  # Handle both formats
            
            if pred and gt and not v.get("error"):
                pred_norm = normalize_classification(pred)
                gt_norm = normalize_classification(gt)
                pred_dir = get_direction(pred)
                gt_dir = get_direction(gt)
                
                if pred_dir != "unknown" and gt_dir != "unknown":
                    predictions_dir.append(pred_dir)
                    ground_truths_dir.append(gt_dir)
                    predictions_exact.append(pred_norm)
                    ground_truths_exact.append(gt_norm)
        
        n_total = len(predictions_dir)
        if n_total == 0:
            continue
        
        # Calculate metrics for each direction (P/LP, VUS, B/LB)
        cat_metrics = {"n_variants": n_total}
        
        for direction in ["pathogenic", "vus", "benign"]:
            tp = sum(1 for g, p in zip(ground_truths_dir, predictions_dir) if g == direction and p == direction)
            fp = sum(1 for g, p in zip(ground_truths_dir, predictions_dir) if g != direction and p == direction)
            fn = sum(1 for g, p in zip(ground_truths_dir, predictions_dir) if g == direction and p != direction)
            tn = n_total - tp - fp - fn
            
            cat_metrics[direction] = calculate_metrics(tp, fp, fn, tn)
        
        # Overall directional accuracy (3-class)
        correct_dir = sum(1 for g, p in zip(ground_truths_dir, predictions_dir) if g == p)
        cat_metrics["directional_accuracy"] = round(correct_dir / n_total * 100, 2) if n_total > 0 else 0
        
        # Exact accuracy (5-class)
        correct_exact = sum(1 for g, p in zip(ground_truths_exact, predictions_exact) if g == p)
        cat_metrics["exact_accuracy"] = round(correct_exact / n_total * 100, 2) if n_total > 0 else 0
        
        # Calculate metrics for each EXACT 5-class classification
        exact_classes = ["Pathogenic", "Likely Pathogenic", "Uncertain Significance", "Likely Benign", "Benign"]
        for exact_class in exact_classes:
            tp = sum(1 for g, p in zip(ground_truths_exact, predictions_exact) if g == exact_class and p == exact_class)
            fp = sum(1 for g, p in zip(ground_truths_exact, predictions_exact) if g != exact_class and p == exact_class)
            fn = sum(1 for g, p in zip(ground_truths_exact, predictions_exact) if g == exact_class and p != exact_class)
            tn = n_total - tp - fp - fn
            
            cat_metrics[f"exact_{exact_class}"] = calculate_metrics(tp, fp, fn, tn)
        
        results[cat] = cat_metrics
    
    return results


def load_jsonl(filepath: Path) -> List[Dict]:
    """Load JSONL file."""
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def print_category_metrics(all_metrics: Dict[str, Dict[str, Dict]], output_file=None):
    """Print BIAS-style metrics by category for each model."""
    
    lines = []
    
    def output(text=""):
        print(text)
        lines.append(text)
    
    # Sort models: baselines first, then AIVA models
    def model_sort_key(m):
        if m == "InterVar":
            return (0, m)
        elif m == "BIAS-2015":
            return (1, m)
        else:
            return (2, m)
    
    models = sorted(all_metrics.keys(), key=model_sort_key)
    
    categories = set()
    for model_metrics in all_metrics.values():
        categories.update(model_metrics.keys())
    
    # Sort categories by predefined order
    def sort_key(cat):
        try:
            return CATEGORY_ORDER.index(cat)
        except ValueError:
            return len(CATEGORY_ORDER)
    
    categories = sorted(categories, key=sort_key)
    
    output("\n" + "=" * 145)
    output("BIAS-2015 STYLE METRICS BY DISEASE CATEGORY (Comparing AIVA vs BIAS-2015 vs InterVar)")
    output("=" * 145)
    
    # For each category, print metrics for all models
    for cat in categories:
        output(f"\n{'─' * 145}")
        output(f"CATEGORY: {cat}")
        output(f"{'─' * 145}")
        
        # Header
        output(f"\n{'Tool/Model':<45} {'N':>5} {'DirAcc':>8} │ {'P/LP Sens':>9} {'Spec':>8} {'Prec':>8} {'F1':>8} │ {'VUS Sens':>9} {'Spec':>8} {'Prec':>8} {'F1':>8} │ {'B/LB Sens':>9} {'Spec':>8} {'Prec':>8} {'F1':>8}")
        output("─" * 145)
        
        for model in models:
            if cat not in all_metrics[model]:
                continue
            
            m = all_metrics[model][cat]
            n = m.get("n_variants", 0)
            dir_acc = m.get("directional_accuracy", 0)
            
            # Get short model name - prefix AIVA models
            model_short = model.split("/")[-1] if "/" in model else model
            if model not in ["BIAS-2015", "InterVar"]:
                model_short = f"AIVA ({model_short})"
            if len(model_short) > 42:
                model_short = model_short[:42] + "..."
            
            p = m.get("pathogenic", {})
            v = m.get("vus", {})
            b = m.get("benign", {})
            
            output(f"{model_short:<45} {n:>5} {dir_acc:>7.1f}% │ "
                   f"{p.get('sensitivity', 0):>8.1f}% {p.get('specificity', 0):>7.1f}% {p.get('precision', 0):>7.1f}% {p.get('f1', 0):>7.1f}% │ "
                   f"{v.get('sensitivity', 0):>8.1f}% {v.get('specificity', 0):>7.1f}% {v.get('precision', 0):>7.1f}% {v.get('f1', 0):>7.1f}% │ "
                   f"{b.get('sensitivity', 0):>8.1f}% {b.get('specificity', 0):>7.1f}% {b.get('precision', 0):>7.1f}% {b.get('f1', 0):>7.1f}%")
    
    # Summary: Best tool per category
    output("\n" + "=" * 145)
    output("SUMMARY: BEST PERFORMING TOOL BY CATEGORY (Directional Accuracy)")
    output("=" * 145)
    output(f"\n{'Category':<45} {'Best Tool':<40} {'Dir Acc':>10} {'N':>6}")
    output("─" * 105)
    
    for cat in categories:
        best_model = None
        best_acc = 0
        best_n = 0
        
        for model in models:
            if cat in all_metrics[model]:
                acc = all_metrics[model][cat].get("directional_accuracy", 0)
                n = all_metrics[model][cat].get("n_variants", 0)
                if acc > best_acc:
                    best_acc = acc
                    best_model = model
                    best_n = n
        
        if best_model:
            # Format model name
            if best_model in ["BIAS-2015", "InterVar"]:
                display_name = best_model
            else:
                display_name = f"AIVA ({best_model.split('/')[-1]})"
            output(f"{cat:<45} {display_name:<40} {best_acc:>9.1f}% {best_n:>6}")
    
    # Comparison table: AIVA vs BIAS-2015 vs InterVar (percentage differences)
    output("\n" + "=" * 145)
    output("COMPARISON: AIVA (Best) vs BIAS-2015 vs InterVar (Directional Accuracy Difference)")
    output("=" * 145)
    output(f"\n{'Category':<35} {'AIVA Best':>12} {'BIAS-2015':>12} {'InterVar':>12} │ {'AIVA-BIAS':>12} {'AIVA-IV':>12} {'Winner':>20}")
    output("─" * 145)
    
    # Find AIVA models (exclude baselines)
    aiva_models = [m for m in models if m not in ["BIAS-2015", "InterVar"]]
    
    aiva_wins = 0
    bias_wins = 0
    intervar_wins = 0
    
    for cat in categories:
        # Get best AIVA accuracy for this category
        best_aiva_acc = 0
        best_aiva_model = None
        for model in aiva_models:
            if cat in all_metrics[model]:
                acc = all_metrics[model][cat].get("directional_accuracy", 0)
                if acc > best_aiva_acc:
                    best_aiva_acc = acc
                    best_aiva_model = model
        
        # Get BIAS-2015 accuracy
        bias_acc = all_metrics.get("BIAS-2015", {}).get(cat, {}).get("directional_accuracy", 0)
        
        # Get InterVar accuracy
        intervar_acc = all_metrics.get("InterVar", {}).get(cat, {}).get("directional_accuracy", 0)
        
        # Calculate differences
        aiva_vs_bias = best_aiva_acc - bias_acc
        aiva_vs_intervar = best_aiva_acc - intervar_acc
        
        # Determine winner
        accs = {"AIVA": best_aiva_acc, "BIAS-2015": bias_acc, "InterVar": intervar_acc}
        winner = max(accs, key=accs.get)
        if winner == "AIVA":
            aiva_wins += 1
        elif winner == "BIAS-2015":
            bias_wins += 1
        else:
            intervar_wins += 1
        
        # Format difference with +/- sign
        def fmt_diff(diff):
            if diff > 0:
                return f"+{diff:>5.1f}%"
            elif diff < 0:
                return f"{diff:>6.1f}%"
            else:
                return "  0.0%"
        
        output(f"{cat:<35} {best_aiva_acc:>11.1f}% {bias_acc:>11.1f}% {intervar_acc:>11.1f}% │ {fmt_diff(aiva_vs_bias):>12} {fmt_diff(aiva_vs_intervar):>12} {winner:>20}")
    
    output("─" * 145)
    
    # Summary statistics
    output(f"\n{'OVERALL WINS (Directional):':<35} {'AIVA':>12} {'BIAS-2015':>12} {'InterVar':>12}")
    output(f"{'':35} {aiva_wins:>12} {bias_wins:>12} {intervar_wins:>12}")
    
    # Calculate average differences across all categories
    total_aiva_vs_bias = 0
    total_aiva_vs_intervar = 0
    n_cats = 0
    
    for cat in categories:
        best_aiva_acc = 0
        for model in aiva_models:
            if cat in all_metrics[model]:
                acc = all_metrics[model][cat].get("directional_accuracy", 0)
                if acc > best_aiva_acc:
                    best_aiva_acc = acc
        
        bias_acc = all_metrics.get("BIAS-2015", {}).get(cat, {}).get("directional_accuracy", 0)
        intervar_acc = all_metrics.get("InterVar", {}).get(cat, {}).get("directional_accuracy", 0)
        
        if best_aiva_acc > 0:
            total_aiva_vs_bias += (best_aiva_acc - bias_acc)
            total_aiva_vs_intervar += (best_aiva_acc - intervar_acc)
            n_cats += 1
    
    if n_cats > 0:
        avg_vs_bias = total_aiva_vs_bias / n_cats
        avg_vs_intervar = total_aiva_vs_intervar / n_cats
        
        output(f"\n{'AVERAGE DIFFERENCE (Directional):':<35}")
        output(f"  AIVA vs BIAS-2015:  {avg_vs_bias:>+6.1f}% {'(AIVA better)' if avg_vs_bias > 0 else '(BIAS-2015 better)'}")
        output(f"  AIVA vs InterVar:   {avg_vs_intervar:>+6.1f}% {'(AIVA better)' if avg_vs_intervar > 0 else '(InterVar better)'}")
    
    # ==========================================================================
    # EXACT ACCURACY (5-class) COMPARISON
    # ==========================================================================
    output("\n" + "=" * 145)
    output("COMPARISON: AIVA (Best) vs BIAS-2015 vs InterVar (EXACT 5-CLASS Accuracy Difference)")
    output("=" * 145)
    output(f"\n{'Category':<35} {'AIVA Best':>12} {'BIAS-2015':>12} {'InterVar':>12} │ {'AIVA-BIAS':>12} {'AIVA-IV':>12} {'Winner':>20}")
    output("─" * 145)
    
    aiva_wins_exact = 0
    bias_wins_exact = 0
    intervar_wins_exact = 0
    total_aiva_vs_bias_exact = 0
    total_aiva_vs_intervar_exact = 0
    n_cats_exact = 0
    
    for cat in categories:
        # Get best AIVA exact accuracy for this category
        best_aiva_acc = 0
        best_aiva_model = None
        for model in aiva_models:
            if cat in all_metrics[model]:
                acc = all_metrics[model][cat].get("exact_accuracy", 0)
                if acc > best_aiva_acc:
                    best_aiva_acc = acc
                    best_aiva_model = model
        
        # Get BIAS-2015 exact accuracy
        bias_acc = all_metrics.get("BIAS-2015", {}).get(cat, {}).get("exact_accuracy", 0)
        
        # Get InterVar exact accuracy
        intervar_acc = all_metrics.get("InterVar", {}).get(cat, {}).get("exact_accuracy", 0)
        
        # Calculate differences
        aiva_vs_bias = best_aiva_acc - bias_acc
        aiva_vs_intervar = best_aiva_acc - intervar_acc
        
        # Determine winner
        accs = {"AIVA": best_aiva_acc, "BIAS-2015": bias_acc, "InterVar": intervar_acc}
        winner = max(accs, key=accs.get)
        if winner == "AIVA":
            aiva_wins_exact += 1
        elif winner == "BIAS-2015":
            bias_wins_exact += 1
        else:
            intervar_wins_exact += 1
        
        if best_aiva_acc > 0:
            total_aiva_vs_bias_exact += aiva_vs_bias
            total_aiva_vs_intervar_exact += aiva_vs_intervar
            n_cats_exact += 1
        
        output(f"{cat:<35} {best_aiva_acc:>11.1f}% {bias_acc:>11.1f}% {intervar_acc:>11.1f}% │ {fmt_diff(aiva_vs_bias):>12} {fmt_diff(aiva_vs_intervar):>12} {winner:>20}")
    
    output("─" * 145)
    
    # Summary statistics for exact accuracy
    output(f"\n{'OVERALL WINS (Exact 5-class):':<35} {'AIVA':>12} {'BIAS-2015':>12} {'InterVar':>12}")
    output(f"{'':35} {aiva_wins_exact:>12} {bias_wins_exact:>12} {intervar_wins_exact:>12}")
    
    if n_cats_exact > 0:
        avg_vs_bias_exact = total_aiva_vs_bias_exact / n_cats_exact
        avg_vs_intervar_exact = total_aiva_vs_intervar_exact / n_cats_exact
        
        output(f"\n{'AVERAGE DIFFERENCE (Exact):':<35}")
        output(f"  AIVA vs BIAS-2015:  {avg_vs_bias_exact:>+6.1f}% {'(AIVA better)' if avg_vs_bias_exact > 0 else '(BIAS-2015 better)'}")
        output(f"  AIVA vs InterVar:   {avg_vs_intervar_exact:>+6.1f}% {'(AIVA better)' if avg_vs_intervar_exact > 0 else '(InterVar better)'}")
    
    # ==========================================================================
    # DETAILED 5-CLASS METRICS BY CATEGORY
    # ==========================================================================
    output("\n" + "=" * 180)
    output("DETAILED 5-CLASS METRICS BY DISEASE CATEGORY (Pathogenic, Likely Pathogenic, VUS, Likely Benign, Benign)")
    output("=" * 180)
    
    exact_classes = ["Pathogenic", "Likely Pathogenic", "Uncertain Significance", "Likely Benign", "Benign"]
    class_abbrev = {"Pathogenic": "P", "Likely Pathogenic": "LP", "Uncertain Significance": "VUS", "Likely Benign": "LB", "Benign": "B"}
    
    for cat in categories:
        output(f"\n{'─' * 180}")
        output(f"CATEGORY: {cat}")
        output(f"{'─' * 180}")
        
        # Header for 5-class metrics
        output(f"\n{'Tool/Model':<45} {'N':>5} {'ExactAcc':>9} │ "
               f"{'P Sens':>7} {'Spec':>6} {'Prec':>6} {'F1':>6} │ "
               f"{'LP Sens':>7} {'Spec':>6} {'Prec':>6} {'F1':>6} │ "
               f"{'VUS Sens':>8} {'Spec':>6} {'Prec':>6} {'F1':>6} │ "
               f"{'LB Sens':>7} {'Spec':>6} {'Prec':>6} {'F1':>6} │ "
               f"{'B Sens':>6} {'Spec':>6} {'Prec':>6} {'F1':>6}")
        output("─" * 180)
        
        for model in models:
            if cat not in all_metrics[model]:
                continue
            
            m = all_metrics[model][cat]
            n = m.get("n_variants", 0)
            exact_acc = m.get("exact_accuracy", 0)
            
            # Get short model name
            model_short = model.split("/")[-1] if "/" in model else model
            if model not in ["BIAS-2015", "InterVar"]:
                model_short = f"AIVA ({model_short})"
            if len(model_short) > 42:
                model_short = model_short[:42] + "..."
            
            # Get metrics for each exact class
            p = m.get("exact_Pathogenic", {})
            lp = m.get("exact_Likely Pathogenic", {})
            vus = m.get("exact_Uncertain Significance", {})
            lb = m.get("exact_Likely Benign", {})
            b = m.get("exact_Benign", {})
            
            output(f"{model_short:<45} {n:>5} {exact_acc:>8.1f}% │ "
                   f"{p.get('sensitivity', 0):>6.1f}% {p.get('specificity', 0):>5.1f}% {p.get('precision', 0):>5.1f}% {p.get('f1', 0):>5.1f}% │ "
                   f"{lp.get('sensitivity', 0):>6.1f}% {lp.get('specificity', 0):>5.1f}% {lp.get('precision', 0):>5.1f}% {lp.get('f1', 0):>5.1f}% │ "
                   f"{vus.get('sensitivity', 0):>7.1f}% {vus.get('specificity', 0):>5.1f}% {vus.get('precision', 0):>5.1f}% {vus.get('f1', 0):>5.1f}% │ "
                   f"{lb.get('sensitivity', 0):>6.1f}% {lb.get('specificity', 0):>5.1f}% {lb.get('precision', 0):>5.1f}% {lb.get('f1', 0):>5.1f}% │ "
                   f"{b.get('sensitivity', 0):>5.1f}% {b.get('specificity', 0):>5.1f}% {b.get('precision', 0):>5.1f}% {b.get('f1', 0):>5.1f}%")
    
    # Save to file if requested
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\nSaved report to {output_file}")


def save_metrics_tsv(all_metrics: Dict, output_path: Path):
    """Save metrics to TSV file with both directional and exact metrics."""
    with open(output_path, "w", encoding="utf-8") as f:
        # Header - include both directional and exact metrics
        f.write("category\tmodel\tn_variants\t")
        # Directional (3-class) metrics
        f.write("directional_accuracy\t")
        f.write("plp_sensitivity\tplp_specificity\tplp_precision\tplp_f1\t")
        f.write("vus_sensitivity\tvus_specificity\tvus_precision\tvus_f1\t")
        f.write("blb_sensitivity\tblb_specificity\tblb_precision\tblb_f1\t")
        # Exact (5-class) metrics
        f.write("exact_accuracy\t")
        f.write("exact_p_f1\texact_lp_f1\texact_vus_f1\texact_lb_f1\texact_b_f1\texact_macro_f1\n")
        
        for model, model_metrics in sorted(all_metrics.items()):
            model_short = model.split("/")[-1] if "/" in model else model
            
            for cat in sorted(model_metrics.keys(), key=lambda x: CATEGORY_ORDER.index(x) if x in CATEGORY_ORDER else 999):
                m = model_metrics[cat]
                p = m.get("pathogenic", {})
                v = m.get("vus", {})
                b = m.get("benign", {})
                
                # Exact 5-class metrics
                exact_p = m.get("exact_Pathogenic", {})
                exact_lp = m.get("exact_Likely Pathogenic", {})
                exact_vus = m.get("exact_Uncertain Significance", {})
                exact_lb = m.get("exact_Likely Benign", {})
                exact_b = m.get("exact_Benign", {})
                
                # Calculate macro F1 for exact classes
                exact_f1s = [
                    exact_p.get('f1', 0),
                    exact_lp.get('f1', 0),
                    exact_vus.get('f1', 0),
                    exact_lb.get('f1', 0),
                    exact_b.get('f1', 0)
                ]
                macro_f1 = sum(exact_f1s) / 5 if exact_f1s else 0
                
                # Directional metrics
                f.write(f"{cat}\t{model_short}\t{m.get('n_variants', 0)}\t{m.get('directional_accuracy', 0)}\t")
                f.write(f"{p.get('sensitivity', 0)}\t{p.get('specificity', 0)}\t{p.get('precision', 0)}\t{p.get('f1', 0)}\t")
                f.write(f"{v.get('sensitivity', 0)}\t{v.get('specificity', 0)}\t{v.get('precision', 0)}\t{v.get('f1', 0)}\t")
                f.write(f"{b.get('sensitivity', 0)}\t{b.get('specificity', 0)}\t{b.get('precision', 0)}\t{b.get('f1', 0)}\t")
                # Exact metrics
                f.write(f"{m.get('exact_accuracy', 0)}\t")
                f.write(f"{exact_p.get('f1', 0)}\t{exact_lp.get('f1', 0)}\t{exact_vus.get('f1', 0)}\t{exact_lb.get('f1', 0)}\t{exact_b.get('f1', 0)}\t{macro_f1:.2f}\n")
    
    print(f"Saved metrics TSV to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Calculate BIAS-style metrics by disease category")
    parser.add_argument("input_files", nargs="+", type=Path, help="JSONL classification result files")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory")
    parser.add_argument("--unified", type=Path, default=None, help="Path to unified BIAS data (for BIAS-2015 and InterVar baselines)")
    args = parser.parse_args()
    
    # Load all AIVA variants from classification files
    all_variants = []
    models = set()
    variant_ids = set()
    
    for fp in args.input_files:
        if not fp.exists():
            print(f"Warning: File not found: {fp}")
            continue
        
        variants = load_jsonl(fp)
        all_variants.extend(variants)
        
        for v in variants:
            if v.get("model_used"):
                models.add(v["model_used"])
            if v.get("variant_id"):
                variant_ids.add(v["variant_id"])
    
    print(f"Loaded {len(all_variants)} AIVA predictions from {len(args.input_files)} file(s)")
    print(f"AIVA Models: {', '.join(sorted(models))}")
    print(f"Unique variants: {len(variant_ids)}")
    
    # Load unified data for BIAS-2015 and InterVar baselines
    unified_path = args.unified or DATA_DIR / "bias_unified.jsonl"
    unified_data = []
    unified_by_id = {}
    
    if unified_path.exists():
        unified_data = load_jsonl(unified_path)
        unified_by_id = {v.get("id"): v for v in unified_data}
        print(f"Loaded {len(unified_data)} variants from unified dataset")
    else:
        print(f"Warning: Unified data not found at {unified_path}")
    
    # Filter unified data to only variants in our AIVA benchmark
    unified_filtered = [unified_by_id[vid] for vid in variant_ids if vid in unified_by_id]
    print(f"Matched {len(unified_filtered)} variants for BIAS/InterVar comparison")
    
    # Calculate metrics for each AIVA model
    all_metrics = {}
    for model in sorted(models):
        all_metrics[model] = calculate_category_metrics(all_variants, model, "aiva_classification")
    
    # Calculate metrics for BIAS-2015 and InterVar baselines (on the same variant set)
    if unified_filtered:
        all_metrics["BIAS-2015"] = calculate_category_metrics(unified_filtered, None, "bias_classification")
        all_metrics["InterVar"] = calculate_category_metrics(unified_filtered, None, "intervar_classification")
        print("Added BIAS-2015 and InterVar baseline metrics")
    
    # Determine output directory
    output_dir = args.output_dir or args.input_files[0].parent
    
    # Print and save report
    report_path = output_dir / "metrics_by_category.txt"
    print_category_metrics(all_metrics, report_path)
    
    # Save TSV
    tsv_path = output_dir / "metrics_by_category.tsv"
    save_metrics_tsv(all_metrics, tsv_path)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
