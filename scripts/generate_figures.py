#!/usr/bin/env python3
"""
Generate publication-quality figures for AIVA benchmarking results.

Creates:
1. ROC curves (per-class and micro/macro averaged)
2. Precision-Recall curves
3. Confusion matrices (heatmaps)
4. Bar charts comparing tools by category
5. Radar/Spider plots for multi-metric comparison
6. Performance summary tables

Usage:
    python scripts/generate_figures.py Results_500_benchmarked/classifications_*.jsonl
    python scripts/generate_figures.py Results_500_benchmarked/classifications_*.jsonl --output-dir figures
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns

# Try to import sklearn for ROC curves
try:
    from sklearn.metrics import (
        roc_curve, auc, precision_recall_curve, average_precision_score,
        confusion_matrix, classification_report
    )
    from sklearn.preprocessing import label_binarize
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Some plots will be skipped.")

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR

# =============================================================================
# Configuration
# =============================================================================

# Publication-quality settings
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,
})

# Color palette for tools (colorblind-friendly)
TOOL_COLORS = {
    'AIVA (claude-opus-4-5-20251101)': '#0072B2',  # Blue
    'AIVA (gemini-3-pro-preview)': '#009E73',      # Green
    'AIVA (gpt-5.2)': '#D55E00',                   # Orange
    'BIAS-2015': '#CC79A7',                        # Pink
    'InterVar': '#F0E442',                         # Yellow
}

# Short names for display
TOOL_SHORT_NAMES = {
    'anthropic/claude-opus-4-5-20251101': 'AIVA-Claude',
    'google/gemini-3-pro-preview': 'AIVA-Gemini',
    'openai/gpt-5.2': 'AIVA-GPT',
    'BIAS-2015': 'BIAS-2015',
    'InterVar': 'InterVar',
}

# Classification labels
CLASS_LABELS_5 = ['Pathogenic', 'Likely Pathogenic', 'VUS', 'Likely Benign', 'Benign']
CLASS_LABELS_3 = ['Pathogenic/Likely Pathogenic', 'VUS', 'Benign/Likely Benign']

# Disease categories
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
]

CATEGORY_SHORT = {
    "Cancer Predisposition": "Cancer",
    "Metabolic Disorders": "Metabolic",
    "Cardiovascular Disorders": "Cardio",
    "Hematologic Disorders": "Hemato",
    "Immunodeficiency Disorders": "Immuno",
    "Neurodevelopmental Disorders": "Neurodev",
    "Neuromuscular Disorders": "Neuromusc",
    "Ophthalmologic Disorders": "Ophthalm",
    "Hearing Disorders": "Hearing",
    "RASopathies": "RASopathy",
}

# =============================================================================
# Helper Functions
# =============================================================================

def normalize_classification(cls: str) -> str:
    """Normalize classification string to 5-class."""
    if not cls:
        return ""
    cls_lower = cls.lower().strip()
    
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
        return "P/LP"
    elif cls_norm in ["Benign", "Likely Benign"]:
        return "B/LB"
    elif cls_norm == "Uncertain Significance":
        return "VUS"
    return "unknown"


def load_jsonl(filepath: Path) -> List[Dict]:
    """Load JSONL file."""
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def get_tool_color(tool_name: str) -> str:
    """Get color for a tool."""
    for key, color in TOOL_COLORS.items():
        if key in tool_name or tool_name in key:
            return color
    return '#999999'


def get_short_name(tool_name: str) -> str:
    """Get short display name for a tool."""
    for key, short in TOOL_SHORT_NAMES.items():
        if key in tool_name or tool_name in key:
            return short
    return tool_name.split('/')[-1][:15]


# =============================================================================
# Data Loading
# =============================================================================

def load_all_data(input_files: List[Path], unified_path: Path) -> Tuple[Dict, Dict]:
    """Load AIVA results and unified baseline data."""
    
    # Load AIVA results
    aiva_data = defaultdict(list)
    variant_ids = set()
    
    for fp in input_files:
        if not fp.exists():
            continue
        variants = load_jsonl(fp)
        for v in variants:
            model = v.get("model_used", "unknown")
            aiva_data[model].append(v)
            if v.get("variant_id"):
                variant_ids.add(v["variant_id"])
    
    # Load unified data for baselines
    unified_by_id = {}
    if unified_path.exists():
        unified_data = load_jsonl(unified_path)
        unified_by_id = {v.get("id"): v for v in unified_data}
    
    # Filter to matching variants
    unified_filtered = {vid: unified_by_id[vid] for vid in variant_ids if vid in unified_by_id}
    
    return aiva_data, unified_filtered


# =============================================================================
# Figure 1: Confusion Matrices
# =============================================================================

def plot_confusion_matrices(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Generate confusion matrix heatmaps for each tool."""
    
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    axes = axes.flatten()
    
    tools_data = []
    
    # Prepare AIVA model data
    for model, variants in aiva_data.items():
        y_true = []
        y_pred = []
        for v in variants:
            gt = get_direction(v.get("ground_truth", ""))
            pred = get_direction(v.get("aiva_classification", ""))
            if gt != "unknown" and pred != "unknown" and not v.get("error"):
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_data.append((get_short_name(model), y_true, y_pred))
    
    # Prepare baseline data
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true = []
        y_pred = []
        for vid, v in unified_data.items():
            gt = get_direction(v.get("classification", ""))
            pred = get_direction(v.get(pred_field, ""))
            if gt != "unknown" and pred != "unknown":
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_data.append((tool, y_true, y_pred))
    
    labels = ['P/LP', 'VUS', 'B/LB']
    
    for idx, (tool_name, y_true, y_pred) in enumerate(tools_data[:6]):
        ax = axes[idx]
        
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        cm_normalized = np.nan_to_num(cm_normalized)
        
        sns.heatmap(cm_normalized, annot=True, fmt='.2f', cmap='Blues',
                    xticklabels=labels, yticklabels=labels, ax=ax,
                    vmin=0, vmax=1, cbar_kws={'label': 'Proportion'})
        
        # Add raw counts as secondary annotation
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j + 0.5, i + 0.75, f'(n={cm[i, j]})',
                       ha='center', va='center', fontsize=7, color='gray')
        
        ax.set_title(f'{tool_name}', fontweight='bold')
        ax.set_xlabel('Predicted')
        ax.set_ylabel('True')
    
    # Hide unused axes
    for idx in range(len(tools_data), 6):
        axes[idx].axis('off')
    
    plt.suptitle('Confusion Matrices (3-Class Directional)', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    output_path = output_dir / 'figure1_confusion_matrices.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure1_confusion_matrices.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 2: Performance Bar Charts by Category
# =============================================================================

def plot_performance_by_category(metrics_tsv: Path, output_dir: Path):
    """Generate grouped bar charts showing performance by disease category."""
    
    import csv
    
    # Load metrics from TSV
    metrics = defaultdict(lambda: defaultdict(dict))
    
    with open(metrics_tsv, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            cat = row['category']
            model = row['model']
            metrics[cat][model] = {
                'accuracy': float(row['directional_accuracy']),
                'plp_sens': float(row['plp_sensitivity']),
                'plp_f1': float(row['plp_f1']),
                'vus_sens': float(row['vus_sensitivity']),
                'vus_f1': float(row['vus_f1']),
                'blb_sens': float(row['blb_sensitivity']),
                'blb_f1': float(row['blb_f1']),
            }
    
    # Filter to categories in our order
    categories = [c for c in CATEGORY_ORDER if c in metrics]
    
    # Get all tools
    all_tools = set()
    for cat_metrics in metrics.values():
        all_tools.update(cat_metrics.keys())
    
    # Sort tools: AIVA first, then baselines
    tools = sorted([t for t in all_tools if 'claude' in t.lower() or 'gemini' in t.lower() or 'gpt' in t.lower()])
    tools += sorted([t for t in all_tools if t in ['BIAS-2015', 'InterVar']])
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    x = np.arange(len(categories))
    width = 0.15
    
    # Plot 1: Overall Directional Accuracy
    ax = axes[0, 0]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('accuracy', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=get_short_name(tool),
                     color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('A. Directional Accuracy by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.legend(loc='upper right', fontsize=8)
    ax.set_ylim(0, 105)
    ax.axhline(y=80, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
    
    # Plot 2: P/LP Sensitivity
    ax = axes[0, 1]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('plp_sens', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=get_short_name(tool),
               color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Sensitivity (%)')
    ax.set_title('B. P/LP Sensitivity by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    ax.axhline(y=80, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
    
    # Plot 3: VUS Sensitivity
    ax = axes[1, 0]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('vus_sens', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=get_short_name(tool),
               color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Sensitivity (%)')
    ax.set_title('C. VUS Sensitivity by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    
    # Plot 4: B/LB Sensitivity
    ax = axes[1, 1]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('blb_sens', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=get_short_name(tool),
               color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Sensitivity (%)')
    ax.set_title('D. B/LB Sensitivity by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure2_performance_by_category.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure2_performance_by_category.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 3: Radar/Spider Plot for Multi-Metric Comparison
# =============================================================================

def plot_radar_comparison(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Generate radar plot comparing tools across multiple metrics."""
    
    # Calculate overall metrics for each tool
    def calc_metrics(y_true, y_pred, labels=['P/LP', 'VUS', 'B/LB']):
        from collections import Counter
        
        total = len(y_true)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / total * 100 if total > 0 else 0
        
        metrics_dict = {'accuracy': accuracy}
        
        for label in labels:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
            
            sens = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
            prec = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
            f1 = 2 * sens * prec / (sens + prec) if (sens + prec) > 0 else 0
            
            metrics_dict[f'{label}_sens'] = sens
            metrics_dict[f'{label}_prec'] = prec
            metrics_dict[f'{label}_f1'] = f1
        
        return metrics_dict
    
    tools_metrics = {}
    
    # AIVA models
    for model, variants in aiva_data.items():
        y_true = []
        y_pred = []
        for v in variants:
            gt = get_direction(v.get("ground_truth", ""))
            pred = get_direction(v.get("aiva_classification", ""))
            if gt != "unknown" and pred != "unknown" and not v.get("error"):
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_metrics[get_short_name(model)] = calc_metrics(y_true, y_pred)
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true = []
        y_pred = []
        for vid, v in unified_data.items():
            gt = get_direction(v.get("classification", ""))
            pred = get_direction(v.get(pred_field, ""))
            if gt != "unknown" and pred != "unknown":
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_metrics[tool] = calc_metrics(y_true, y_pred)
    
    # Metrics to plot
    metric_labels = ['Accuracy', 'P/LP Sens', 'P/LP Prec', 'VUS Sens', 'VUS Prec', 'B/LB Sens', 'B/LB Prec']
    metric_keys = ['accuracy', 'P/LP_sens', 'P/LP_prec', 'VUS_sens', 'VUS_prec', 'B/LB_sens', 'B/LB_prec']
    
    # Create radar chart
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    angles = np.linspace(0, 2 * np.pi, len(metric_labels), endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle
    
    for tool, metrics in tools_metrics.items():
        values = [metrics.get(k, 0) for k in metric_keys]
        values += values[:1]  # Complete the circle
        
        color = get_tool_color(tool)
        ax.plot(angles, values, 'o-', linewidth=2, label=tool, color=color)
        ax.fill(angles, values, alpha=0.15, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metric_labels, size=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], size=8)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    plt.title('Multi-Metric Performance Comparison', fontsize=14, fontweight='bold', y=1.08)
    
    output_path = output_dir / 'figure3_radar_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure3_radar_comparison.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 4: ROC Curves (if sklearn available)
# =============================================================================

def plot_roc_curves(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Generate ROC curves for each tool (one-vs-rest for each class)."""
    
    if not SKLEARN_AVAILABLE:
        print("Skipping ROC curves (scikit-learn not available)")
        return
    
    classes = ['P/LP', 'VUS', 'B/LB']
    
    # Collect predictions for each tool
    tools_data = {}
    
    # AIVA models
    for model, variants in aiva_data.items():
        y_true = []
        y_pred = []
        for v in variants:
            gt = get_direction(v.get("ground_truth", ""))
            pred = get_direction(v.get("aiva_classification", ""))
            if gt != "unknown" and pred != "unknown" and not v.get("error"):
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_data[get_short_name(model)] = (y_true, y_pred)
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true = []
        y_pred = []
        for vid, v in unified_data.items():
            gt = get_direction(v.get("classification", ""))
            pred = get_direction(v.get(pred_field, ""))
            if gt != "unknown" and pred != "unknown":
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_data[tool] = (y_true, y_pred)
    
    # Create figure with 3 subplots (one per class)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    for idx, target_class in enumerate(classes):
        ax = axes[idx]
        
        for tool, (y_true, y_pred) in tools_data.items():
            # Binary: is this class or not
            y_true_bin = [1 if y == target_class else 0 for y in y_true]
            y_pred_bin = [1 if y == target_class else 0 for y in y_pred]
            
            # For ROC, we need probability scores. Since we have hard predictions,
            # we'll create a pseudo-ROC by calculating TPR/FPR at the single threshold
            tp = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 1 and p == 1)
            fp = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 0 and p == 1)
            fn = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 1 and p == 0)
            tn = sum(1 for t, p in zip(y_true_bin, y_pred_bin) if t == 0 and p == 0)
            
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            # Plot point and line to it
            color = get_tool_color(tool)
            ax.plot([0, fpr, 1], [0, tpr, 1], 'o-', color=color, label=f'{tool}', 
                   markersize=8, linewidth=2)
            ax.scatter([fpr], [tpr], s=100, color=color, zorder=5, edgecolors='black')
        
        # Diagonal line (random classifier)
        ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, linewidth=1)
        
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title(f'{target_class} (One-vs-Rest)', fontweight='bold')
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
        ax.legend(loc='lower right', fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('ROC Analysis (Operating Points)', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    output_path = output_dir / 'figure4_roc_curves.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure4_roc_curves.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 5: Summary Comparison (AIVA vs Baselines)
# =============================================================================

def plot_summary_comparison(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Generate summary bar chart comparing AIVA best vs baselines."""
    
    def calc_overall_metrics(y_true, y_pred):
        total = len(y_true)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        return correct / total * 100 if total > 0 else 0
    
    tools_accuracy = {}
    
    # AIVA models
    for model, variants in aiva_data.items():
        y_true = []
        y_pred = []
        for v in variants:
            gt = get_direction(v.get("ground_truth", ""))
            pred = get_direction(v.get("aiva_classification", ""))
            if gt != "unknown" and pred != "unknown" and not v.get("error"):
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_accuracy[get_short_name(model)] = calc_overall_metrics(y_true, y_pred)
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true = []
        y_pred = []
        for vid, v in unified_data.items():
            gt = get_direction(v.get("classification", ""))
            pred = get_direction(v.get(pred_field, ""))
            if gt != "unknown" and pred != "unknown":
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_accuracy[tool] = calc_overall_metrics(y_true, y_pred)
    
    # Sort by accuracy
    sorted_tools = sorted(tools_accuracy.items(), key=lambda x: x[1], reverse=True)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    tools = [t[0] for t in sorted_tools]
    accuracies = [t[1] for t in sorted_tools]
    colors = [get_tool_color(t) for t in tools]
    
    bars = ax.barh(tools, accuracies, color=colors, edgecolor='black', linewidth=1)
    
    # Add value labels
    for bar, acc in zip(bars, accuracies):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
               f'{acc:.1f}%', va='center', fontsize=10, fontweight='bold')
    
    # Highlight best AIVA
    best_aiva = max([t for t in tools_accuracy.items() if 'AIVA' in t[0]], key=lambda x: x[1])
    ax.axvline(x=best_aiva[1], color='green', linestyle='--', alpha=0.7, linewidth=2)
    
    ax.set_xlabel('Directional Accuracy (%)', fontsize=12)
    ax.set_title('Overall Performance Comparison\n(500-Variant ClinGen Benchmark)', 
                fontsize=14, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure5_summary_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure5_summary_comparison.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 6: Heatmap of Performance Differences
# =============================================================================

def plot_performance_heatmap(metrics_tsv: Path, output_dir: Path):
    """Generate heatmap showing AIVA advantage over baselines by category."""
    
    import csv
    
    # Load metrics
    metrics = defaultdict(lambda: defaultdict(dict))
    
    with open(metrics_tsv, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            cat = row['category']
            model = row['model']
            metrics[cat][model] = float(row['directional_accuracy'])
    
    categories = [c for c in CATEGORY_ORDER if c in metrics]
    
    # Find best AIVA model per category
    aiva_models = [m for m in list(metrics.values())[0].keys() 
                   if 'claude' in m.lower() or 'gemini' in m.lower() or 'gpt' in m.lower()]
    
    # Calculate differences
    diff_data = []
    for cat in categories:
        best_aiva = max([metrics[cat].get(m, 0) for m in aiva_models])
        bias_acc = metrics[cat].get('BIAS-2015', 0)
        intervar_acc = metrics[cat].get('InterVar', 0)
        
        diff_data.append({
            'category': CATEGORY_SHORT.get(cat, cat),
            'AIVA vs BIAS-2015': best_aiva - bias_acc,
            'AIVA vs InterVar': best_aiva - intervar_acc,
        })
    
    # Create heatmap data
    cat_labels = [d['category'] for d in diff_data]
    comparison_labels = ['AIVA vs BIAS-2015', 'AIVA vs InterVar']
    
    heatmap_data = np.array([[d['AIVA vs BIAS-2015'], d['AIVA vs InterVar']] for d in diff_data])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 10))
    
    # Custom colormap: red for negative (AIVA worse), green for positive (AIVA better)
    cmap = sns.diverging_palette(10, 130, as_cmap=True)
    
    sns.heatmap(heatmap_data, annot=True, fmt='+.1f', cmap=cmap, center=0,
                xticklabels=comparison_labels, yticklabels=cat_labels,
                ax=ax, cbar_kws={'label': 'Accuracy Difference (%)'})
    
    # Add annotations for winners
    for i, row in enumerate(heatmap_data):
        for j, val in enumerate(row):
            symbol = '▲' if val > 0 else '▼' if val < 0 else '='
            ax.text(j + 0.5, i + 0.75, symbol, ha='center', va='center', 
                   fontsize=10, color='white' if abs(val) > 15 else 'black')
    
    ax.set_title('AIVA Performance Advantage by Disease Category\n(Positive = AIVA Better)', 
                fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure6_performance_heatmap.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure6_performance_heatmap.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 7: Exact vs Directional Accuracy Scatter
# =============================================================================

def plot_exact_vs_directional(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Scatter plot comparing exact (5-class) vs directional (3-class) accuracy."""
    
    def calc_accuracies(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact):
        dir_correct = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t == p)
        exact_correct = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t == p)
        n = len(y_true_dir)
        return (dir_correct / n * 100 if n > 0 else 0, 
                exact_correct / n * 100 if n > 0 else 0)
    
    tools_data = []
    
    # AIVA models
    for model, variants in aiva_data.items():
        y_true_dir, y_pred_dir = [], []
        y_true_exact, y_pred_exact = [], []
        
        for v in variants:
            gt = v.get("ground_truth", "")
            pred = v.get("aiva_classification", "")
            gt_dir = get_direction(gt)
            pred_dir = get_direction(pred)
            
            if gt_dir != "unknown" and pred_dir != "unknown" and not v.get("error"):
                y_true_dir.append(gt_dir)
                y_pred_dir.append(pred_dir)
                y_true_exact.append(normalize_classification(gt))
                y_pred_exact.append(normalize_classification(pred))
        
        if y_true_dir:
            dir_acc, exact_acc = calc_accuracies(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact)
            tools_data.append((get_short_name(model), dir_acc, exact_acc, get_tool_color(model)))
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true_dir, y_pred_dir = [], []
        y_true_exact, y_pred_exact = [], []
        
        for vid, v in unified_data.items():
            gt = v.get("classification", "")
            pred = v.get(pred_field, "")
            gt_dir = get_direction(gt)
            pred_dir = get_direction(pred)
            
            if gt_dir != "unknown" and pred_dir != "unknown":
                y_true_dir.append(gt_dir)
                y_pred_dir.append(pred_dir)
                y_true_exact.append(normalize_classification(gt))
                y_pred_exact.append(normalize_classification(pred))
        
        if y_true_dir:
            dir_acc, exact_acc = calc_accuracies(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact)
            tools_data.append((tool, dir_acc, exact_acc, get_tool_color(tool)))
    
    # Create scatter plot
    fig, ax = plt.subplots(figsize=(8, 8))
    
    for name, dir_acc, exact_acc, color in tools_data:
        ax.scatter(dir_acc, exact_acc, s=200, c=color, label=name, 
                  edgecolors='black', linewidth=1.5, zorder=5)
        ax.annotate(name, (dir_acc, exact_acc), xytext=(5, 5), 
                   textcoords='offset points', fontsize=9)
    
    # Add diagonal line (exact = directional)
    ax.plot([0, 100], [0, 100], 'k--', alpha=0.3, linewidth=1)
    
    # Add reference lines
    ax.axhline(y=70, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=80, color='gray', linestyle=':', alpha=0.5)
    
    ax.set_xlabel('Directional (3-class) Accuracy (%)', fontsize=12)
    ax.set_ylabel('Exact (5-class) Accuracy (%)', fontsize=12)
    ax.set_title('Exact vs Directional Classification Accuracy', fontsize=14, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right')
    
    # Add text annotation
    ax.text(95, 5, 'Points below diagonal:\nExact < Directional\n(as expected)', 
           fontsize=8, ha='right', va='bottom', style='italic', alpha=0.7)
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure7_exact_vs_directional.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure7_exact_vs_directional.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate publication-quality figures")
    parser.add_argument("input_files", nargs="+", type=Path, help="JSONL classification files")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for figures")
    parser.add_argument("--unified", type=Path, default=None, help="Path to unified BIAS data")
    parser.add_argument("--metrics-tsv", type=Path, default=None, help="Path to metrics_by_category.tsv")
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = args.output_dir or Path("figures")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Output directory: {output_dir}")
    print(f"Loading data from {len(args.input_files)} files...")
    
    # Load data
    unified_path = args.unified or DATA_DIR / "bias_unified.jsonl"
    aiva_data, unified_data = load_all_data(args.input_files, unified_path)
    
    print(f"Loaded {sum(len(v) for v in aiva_data.values())} AIVA predictions")
    print(f"Loaded {len(unified_data)} matched baseline variants")
    print(f"AIVA Models: {list(aiva_data.keys())}")
    
    # Generate figures
    print("\nGenerating figures...")
    
    # Figure 1: Confusion matrices
    print("  [1/7] Confusion matrices...")
    plot_confusion_matrices(aiva_data, unified_data, output_dir)
    
    # Figure 2: Performance by category (requires TSV)
    metrics_tsv = args.metrics_tsv
    if not metrics_tsv:
        # Try to find it
        for parent in [args.input_files[0].parent, Path("Results_500_benchmarked")]:
            candidate = parent / "metrics_by_category.tsv"
            if candidate.exists():
                metrics_tsv = candidate
                break
    
    if metrics_tsv and metrics_tsv.exists():
        print("  [2/7] Performance by category...")
        plot_performance_by_category(metrics_tsv, output_dir)
        
        print("  [6/7] Performance heatmap...")
        plot_performance_heatmap(metrics_tsv, output_dir)
    else:
        print("  [2/7] Skipping (metrics_by_category.tsv not found)")
        print("  [6/7] Skipping (metrics_by_category.tsv not found)")
    
    # Figure 3: Radar plot
    print("  [3/7] Radar comparison...")
    plot_radar_comparison(aiva_data, unified_data, output_dir)
    
    # Figure 4: ROC curves
    print("  [4/7] ROC curves...")
    plot_roc_curves(aiva_data, unified_data, output_dir)
    
    # Figure 5: Summary comparison
    print("  [5/7] Summary comparison...")
    plot_summary_comparison(aiva_data, unified_data, output_dir)
    
    # Figure 7: Exact vs Directional
    print("  [7/7] Exact vs Directional scatter...")
    plot_exact_vs_directional(aiva_data, unified_data, output_dir)
    
    print(f"\n✅ All figures saved to {output_dir}/")
    print("\nGenerated files:")
    for f in sorted(output_dir.glob("figure*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
