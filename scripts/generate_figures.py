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

# Color palette for tools (colorblind-friendly, AIVA prominent)
# AIVA models get vibrant, distinct colors; baselines get muted colors
TOOL_COLORS = {
    # AIVA models - vibrant, primary colors
    'AIVA-Claude': '#2E86AB',        # Strong Blue
    'AIVA-Gemini': '#28A745',        # Vibrant Green  
    'AIVA-GPT': '#E85D04',           # Vibrant Orange
    'claude-opus-4-5-20251101': '#2E86AB',
    'gemini-3-pro-preview': '#28A745',
    'gpt-5.2': '#E85D04',
    # Baselines - muted/secondary colors
    'BIAS-2015': '#6C757D',          # Muted Gray
    'InterVar': '#ADB5BD',           # Light Gray
}

# Short names for display
TOOL_SHORT_NAMES = {
    'anthropic/claude-opus-4-5-20251101': 'AIVA-Claude',
    'google/gemini-3-pro-preview': 'AIVA-Gemini', 
    'openai/gpt-5.2': 'AIVA-GPT',
    'claude-opus-4-5-20251101': 'AIVA-Claude',
    'gemini-3-pro-preview': 'AIVA-Gemini',
    'gpt-5.2': 'AIVA-GPT',
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
    """Generate grouped bar charts showing F1 scores by disease category."""
    
    import csv
    
    # Load metrics from TSV
    metrics = defaultdict(lambda: defaultdict(dict))
    
    with open(metrics_tsv, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            cat = row['category']
            model = row['model']
            metrics[cat][model] = {
                'dir_accuracy': float(row['directional_accuracy']),
                'exact_accuracy': float(row.get('exact_accuracy', 0)),
                'plp_f1': float(row['plp_f1']),
                'vus_f1': float(row['vus_f1']),
                'blb_f1': float(row['blb_f1']),
                # Exact 5-class F1 scores
                'exact_p_f1': float(row.get('exact_p_f1', 0)),
                'exact_lp_f1': float(row.get('exact_lp_f1', 0)),
                'exact_vus_f1': float(row.get('exact_vus_f1', 0)),
                'exact_lb_f1': float(row.get('exact_lb_f1', 0)),
                'exact_b_f1': float(row.get('exact_b_f1', 0)),
                'exact_macro_f1': float(row.get('exact_macro_f1', 0)),
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
    
    # Create figure with subplots - 2x2 showing F1 scores
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    x = np.arange(len(categories))
    width = 0.15
    
    # Plot 1: Exact Macro F1 Score (5-class)
    ax = axes[0, 0]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('exact_macro_f1', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=get_short_name(tool),
                     color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('Macro F1 Score (%)')
    ax.set_title('A. Exact 5-Class Macro F1 by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.legend(loc='upper right', fontsize=8)
    ax.set_ylim(0, 105)
    ax.axhline(y=60, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
    
    # Plot 2: P/LP F1 Score (Directional)
    ax = axes[0, 1]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('plp_f1', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=get_short_name(tool),
               color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('F1 Score (%)')
    ax.set_title('B. P/LP F1 Score by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    ax.axhline(y=80, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
    
    # Plot 3: VUS F1 Score (Directional)
    ax = axes[1, 0]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('vus_f1', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=get_short_name(tool),
               color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('F1 Score (%)')
    ax.set_title('C. VUS F1 Score by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    
    # Plot 4: B/LB F1 Score (Directional)
    ax = axes[1, 1]
    for i, tool in enumerate(tools):
        values = [metrics[cat].get(tool, {}).get('blb_f1', 0) for cat in categories]
        offset = (i - len(tools)/2 + 0.5) * width
        ax.bar(x + offset, values, width, label=get_short_name(tool),
               color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
    
    ax.set_ylabel('F1 Score (%)')
    ax.set_title('D. B/LB F1 Score by Disease Category', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_SHORT.get(c, c) for c in categories], rotation=45, ha='right')
    ax.set_ylim(0, 105)
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure2_f1_by_category.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure2_f1_by_category.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 3: Radar/Spider Plot for Multi-Metric Comparison
# =============================================================================

def plot_radar_comparison(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Generate radar plot comparing tools across F1 scores for each class."""
    
    # Calculate F1 scores for each tool (both directional 3-class and exact 5-class)
    def calc_f1_metrics(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact):
        metrics_dict = {}
        
        # Directional F1 scores (3-class)
        dir_f1s = []
        for label in ['P/LP', 'VUS', 'B/LB']:
            tp = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t == label and p != label)
            
            prec = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            
            metrics_dict[f'{label}_f1'] = f1
            dir_f1s.append(f1)
        
        metrics_dict['dir_macro_f1'] = np.mean(dir_f1s) if dir_f1s else 0
        
        # Exact F1 scores (5-class)
        exact_classes = ['Pathogenic', 'Likely Pathogenic', 'Uncertain Significance', 'Likely Benign', 'Benign']
        exact_short = ['P', 'LP', 'VUS', 'LB', 'B']
        exact_f1s = []
        for cls, short in zip(exact_classes, exact_short):
            tp = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t == cls and p == cls)
            fp = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t != cls and p == cls)
            fn = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t == cls and p != cls)
            
            prec = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
            
            metrics_dict[f'{short}_exact_f1'] = f1
            exact_f1s.append(f1)
        
        metrics_dict['exact_macro_f1'] = np.mean(exact_f1s) if exact_f1s else 0
        
        return metrics_dict
    
    tools_metrics = {}
    
    # AIVA models
    for model, variants in aiva_data.items():
        y_true_dir, y_pred_dir = [], []
        y_true_exact, y_pred_exact = [], []
        for v in variants:
            gt = v.get("ground_truth", "")
            pred = v.get("aiva_classification", "")
            if gt and pred and not v.get("error"):
                gt_dir = get_direction(gt)
                pred_dir = get_direction(pred)
                gt_exact = normalize_classification(gt)
                pred_exact = normalize_classification(pred)
                if gt_dir != "unknown" and pred_dir != "unknown":
                    y_true_dir.append(gt_dir)
                    y_pred_dir.append(pred_dir)
                    y_true_exact.append(gt_exact)
                    y_pred_exact.append(pred_exact)
        if y_true_dir:
            tools_metrics[get_short_name(model)] = calc_f1_metrics(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact)
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true_dir, y_pred_dir = [], []
        y_true_exact, y_pred_exact = [], []
        for vid, v in unified_data.items():
            gt = v.get("classification", "")
            pred = v.get(pred_field, "")
            if gt and pred:
                gt_dir = get_direction(gt)
                pred_dir = get_direction(pred)
                gt_exact = normalize_classification(gt)
                pred_exact = normalize_classification(pred)
                if gt_dir != "unknown" and pred_dir != "unknown":
                    y_true_dir.append(gt_dir)
                    y_pred_dir.append(pred_dir)
                    y_true_exact.append(gt_exact)
                    y_pred_exact.append(pred_exact)
        if y_true_dir:
            tools_metrics[tool] = calc_f1_metrics(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact)
    
    # Create figure with two radar charts side by side
    fig, axes = plt.subplots(1, 2, figsize=(16, 8), subplot_kw=dict(projection='polar'))
    
    # Left radar: Directional F1 scores (3-class)
    ax = axes[0]
    dir_labels = ['P/LP F1', 'VUS F1', 'B/LB F1', 'Macro F1']
    dir_keys = ['P/LP_f1', 'VUS_f1', 'B/LB_f1', 'dir_macro_f1']
    
    angles = np.linspace(0, 2 * np.pi, len(dir_labels), endpoint=False).tolist()
    angles += angles[:1]
    
    for tool, metrics in tools_metrics.items():
        values = [metrics.get(k, 0) for k in dir_keys]
        values += values[:1]
        
        color = get_tool_color(tool)
        ax.plot(angles, values, 'o-', linewidth=2, label=tool, color=color, markersize=6)
        ax.fill(angles, values, alpha=0.15, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dir_labels, size=11, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], size=9)
    ax.set_title('A. Directional F1 Scores (3-Class)', fontsize=12, fontweight='bold', y=1.08)
    
    # Right radar: Exact F1 scores (5-class)
    ax = axes[1]
    exact_labels = ['P F1', 'LP F1', 'VUS F1', 'LB F1', 'B F1', 'Macro F1']
    exact_keys = ['P_exact_f1', 'LP_exact_f1', 'VUS_exact_f1', 'LB_exact_f1', 'B_exact_f1', 'exact_macro_f1']
    
    angles = np.linspace(0, 2 * np.pi, len(exact_labels), endpoint=False).tolist()
    angles += angles[:1]
    
    for tool, metrics in tools_metrics.items():
        values = [metrics.get(k, 0) for k in exact_keys]
        values += values[:1]
        
        color = get_tool_color(tool)
        ax.plot(angles, values, 'o-', linewidth=2, label=tool, color=color, markersize=6)
        ax.fill(angles, values, alpha=0.15, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(exact_labels, size=11, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], size=9)
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1), fontsize=10)
    ax.set_title('B. Exact F1 Scores (5-Class)', fontsize=12, fontweight='bold', y=1.08)
    
    plt.suptitle('F1 Score Comparison Across Classification Tools', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    output_path = output_dir / 'figure3_radar_f1_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure3_radar_f1_comparison.pdf', bbox_inches='tight')
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
    """Generate summary bar chart comparing exact accuracy and macro F1 scores."""
    
    def calc_metrics(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact):
        """Calculate both directional and exact metrics."""
        # Directional accuracy
        total_dir = len(y_true_dir)
        correct_dir = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t == p)
        dir_acc = correct_dir / total_dir * 100 if total_dir > 0 else 0
        
        # Exact accuracy
        total_exact = len(y_true_exact)
        correct_exact = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t == p)
        exact_acc = correct_exact / total_exact * 100 if total_exact > 0 else 0
        
        # Directional F1 (macro)
        dir_f1s = []
        for label in ['P/LP', 'VUS', 'B/LB']:
            tp = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true_dir, y_pred_dir) if t == label and p != label)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) * 100 if (prec + rec) > 0 else 0
            dir_f1s.append(f1)
        dir_macro_f1 = np.mean(dir_f1s) if dir_f1s else 0
        
        # Exact F1 (macro over 5 classes)
        exact_classes = ['Pathogenic', 'Likely Pathogenic', 'Uncertain Significance', 'Likely Benign', 'Benign']
        exact_f1s = []
        for cls in exact_classes:
            tp = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t == cls and p == cls)
            fp = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t != cls and p == cls)
            fn = sum(1 for t, p in zip(y_true_exact, y_pred_exact) if t == cls and p != cls)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * prec * rec / (prec + rec) * 100 if (prec + rec) > 0 else 0
            exact_f1s.append(f1)
        exact_macro_f1 = np.mean(exact_f1s) if exact_f1s else 0
        
        return {
            'dir_acc': dir_acc,
            'exact_acc': exact_acc,
            'dir_macro_f1': dir_macro_f1,
            'exact_macro_f1': exact_macro_f1
        }
    
    tools_metrics = {}
    
    # AIVA models
    for model, variants in aiva_data.items():
        y_true_dir, y_pred_dir = [], []
        y_true_exact, y_pred_exact = [], []
        for v in variants:
            gt = v.get("ground_truth", "")
            pred = v.get("aiva_classification", "")
            if gt and pred and not v.get("error"):
                gt_dir = get_direction(gt)
                pred_dir = get_direction(pred)
                gt_exact = normalize_classification(gt)
                pred_exact = normalize_classification(pred)
                if gt_dir != "unknown" and pred_dir != "unknown":
                    y_true_dir.append(gt_dir)
                    y_pred_dir.append(pred_dir)
                    y_true_exact.append(gt_exact)
                    y_pred_exact.append(pred_exact)
        if y_true_dir:
            tools_metrics[get_short_name(model)] = calc_metrics(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact)
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true_dir, y_pred_dir = [], []
        y_true_exact, y_pred_exact = [], []
        for vid, v in unified_data.items():
            gt = v.get("classification", "")
            pred = v.get(pred_field, "")
            if gt and pred:
                gt_dir = get_direction(gt)
                pred_dir = get_direction(pred)
                gt_exact = normalize_classification(gt)
                pred_exact = normalize_classification(pred)
                if gt_dir != "unknown" and pred_dir != "unknown":
                    y_true_dir.append(gt_dir)
                    y_pred_dir.append(pred_dir)
                    y_true_exact.append(gt_exact)
                    y_pred_exact.append(pred_exact)
        if y_true_dir:
            tools_metrics[tool] = calc_metrics(y_true_dir, y_pred_dir, y_true_exact, y_pred_exact)
    
    # Create figure with 2 subplots
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Sort by exact macro F1 (most important metric)
    sorted_tools = sorted(tools_metrics.items(), key=lambda x: x[1]['exact_macro_f1'], reverse=True)
    tools = [t[0] for t in sorted_tools]
    
    # Left plot: Accuracy comparison
    ax = axes[0]
    x = np.arange(len(tools))
    width = 0.35
    
    exact_accs = [tools_metrics[t]['exact_acc'] for t in tools]
    dir_accs = [tools_metrics[t]['dir_acc'] for t in tools]
    colors = [get_tool_color(t) for t in tools]
    
    bars1 = ax.bar(x - width/2, exact_accs, width, label='Exact (5-class)', 
                   color=colors, edgecolor='black', linewidth=1)
    bars2 = ax.bar(x + width/2, dir_accs, width, label='Directional (3-class)',
                   color=colors, edgecolor='black', linewidth=1, alpha=0.6)
    
    # Add value labels
    for bar, val in zip(bars1, exact_accs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    for bar, val in zip(bars2, dir_accs):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title('A. Classification Accuracy\n(Exact vs Directional)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tools, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.set_ylim(0, 100)
    ax.axhline(y=60, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.grid(axis='y', alpha=0.3)
    
    # Right plot: Macro F1 comparison
    ax = axes[1]
    
    exact_f1s = [tools_metrics[t]['exact_macro_f1'] for t in tools]
    dir_f1s = [tools_metrics[t]['dir_macro_f1'] for t in tools]
    
    bars1 = ax.bar(x - width/2, exact_f1s, width, label='Exact (5-class)',
                   color=colors, edgecolor='black', linewidth=1)
    bars2 = ax.bar(x + width/2, dir_f1s, width, label='Directional (3-class)',
                   color=colors, edgecolor='black', linewidth=1, alpha=0.6)
    
    # Add value labels
    for bar, val in zip(bars1, exact_f1s):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    for bar, val in zip(bars2, dir_f1s):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
               f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    
    ax.set_ylabel('Macro F1 Score (%)', fontsize=12)
    ax.set_title('B. Macro F1 Score\n(Exact vs Directional)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tools, rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.set_ylim(0, 100)
    ax.axhline(y=60, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.grid(axis='y', alpha=0.3)
    
    plt.suptitle('Overall Performance Comparison (500-Variant ClinGen Benchmark)', 
                fontsize=14, fontweight='bold', y=1.02)
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
    """Generate heatmap showing AIVA F1 advantage over baselines by category."""
    
    import csv
    
    # Load metrics - use exact macro F1 instead of directional accuracy
    metrics = defaultdict(lambda: defaultdict(dict))
    
    with open(metrics_tsv, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            cat = row['category']
            model = row['model']
            metrics[cat][model] = {
                'exact_acc': float(row.get('exact_accuracy', 0)),
                'exact_macro_f1': float(row.get('exact_macro_f1', 0)),
                'dir_acc': float(row['directional_accuracy']),
            }
    
    categories = [c for c in CATEGORY_ORDER if c in metrics]
    
    # Find best AIVA model per category
    aiva_models = [m for m in list(metrics.values())[0].keys() 
                   if 'claude' in m.lower() or 'gemini' in m.lower() or 'gpt' in m.lower()]
    
    # Calculate differences for exact macro F1
    diff_data = []
    for cat in categories:
        best_aiva_f1 = max([metrics[cat].get(m, {}).get('exact_macro_f1', 0) for m in aiva_models])
        bias_f1 = metrics[cat].get('BIAS-2015', {}).get('exact_macro_f1', 0)
        intervar_f1 = metrics[cat].get('InterVar', {}).get('exact_macro_f1', 0)
        
        diff_data.append({
            'category': CATEGORY_SHORT.get(cat, cat),
            'AIVA vs BIAS-2015': best_aiva_f1 - bias_f1,
            'AIVA vs InterVar': best_aiva_f1 - intervar_f1,
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
                ax=ax, cbar_kws={'label': 'Exact Macro F1 Difference (%)'})
    
    # Add annotations for winners
    for i, row in enumerate(heatmap_data):
        for j, val in enumerate(row):
            symbol = '▲' if val > 0 else '▼' if val < 0 else '='
            ax.text(j + 0.5, i + 0.75, symbol, ha='center', va='center', 
                   fontsize=10, color='white' if abs(val) > 15 else 'black')
    
    ax.set_title('AIVA F1 Score Advantage by Disease Category\n(Exact 5-Class Macro F1, Positive = AIVA Better)', 
                fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure6_f1_heatmap.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure6_f1_heatmap.pdf', bbox_inches='tight')
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
# Figure 8: F1-Score Comparison by Class
# =============================================================================

def plot_f1_comparison(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Generate grouped bar chart comparing F1-scores across tools and classes."""
    
    def calc_f1_scores(y_true, y_pred, labels=['P/LP', 'VUS', 'B/LB']):
        f1_scores = {}
        for label in labels:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            f1_scores[label] = f1 * 100
        
        # Macro F1
        f1_scores['Macro'] = np.mean(list(f1_scores.values()))
        return f1_scores
    
    tools_f1 = {}
    
    # AIVA models
    for model, variants in aiva_data.items():
        y_true, y_pred = [], []
        for v in variants:
            gt = get_direction(v.get("ground_truth", ""))
            pred = get_direction(v.get("aiva_classification", ""))
            if gt != "unknown" and pred != "unknown" and not v.get("error"):
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_f1[get_short_name(model)] = calc_f1_scores(y_true, y_pred)
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true, y_pred = [], []
        for vid, v in unified_data.items():
            gt = get_direction(v.get("classification", ""))
            pred = get_direction(v.get(pred_field, ""))
            if gt != "unknown" and pred != "unknown":
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_f1[tool] = calc_f1_scores(y_true, y_pred)
    
    # Create grouped bar chart
    fig, ax = plt.subplots(figsize=(12, 6))
    
    classes = ['P/LP', 'VUS', 'B/LB', 'Macro']
    x = np.arange(len(classes))
    width = 0.15
    
    # Order tools: AIVA first, then baselines
    tools_order = [t for t in tools_f1.keys() if 'AIVA' in t] + \
                  [t for t in tools_f1.keys() if 'AIVA' not in t]
    
    for i, tool in enumerate(tools_order):
        values = [tools_f1[tool].get(c, 0) for c in classes]
        offset = (i - len(tools_order)/2 + 0.5) * width
        bars = ax.bar(x + offset, values, width, label=tool,
                     color=get_tool_color(tool), edgecolor='black', linewidth=0.5)
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                       f'{val:.0f}', ha='center', va='bottom', fontsize=7, rotation=0)
    
    ax.set_ylabel('F1-Score (%)', fontsize=12)
    ax.set_xlabel('Classification Class', fontsize=12)
    ax.set_title('F1-Score Comparison by Classification Class', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(['Pathogenic/\nLikely Path.', 'VUS', 'Benign/\nLikely Benign', 'Macro\nAverage'])
    ax.legend(loc='upper right', fontsize=9)
    ax.set_ylim(0, 105)
    ax.axhline(y=80, color='gray', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure8_f1_comparison.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure8_f1_comparison.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 9: Model Agreement Heatmap
# =============================================================================

def plot_model_agreement(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Generate heatmap showing pairwise agreement between tools."""
    
    # Collect predictions per variant
    variant_preds = defaultdict(dict)
    
    # AIVA models
    for model, variants in aiva_data.items():
        short_name = get_short_name(model)
        for v in variants:
            vid = v.get("variant_id")
            pred = get_direction(v.get("aiva_classification", ""))
            if vid and pred != "unknown" and not v.get("error"):
                variant_preds[vid][short_name] = pred
    
    # Baselines
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        for vid, v in unified_data.items():
            pred = get_direction(v.get(pred_field, ""))
            if pred != "unknown":
                variant_preds[vid][tool] = pred
    
    # Get all tools that have predictions
    all_tools = set()
    for preds in variant_preds.values():
        all_tools.update(preds.keys())
    
    tools_list = [t for t in all_tools if 'AIVA' in t] + [t for t in all_tools if 'AIVA' not in t]
    
    # Calculate pairwise agreement
    n_tools = len(tools_list)
    agreement_matrix = np.zeros((n_tools, n_tools))
    
    for i, tool1 in enumerate(tools_list):
        for j, tool2 in enumerate(tools_list):
            agree = 0
            total = 0
            for vid, preds in variant_preds.items():
                if tool1 in preds and tool2 in preds:
                    total += 1
                    if preds[tool1] == preds[tool2]:
                        agree += 1
            agreement_matrix[i, j] = agree / total * 100 if total > 0 else 0
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(8, 7))
    
    mask = np.triu(np.ones_like(agreement_matrix, dtype=bool), k=1)
    
    sns.heatmap(agreement_matrix, annot=True, fmt='.1f', cmap='RdYlGn',
                xticklabels=tools_list, yticklabels=tools_list,
                ax=ax, vmin=50, vmax=100, cbar_kws={'label': 'Agreement (%)'},
                mask=mask, square=True)
    
    # Fill diagonal with 100%
    for i in range(n_tools):
        ax.text(i + 0.5, i + 0.5, '100.0', ha='center', va='center', fontsize=10, fontweight='bold')
    
    ax.set_title('Pairwise Agreement Between Classification Tools', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure9_model_agreement.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure9_model_agreement.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 10: Error Analysis - Misclassification Patterns
# =============================================================================

def plot_error_analysis(aiva_data: Dict, unified_data: Dict, output_dir: Path):
    """Analyze and visualize misclassification patterns."""
    
    # Find best AIVA model
    best_model = None
    best_acc = 0
    
    for model, variants in aiva_data.items():
        correct = sum(1 for v in variants 
                     if get_direction(v.get("ground_truth", "")) == get_direction(v.get("aiva_classification", ""))
                     and not v.get("error"))
        total = sum(1 for v in variants if not v.get("error"))
        acc = correct / total if total > 0 else 0
        if acc > best_acc:
            best_acc = acc
            best_model = model
    
    if not best_model:
        print("No AIVA model found for error analysis")
        return
    
    # Collect misclassifications for best AIVA model
    misclass_types = defaultdict(int)
    correct_types = defaultdict(int)
    
    for v in aiva_data[best_model]:
        gt = get_direction(v.get("ground_truth", ""))
        pred = get_direction(v.get("aiva_classification", ""))
        
        if gt == "unknown" or pred == "unknown" or v.get("error"):
            continue
        
        if gt == pred:
            correct_types[gt] += 1
        else:
            misclass_types[(gt, pred)] += 1
    
    # Create Sankey-like flow diagram using stacked bars
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Left plot: Confusion flow
    ax = axes[0]
    
    labels = ['P/LP', 'VUS', 'B/LB']
    colors = {'P/LP': '#d62728', 'VUS': '#ff7f0e', 'B/LB': '#2ca02c'}
    
    # For each true class, show where predictions went
    x = np.arange(len(labels))
    bottom = np.zeros(len(labels))
    
    for pred_class in labels:
        heights = []
        for true_class in labels:
            if true_class == pred_class:
                heights.append(correct_types.get(true_class, 0))
            else:
                heights.append(misclass_types.get((true_class, pred_class), 0))
        
        ax.bar(x, heights, bottom=bottom, label=f'Pred: {pred_class}', 
               color=colors[pred_class], edgecolor='black', linewidth=0.5, alpha=0.8)
        bottom += heights
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'True:\n{l}' for l in labels])
    ax.set_ylabel('Number of Variants')
    ax.set_title(f'Classification Distribution by True Class\n({get_short_name(best_model)})', 
                fontweight='bold')
    ax.legend(loc='upper right')
    
    # Right plot: Error breakdown pie chart
    ax = axes[1]
    
    error_counts = []
    error_labels = []
    error_colors = []
    
    cmap = plt.cm.Set3
    for i, ((true_c, pred_c), count) in enumerate(sorted(misclass_types.items(), key=lambda x: -x[1])):
        if count > 0:
            error_counts.append(count)
            error_labels.append(f'{true_c} → {pred_c}\n(n={count})')
            error_colors.append(cmap(i % 12))
    
    if error_counts:
        wedges, texts, autotexts = ax.pie(error_counts, labels=error_labels, autopct='%1.1f%%',
                                          colors=error_colors, explode=[0.02]*len(error_counts))
        ax.set_title(f'Misclassification Breakdown\n({get_short_name(best_model)})', fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No errors!', ha='center', va='center', fontsize=14)
        ax.set_title('Misclassification Breakdown', fontweight='bold')
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure10_error_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure10_error_analysis.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 11: Performance vs Sample Size
# =============================================================================

def plot_performance_vs_sample_size(metrics_tsv: Path, output_dir: Path):
    """Scatter plot showing relationship between category sample size and accuracy."""
    
    import csv
    
    # Load metrics
    data_points = []
    
    with open(metrics_tsv, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            data_points.append({
                'category': row['category'],
                'model': row['model'],
                'n': int(row['n_variants']),
                'accuracy': float(row['directional_accuracy'])
            })
    
    # Get unique categories and their sizes
    cat_sizes = {}
    for d in data_points:
        cat_sizes[d['category']] = d['n']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Plot each tool
    tools = set(d['model'] for d in data_points)
    tools_order = [t for t in tools if 'claude' in t.lower() or 'gemini' in t.lower() or 'gpt' in t.lower()]
    tools_order += [t for t in tools if t in ['BIAS-2015', 'InterVar']]
    
    for tool in tools_order:
        tool_data = [d for d in data_points if d['model'] == tool]
        x = [d['n'] for d in tool_data]
        y = [d['accuracy'] for d in tool_data]
        
        short_name = get_short_name(tool)
        ax.scatter(x, y, s=100, label=short_name, color=get_tool_color(short_name),
                  edgecolors='black', linewidth=0.5, alpha=0.8)
    
    # Add category labels for the best performing tool's points
    best_tool = 'gemini-3-pro-preview'
    for d in data_points:
        if best_tool in d['model'].lower():
            ax.annotate(CATEGORY_SHORT.get(d['category'], d['category'][:8]), 
                       (d['n'], d['accuracy']), xytext=(5, 5),
                       textcoords='offset points', fontsize=7, alpha=0.7)
    
    ax.set_xlabel('Number of Variants in Category', fontsize=12)
    ax.set_ylabel('Directional Accuracy (%)', fontsize=12)
    ax.set_title('Performance vs Sample Size by Disease Category', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    # Add trend line for best AIVA
    tool_data = [d for d in data_points if 'gemini' in d['model'].lower()]
    if tool_data:
        x = np.array([d['n'] for d in tool_data])
        y = np.array([d['accuracy'] for d in tool_data])
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        ax.plot(sorted(x), p(sorted(x)), '--', color='#28A745', alpha=0.5, linewidth=2)
    
    plt.tight_layout()
    
    output_path = output_dir / 'figure11_performance_vs_size.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure11_performance_vs_size.pdf', bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


# =============================================================================
# Figure 12: Combined Summary Figure (for paper main figure)
# =============================================================================

def plot_main_summary_figure(aiva_data: Dict, unified_data: Dict, metrics_tsv: Path, output_dir: Path):
    """Create a comprehensive multi-panel summary figure for publication."""
    
    import csv
    
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Helper function for metrics
    def calc_metrics_for_tool(y_true, y_pred):
        total = len(y_true)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / total * 100 if total > 0 else 0
        
        metrics = {'accuracy': accuracy}
        for label in ['P/LP', 'VUS', 'B/LB']:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
            
            sens = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
            prec = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
            f1 = 2 * sens * prec / (sens + prec) if (sens + prec) > 0 else 0
            
            metrics[f'{label}_sens'] = sens
            metrics[f'{label}_f1'] = f1
        
        return metrics
    
    # Collect data for all tools
    tools_metrics = {}
    
    for model, variants in aiva_data.items():
        y_true, y_pred = [], []
        for v in variants:
            gt = get_direction(v.get("ground_truth", ""))
            pred = get_direction(v.get("aiva_classification", ""))
            if gt != "unknown" and pred != "unknown" and not v.get("error"):
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_metrics[get_short_name(model)] = calc_metrics_for_tool(y_true, y_pred)
    
    for tool, pred_field in [("BIAS-2015", "bias_classification"), ("InterVar", "intervar_classification")]:
        y_true, y_pred = [], []
        for vid, v in unified_data.items():
            gt = get_direction(v.get("classification", ""))
            pred = get_direction(v.get(pred_field, ""))
            if gt != "unknown" and pred != "unknown":
                y_true.append(gt)
                y_pred.append(pred)
        if y_true:
            tools_metrics[tool] = calc_metrics_for_tool(y_true, y_pred)
    
    # Panel A: Overall accuracy comparison
    ax_a = fig.add_subplot(gs[0, 0])
    tools_order = ['AIVA-Gemini', 'AIVA-Claude', 'AIVA-GPT', 'BIAS-2015', 'InterVar']
    tools_order = [t for t in tools_order if t in tools_metrics]
    
    accuracies = [tools_metrics[t]['accuracy'] for t in tools_order]
    colors = [get_tool_color(t) for t in tools_order]
    
    bars = ax_a.bar(tools_order, accuracies, color=colors, edgecolor='black', linewidth=1)
    ax_a.set_ylabel('Accuracy (%)')
    ax_a.set_title('A. Overall Directional Accuracy', fontweight='bold')
    ax_a.set_ylim(0, 100)
    ax_a.axhline(y=80, color='gray', linestyle='--', alpha=0.5)
    
    for bar, acc in zip(bars, accuracies):
        ax_a.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'{acc:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax_a.tick_params(axis='x', rotation=45)
    
    # Panel B: Sensitivity by class
    ax_b = fig.add_subplot(gs[0, 1])
    classes = ['P/LP', 'VUS', 'B/LB']
    x = np.arange(len(classes))
    width = 0.15
    
    for i, tool in enumerate(tools_order):
        values = [tools_metrics[tool].get(f'{c}_sens', 0) for c in classes]
        offset = (i - len(tools_order)/2 + 0.5) * width
        ax_b.bar(x + offset, values, width, label=tool, color=get_tool_color(tool),
                edgecolor='black', linewidth=0.5)
    
    ax_b.set_ylabel('Sensitivity (%)')
    ax_b.set_title('B. Sensitivity by Classification Class', fontweight='bold')
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(['P/LP', 'VUS', 'B/LB'])
    ax_b.legend(loc='upper right', fontsize=7)
    ax_b.set_ylim(0, 105)
    
    # Panel C: F1-Score comparison
    ax_c = fig.add_subplot(gs[0, 2])
    
    for i, tool in enumerate(tools_order):
        values = [tools_metrics[tool].get(f'{c}_f1', 0) for c in classes]
        offset = (i - len(tools_order)/2 + 0.5) * width
        ax_c.bar(x + offset, values, width, label=tool, color=get_tool_color(tool),
                edgecolor='black', linewidth=0.5)
    
    ax_c.set_ylabel('F1-Score (%)')
    ax_c.set_title('C. F1-Score by Classification Class', fontweight='bold')
    ax_c.set_xticks(x)
    ax_c.set_xticklabels(['P/LP', 'VUS', 'B/LB'])
    ax_c.set_ylim(0, 105)
    
    # Panel D: Performance by category (load from TSV)
    ax_d = fig.add_subplot(gs[1, :2])
    
    if metrics_tsv and metrics_tsv.exists():
        cat_metrics = defaultdict(lambda: defaultdict(float))
        with open(metrics_tsv, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                cat = CATEGORY_SHORT.get(row['category'], row['category'][:10])
                model = get_short_name(row['model'])
                cat_metrics[cat][model] = float(row['directional_accuracy'])
        
        categories = list(cat_metrics.keys())[:10]
        x = np.arange(len(categories))
        
        for i, tool in enumerate(tools_order):
            values = [cat_metrics[cat].get(tool, 0) for cat in categories]
            offset = (i - len(tools_order)/2 + 0.5) * width
            ax_d.bar(x + offset, values, width, label=tool, color=get_tool_color(tool),
                    edgecolor='black', linewidth=0.5)
        
        ax_d.set_ylabel('Accuracy (%)')
        ax_d.set_title('D. Performance by Disease Category', fontweight='bold')
        ax_d.set_xticks(x)
        ax_d.set_xticklabels(categories, rotation=45, ha='right')
        ax_d.legend(loc='upper right', fontsize=7)
        ax_d.set_ylim(0, 105)
        ax_d.axhline(y=80, color='gray', linestyle='--', alpha=0.5)
    
    # Panel E: AIVA advantage heatmap
    ax_e = fig.add_subplot(gs[1, 2])
    
    if metrics_tsv and metrics_tsv.exists():
        # Find best AIVA per category and compare to baselines
        advantages = []
        cat_labels = []
        
        for cat in categories:
            best_aiva = max([cat_metrics[cat].get(t, 0) for t in tools_order if 'AIVA' in t])
            bias_acc = cat_metrics[cat].get('BIAS-2015', 0)
            intervar_acc = cat_metrics[cat].get('InterVar', 0)
            
            advantages.append([best_aiva - bias_acc, best_aiva - intervar_acc])
            cat_labels.append(cat)
        
        advantages = np.array(advantages)
        
        cmap = sns.diverging_palette(10, 130, as_cmap=True)
        sns.heatmap(advantages, annot=True, fmt='+.1f', cmap=cmap, center=0,
                   xticklabels=['vs BIAS', 'vs InterVar'], yticklabels=cat_labels,
                   ax=ax_e, cbar_kws={'label': 'Δ Accuracy (%)'})
        
        ax_e.set_title('E. AIVA Advantage', fontweight='bold')
    
    plt.suptitle('AIVA Variant Classification Performance Summary\n(500-Variant ClinGen Benchmark)', 
                fontsize=16, fontweight='bold', y=1.02)
    
    output_path = output_dir / 'figure_main_summary.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'figure_main_summary.pdf', bbox_inches='tight')
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
    print("  [1/13] Confusion matrices...")
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
        print("  [2/13] Performance by category...")
        plot_performance_by_category(metrics_tsv, output_dir)
        
        print("  [6/13] Performance heatmap...")
        plot_performance_heatmap(metrics_tsv, output_dir)
        
        print("  [11/13] Performance vs sample size...")
        plot_performance_vs_sample_size(metrics_tsv, output_dir)
    else:
        print("  [2/13] Skipping (metrics_by_category.tsv not found)")
        print("  [6/13] Skipping (metrics_by_category.tsv not found)")
        print("  [11/13] Skipping (metrics_by_category.tsv not found)")
    
    # Figure 3: Radar plot
    print("  [3/13] Radar comparison...")
    plot_radar_comparison(aiva_data, unified_data, output_dir)
    
    # Figure 4: ROC curves
    print("  [4/13] ROC curves...")
    plot_roc_curves(aiva_data, unified_data, output_dir)
    
    # Figure 5: Summary comparison
    print("  [5/13] Summary comparison...")
    plot_summary_comparison(aiva_data, unified_data, output_dir)
    
    # Figure 7: Exact vs Directional
    print("  [7/13] Exact vs Directional scatter...")
    plot_exact_vs_directional(aiva_data, unified_data, output_dir)
    
    # Figure 8: F1-Score comparison
    print("  [8/13] F1-score comparison...")
    plot_f1_comparison(aiva_data, unified_data, output_dir)
    
    # Figure 9: Model agreement heatmap
    print("  [9/13] Model agreement heatmap...")
    plot_model_agreement(aiva_data, unified_data, output_dir)
    
    # Figure 10: Error analysis
    print("  [10/13] Error analysis...")
    plot_error_analysis(aiva_data, unified_data, output_dir)
    
    # Figure 12: Main summary figure (multi-panel)
    if metrics_tsv and metrics_tsv.exists():
        print("  [12/13] Main summary figure...")
        plot_main_summary_figure(aiva_data, unified_data, metrics_tsv, output_dir)
    else:
        print("  [12/13] Skipping main summary (metrics_by_category.tsv not found)")
    
    print(f"\n✅ All figures saved to {output_dir}/")
    print("\nGenerated files:")
    for f in sorted(output_dir.glob("figure*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()
