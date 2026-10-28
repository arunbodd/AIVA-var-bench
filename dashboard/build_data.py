#!/usr/bin/env python3
"""
Dashboard Data Builder for AIVA Variant Benchmarking.

Scans all model results across AIVA-var-bench, computes comprehensive
metrics, confusion matrices, disease category breakdowns, safety audits,
ACMG criteria frequencies, and pairwise concordance, and outputs a single
JSON dataset consumed by dashboard/generate_html.py.

Dynamic & Extensible: Re-running this script or adding any new result file
instantly refreshes the dashboard.
"""

import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from config import CLASSIFICATION_LABELS, DIRECTION_LABELS, CLASSIFICATION_TO_DIRECTION
from scripts.metrics import (
    normalize_classification,
    get_direction,
    normalize_criterion,
    calculate_class_metrics,
    calculate_direction_metrics,
    calculate_macro_f1,
)
from scripts.generate_results import VCEP_TO_CATEGORY, CATEGORY_ORDER


# One fixed colour per model, used by every dashboard figure.
MODEL_COLORS = {
    "aiva_opus_rerun": "#eb6834",
    "aiva_sonnet_rerun": "#6250d6",
    "aiva_haiku_rerun": "#1baf7a",
    "claude_code_haiku": "#eda100",
    "aiva_gemini_pro": "#184f95",
    "aiva_gemini_flash": "#d55181",
    "baseline_bias": "#0097a7",
    "baseline_intervar": "#5c4033",
}
# Lighter steps for colours that are too dark to read on the dark theme.
MODEL_COLORS_DARK = {
    "baseline_intervar": "#a8835c",
    "aiva_gemini_pro": "#4f86d0",
}
# Models removed from the dashboard (one key per line) and results imported
# through the local dashboard server (tab-separated: key, name, family, path).
EXCLUDED_FILE = REPO_ROOT / "dashboard" / "excluded_models.txt"
IMPORTED_FILE = REPO_ROOT / "dashboard" / "imported_models.tsv"


def read_excluded() -> set[str]:
    if not EXCLUDED_FILE.exists():
        return set()
    keys = (line.split("#")[0].strip() for line in EXCLUDED_FILE.read_text(encoding="utf-8").splitlines())
    return {k for k in keys if k}


def read_imported() -> list[dict]:
    if not IMPORTED_FILE.exists():
        return []
    rows = []
    for line in IMPORTED_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 4 and not line.startswith("#"):
            rows.append(dict(zip(("key", "name", "family", "path"), parts)))
    return rows


# Initial runs superseded by re-runs; they are not shown on the dashboard.
RETIRED_MODELS = {"aiva_haiku_initial", "aiva_sonnet_initial", "aiva_opus_initial"}
RETIRED_RESULT_DIRS = {
    "Results_Claude_Haiku_5_5_Analysis",
    "Results_Claude_Sonnet_5_5_Analysis",
    "Results_Claude_Opus_5_5_Analysis",
}

FALLBACK_COLORS = ["#008300", "#e34948", "#0d366b", "#8c5a2b"]


def get_vcep_category(panel: str) -> str:
    if not panel:
        return "Other"
    return VCEP_TO_CATEGORY.get(panel.strip(), "Other")


def load_unified_data(path: Path) -> tuple[dict, dict]:
    """Load unified dataset: id -> variant dict, and id -> metadata dict."""
    variants = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                vid = item["id"]
                gt_norm = normalize_classification(item.get("classification", ""))
                panel = item.get("expert_panel", "")
                cat = get_vcep_category(panel)
                variants[vid] = {
                    "id": vid,
                    "gene": item.get("gene_symbol", ""),
                    "variation": item.get("variation", ""),
                    "variant_key": item.get("variant_key", ""),
                    "disease": item.get("disease", ""),
                    "expert_panel": panel,
                    "category": cat,
                    "ground_truth": gt_norm,
                    "ground_truth_direction": get_direction(gt_norm),
                    "criteria_met": [normalize_criterion(c) for c in (item.get("criteria_met") or [])],
                    "intervar_classification": normalize_classification(item.get("intervar_classification", "")),
                    "intervar_criteria": [normalize_criterion(c) for c in (item.get("intervar_criteria") or [])],
                    "bias_classification": normalize_classification(item.get("bias_classification", "")),
                    "bias_criteria": [normalize_criterion(c) for c in (item.get("bias_criteria") or [])],
                }
    return variants


def discover_model_files(repo_root: Path) -> dict[str, dict]:
    """
    Auto-discover all model results available in the repository.
    Returns mapping of model_key -> metadata dict.
    """
    discovered = {}

    # 1. Claude-Code Haiku Manual Prompt
    cc_path = repo_root / "Claude_code_results" / "acmg_classifications_manual_Haiku.json"
    if cc_path.exists():
        discovered["claude_code_haiku"] = {
            "name": "Claude-Code Haiku 5.5",
            "short_name": "Claude-Code Haiku 5.5",
            "family": "Anthropic Claude",
            "is_anthropic": True,
            "type": "Direct Prompt (Claude Code)",
            "path": str(cc_path),
            "format": "json_array",
            "color": "#D97706",
            "description": "Direct zero-shot prompting via Claude Code CLI without external clinical retrieval tools.",
        }

    # 2. AIVA Claude Haiku Re-Run
    haiku_rr = repo_root / "Results_Claude_Haiku_5_5_Analysis_rerun" / "haiku_full.jsonl"
    if haiku_rr.exists():
        discovered["aiva_haiku_rerun"] = {
            "name": "AIVA-Haiku-5.5",
            "short_name": "AIVA-Haiku-5.5",
            "family": "Anthropic Claude",
            "is_anthropic": True,
            "type": "Autonomous Agent (AIVA)",
            "path": str(haiku_rr),
            "format": "jsonl",
            "color": "#2563EB",
            "description": "AIVA multi-step clinical reasoning engine powered by Claude Haiku 5.5 across full cohort (re-run).",
        }

    # 3. AIVA Claude Sonnet Re-Run (partial runs are included; coverage is reported)
    sonnet_rr = repo_root / "Results_Claude_Sonnet_5_5_Analysis_rerun" / "sonnet_full.jsonl"
    if sonnet_rr.exists():
        if True:
            discovered["aiva_sonnet_rerun"] = {
                "name": "AIVA-Sonnet-5.5",
                "short_name": "AIVA-Sonnet-5.5",
                "family": "Anthropic Claude",
                "is_anthropic": True,
                "type": "Autonomous Agent (AIVA)",
                "path": str(sonnet_rr),
                "format": "jsonl",
                "color": "#9333EA",
                "description": "Re-run of Claude Sonnet 5.5 with the revised ACMG criteria engine.",
            }

    # 4. AIVA Claude Opus Re-Run (partial runs are included; coverage is reported)
    opus_rr = repo_root / "Results_Claude_Opus_5_5_Analysis_rerun" / "opus_full.jsonl"
    if opus_rr.exists():
        if True:
            discovered["aiva_opus_rerun"] = {
                "name": "AIVA-Opus-5.5",
                "short_name": "AIVA-Opus-5.5",
                "family": "Anthropic Claude",
                "is_anthropic": True,
                "type": "Autonomous Agent (AIVA)",
                "path": str(opus_rr),
                "format": "jsonl",
                "color": "#C2410C",
                "description": "Re-run of Claude Opus 5.5; may cover part of the cohort while in progress.",
            }

    # 5. AIVA Gemini 3 Pro
    gemini_pro = repo_root / "Results_Gemini_Pro_Analysis" / "classifications_google_gemini-3-pro-preview_combined.jsonl"
    if gemini_pro.exists():
        discovered["aiva_gemini_pro"] = {
            "name": "AIVA-Gemini-3-Pro",
            "short_name": "AIVA-Gemini-3-Pro",
            "family": "Google Gemini",
            "is_anthropic": False,
            "type": "Autonomous Agent (AIVA)",
            "path": str(gemini_pro),
            "format": "jsonl",
            "color": "#059669",
            "description": "AIVA engine powered by Gemini 3 Pro Preview across 8,387 variants.",
        }

    # 6. AIVA Gemini 3.8 Flash
    gemini_flash = repo_root / "Results_Gemini_3_8_Flash_Analysis" / "gemini_flash_2627.jsonl"
    if gemini_flash.exists():
        discovered["aiva_gemini_flash"] = {
            "name": "AIVA-Gemini-3.8-Flash",
            "short_name": "AIVA-Gemini-3.8-Flash",
            "family": "Google Gemini",
            "is_anthropic": False,
            "type": "Autonomous Agent (AIVA)",
            "path": str(gemini_flash),
            "format": "jsonl",
            "color": "#10B981",
            "description": "AIVA engine powered by Gemini 3.8 Flash (2,627 variant subset).",
        }

    # 7. Dynamic Scan for other Results_* directories
    for res_dir in sorted(glob.glob(str(repo_root / "Results_*"))):
        res_path = Path(res_dir)
        d_name = res_path.name
        # Skip re-runs (managed above), retired initial runs, and registered dirs
        if "_rerun" in d_name.lower() or d_name in RETIRED_RESULT_DIRS or any(d_name in m["path"] for m in discovered.values()):
            continue
        # Check for jsonl
        j_files = list(res_path.glob("*.jsonl"))
        if j_files:
            target_f = max(j_files, key=lambda f: f.stat().st_size)
            clean_name = d_name.replace("Results_", "").replace("_Analysis", "").replace("_", " ")
            key = f"custom_{clean_name.lower().replace(' ', '_')}"
            discovered[key] = {
                "name": f"{clean_name} (AIVA)",
                "short_name": clean_name[:16],
                "family": "Other Models",
                "is_anthropic": "claude" in clean_name.lower() or "anthropic" in clean_name.lower(),
                "type": "Custom Benchmark",
                "path": str(target_f),
                "format": "jsonl",
                "color": "#6B7280",
                "description": f"Auto-discovered benchmark results from {d_name}.",
            }

    # 8. Results imported through the dashboard server
    for row in read_imported():
        path = REPO_ROOT / row["path"]
        if path.exists():
            discovered[row["key"]] = {
                "name": row["name"],
                "short_name": row["name"] if len(row["name"]) <= 22 else row["name"][:21] + "…",
                "family": row["family"],
                "is_anthropic": row["family"] == "Anthropic Claude",
                "type": "Imported results",
                "path": str(path),
                "format": "jsonl",
                "color": "",
                "description": "Imported through the dashboard.",
            }

    # 9. Classical Baselines
    discovered["baseline_bias"] = {
        "name": "BIAS-2015",
        "short_name": "BIAS-2015",
        "family": "Classical ACMG Tools",
        "is_anthropic": False,
        "type": "Algorithmic Rules",
        "path": "unified:bias_classification",
        "format": "unified_field",
        "color": "#64748B",
        "description": "Classical rule-based ACMG classification tool (BIAS-2015).",
    }
    discovered["baseline_intervar"] = {
        "name": "InterVar",
        "short_name": "InterVar",
        "family": "Classical ACMG Tools",
        "is_anthropic": False,
        "type": "Algorithmic Rules",
        "path": "unified:intervar_classification",
        "format": "unified_field",
        "color": "#94A3B8",
        "description": "Clinical bioinformatics standard rule-based variant classifier (InterVar).",
    }

    extra = 0
    for key, info in discovered.items():
        if key in MODEL_COLORS_DARK:
            info["color_dark"] = MODEL_COLORS_DARK[key]
        if key in MODEL_COLORS:
            info["color"] = MODEL_COLORS[key]
        else:
            info["color"] = FALLBACK_COLORS[extra % len(FALLBACK_COLORS)]
            extra += 1

    return discovered


def load_model_predictions(model_info: dict, unified_dict: dict) -> dict[str, dict]:
    """
    Load variant_id -> {prediction, criteria, time_ms, raw} for a given model.
    """
    fmt = model_info["format"]
    path_str = model_info["path"]
    preds = {}

    if fmt == "unified_field":
        field = path_str.split(":")[1]
        crit_field = "bias_criteria" if "bias" in field else "intervar_criteria"
        for vid, v in unified_dict.items():
            p_raw = v.get(field, "")
            preds[vid] = {
                "prediction": p_raw,
                "criteria": v.get(crit_field, []),
                "execution_time_ms": 0,
                "error": None,
            }
        return preds

    if fmt == "json_array":
        with open(path_str, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            vid = item.get("id")
            if not vid:
                continue
            crit = list(item.get("criteria", {}).get("met", {}).keys())
            preds[vid] = {
                "prediction": normalize_classification(item.get("classification", "")),
                "criteria": [normalize_criterion(c) for c in crit],
                "execution_time_ms": item.get("execution_time_ms", 0),
                "error": None,
                "confidence": item.get("confidence", ""),
                "rationale": item.get("disease_context", ""),
            }
        return preds

    if fmt == "jsonl":
        with open(path_str, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                vid = item.get("variant_id") or item.get("id")
                if not vid:
                    continue
                cls_raw = item.get("aiva_classification") or item.get("classification", "")
                err = item.get("error")
                if err or not cls_raw or cls_raw == "Not classified":
                    continue
                preds[vid] = {
                    "prediction": normalize_classification(cls_raw),
                    "criteria": [normalize_criterion(c) for c in (item.get("aiva_criteria") or item.get("criteria") or [])],
                    "execution_time_ms": item.get("execution_time_ms", 0),
                    "error": err,
                    "confidence": item.get("aiva_confidence", ""),
                    "evidence": item.get("aiva_evidence", {}),
                }
        return preds

    return preds


def build_dashboard_dataset():
    print(f"[{datetime.now().strftime('%T')}] Initializing Dashboard Data Builder...")
    unified_path = REPO_ROOT / "data" / "erepo_bias_intervar_merged.jsonl"
    print(f"Loading Ground Truth & Baselines from {unified_path}...")
    unified_dict = load_unified_data(unified_path)
    total_cohort = len(unified_dict)
    print(f"Loaded {total_cohort} ClinGen expert curated variants.")

    models_info = discover_model_files(REPO_ROOT)
    excluded = read_excluded()
    excluded_models = [{"key": k, "name": m["name"]} for k, m in models_info.items() if k in excluded]
    models_info = {k: m for k, m in models_info.items() if k not in excluded}
    print(f"Discovered {len(models_info)} models and baselines:")
    for k, m in models_info.items():
        print(f"  • [{m['family']}] {m['name']} ({m['format']})")

    # Load predictions for all models
    model_predictions = {}
    for m_key, m_info in models_info.items():
        print(f"Loading predictions for {m_key}...")
        preds = load_model_predictions(m_info, unified_dict)
        model_predictions[m_key] = preds
        print(f"  -> {len(preds)} valid predictions loaded.")

    # -------------------------------------------------------------------------
    # COMPUTE COMPREHENSIVE METRICS FOR EACH MODEL
    # -------------------------------------------------------------------------
    models_summary = []
    models_confusion = {}
    models_categories = {}
    models_criteria = {}
    models_safety = {}
    models_latency = {}

    all_criteria_set = set([
        "PVS1", "PS1", "PS2", "PS3", "PS4",
        "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
        "PP1", "PP2", "PP3", "PP4", "PP5",
        "BA1", "BS1", "BS2", "BS3", "BS4",
        "BP1", "BP2", "BP3", "BP4", "BP5", "BP7"
    ])

    for m_key, m_info in models_info.items():
        preds = model_predictions[m_key]
        if not preds:
            continue

        evaluated_ids = [vid for vid in unified_dict if vid in preds]
        n_eval = len(evaluated_ids)
        if n_eval == 0:
            continue

        gt_5 = [unified_dict[vid]["ground_truth"] for vid in evaluated_ids]
        pred_5 = [preds[vid]["prediction"] for vid in evaluated_ids]

        gt_3 = [unified_dict[vid]["ground_truth_direction"] for vid in evaluated_ids]
        pred_3 = [get_direction(p) for p in pred_5]

        # Overall exact and directional matches
        exact_matches = sum(1 for g, p in zip(gt_5, pred_5) if g == p and g != "")
        directional_matches = sum(1 for g, p in zip(gt_3, pred_3) if g == p and g in DIRECTION_LABELS)

        exact_acc = round(exact_matches / n_eval * 100, 2)
        dir_acc = round(directional_matches / n_eval * 100, 2)

        # Per-class 5-class metrics
        per_class_5 = calculate_class_metrics(gt_5, pred_5, CLASSIFICATION_LABELS)
        macro_f1_5 = round(calculate_macro_f1(per_class_5) * 100, 2)

        # Per-direction 3-class metrics
        per_class_3 = calculate_direction_metrics(gt_3, pred_3, DIRECTION_LABELS)
        valid_3_f1s = [per_class_3[d.lower()]["f1"] for d in DIRECTION_LABELS if per_class_3.get(d.lower(), {}).get("support", 0) > 0]
        macro_f1_3 = round((sum(valid_3_f1s) / len(valid_3_f1s) * 100) if valid_3_f1s else 0, 2)

        # Safety / Critical Clinical Errors:
        # 1. False Pathogenic (Type I): Ground truth is Benign/Likely Benign, but model called Pathogenic/Likely Pathogenic
        # 2. False Benign (Type II): Ground truth is Pathogenic/Likely Pathogenic, but model called Benign/Likely Benign
        false_pathogenic_ids = []
        false_benign_ids = []

        for vid in evaluated_ids:
            g_dir = (unified_dict[vid]["ground_truth_direction"] or "").lower()
            p_dir = (get_direction(preds[vid]["prediction"]) or "").lower()
            if g_dir == "benign" and p_dir == "pathogenic":
                false_pathogenic_ids.append(vid)
            elif g_dir == "pathogenic" and p_dir == "benign":
                false_benign_ids.append(vid)

        type1_err_count = len(false_pathogenic_ids)
        type2_err_count = len(false_benign_ids)
        total_critical = type1_err_count + type2_err_count
        critical_error_rate = round(total_critical / n_eval * 100, 2)

        # Criteria frequencies
        crit_counter = Counter()
        for vid in evaluated_ids:
            for c in preds[vid]["criteria"]:
                if c:
                    crit_counter[c] += 1

        # Execution latency
        times = [preds[vid]["execution_time_ms"] for vid in evaluated_ids if preds[vid].get("execution_time_ms", 0) > 0]
        avg_time = round(sum(times) / len(times) / 1000, 1) if times else 0.0

        # Model Summary Object
        summary_obj = {
            "key": m_key,
            "name": m_info["name"],
            "short_name": m_info["short_name"],
            "family": m_info["family"],
            "is_anthropic": m_info["is_anthropic"],
            "type": m_info["type"],
            "color": m_info["color"],
            "color_dark": m_info.get("color_dark", m_info["color"]),
            "description": m_info["description"],
            "evaluated_count": n_eval,
            "total_cohort": total_cohort,
            "coverage_pct": round(n_eval / total_cohort * 100, 1),
            "exact_accuracy": exact_acc,
            "directional_accuracy": dir_acc,
            "macro_f1_5": macro_f1_5,
            "macro_f1_3": macro_f1_3,
            "critical_error_count": total_critical,
            "critical_error_rate": critical_error_rate,
            "false_pathogenic_count": type1_err_count,
            "false_benign_count": type2_err_count,
            "avg_latency_sec": avg_time,
            "per_class_5": {
                c: {
                    "precision": round(per_class_5[c]["precision"] * 100, 2),
                    "recall": round(per_class_5[c]["recall"] * 100, 2),
                    "f1": round(per_class_5[c]["f1"] * 100, 2),
                    "support": per_class_5[c]["support"],
                    "tp": per_class_5[c]["true_positives"],
                    "fp": per_class_5[c]["false_positives"],
                    "fn": per_class_5[c]["false_negatives"],
                }
                for c in CLASSIFICATION_LABELS
            },
            "per_class_3": {
                d: {
                    "precision": round(per_class_3.get(d.lower(), {}).get("precision", 0) * 100, 2),
                    "recall": round(per_class_3.get(d.lower(), {}).get("recall", 0) * 100, 2),
                    "f1": round(per_class_3.get(d.lower(), {}).get("f1", 0) * 100, 2),
                    "support": per_class_3.get(d.lower(), {}).get("support", 0),
                }
                for d in DIRECTION_LABELS
            },
        }
        models_summary.append(summary_obj)

        # 5x5 Confusion Matrix
        cm5 = [[0 for _ in range(5)] for _ in range(5)]
        for g, p in zip(gt_5, pred_5):
            if g in CLASSIFICATION_LABELS and p in CLASSIFICATION_LABELS:
                cm5[CLASSIFICATION_LABELS.index(g)][CLASSIFICATION_LABELS.index(p)] += 1

        # 3x3 Confusion Matrix
        cm3 = [[0 for _ in range(3)] for _ in range(3)]
        d_lower_labels = [d.lower() for d in DIRECTION_LABELS]
        for g, p in zip(gt_3, pred_3):
            g_low = (g or "").lower()
            p_low = (p or "").lower()
            if g_low in d_lower_labels and p_low in d_lower_labels:
                cm3[d_lower_labels.index(g_low)][d_lower_labels.index(p_low)] += 1

        models_confusion[m_key] = {
            "matrix_5": cm5,
            "matrix_3": cm3,
            "labels_5": CLASSIFICATION_LABELS,
            "labels_3": DIRECTION_LABELS,
        }

        # Category Breakdown
        cat_metrics = {}
        for cat in CATEGORY_ORDER:
            c_vids = [vid for vid in evaluated_ids if unified_dict[vid]["category"] == cat]
            if not c_vids:
                continue
            c_gt = [unified_dict[vid]["ground_truth"] for vid in c_vids]
            c_pred = [preds[vid]["prediction"] for vid in c_vids]
            c_gt3 = [unified_dict[vid]["ground_truth_direction"] for vid in c_vids]
            c_pred3 = [get_direction(p) for p in c_pred]

            c_exact = sum(1 for g, p in zip(c_gt, c_pred) if g == p)
            c_dir = sum(1 for g, p in zip(c_gt3, c_pred3) if g == p)
            c_m = calculate_class_metrics(c_gt, c_pred, CLASSIFICATION_LABELS)

            c_cm = [[0] * 5 for _ in range(5)]
            for g, p in zip(c_gt, c_pred):
                if g in CLASSIFICATION_LABELS and p in CLASSIFICATION_LABELS:
                    c_cm[CLASSIFICATION_LABELS.index(g)][CLASSIFICATION_LABELS.index(p)] += 1

            cat_metrics[cat] = {
                "count": len(c_vids),
                "exact_correct": c_exact,
                "directional_correct": c_dir,
                "matrix_5": c_cm,
                "exact_accuracy": round(c_exact / len(c_vids) * 100, 2),
                "directional_accuracy": round(c_dir / len(c_vids) * 100, 2),
                "macro_f1": round(calculate_macro_f1(c_m) * 100, 2),
                "plp_f1": round((c_m["Pathogenic"]["f1"] + c_m["Likely Pathogenic"]["f1"]) / 2 * 100, 2),
                "vus_f1": round(c_m["Uncertain Significance"]["f1"] * 100, 2),
                "blb_f1": round((c_m["Benign"]["f1"] + c_m["Likely Benign"]["f1"]) / 2 * 100, 2),
            }
        models_categories[m_key] = cat_metrics

        # Criteria frequencies
        models_criteria[m_key] = {
            c: crit_counter.get(c, 0) for c in sorted(all_criteria_set)
        }

        # Safety samples
        models_safety[m_key] = {
            "false_pathogenic_count": type1_err_count,
            "false_benign_count": type2_err_count,
            "top_false_pathogenic": [
                {
                    "id": vid,
                    "gene": unified_dict[vid]["gene"],
                    "variant": unified_dict[vid]["variation"],
                    "disease": unified_dict[vid]["disease"],
                    "ground_truth": unified_dict[vid]["ground_truth"],
                    "predicted": preds[vid]["prediction"],
                    "criteria": preds[vid]["criteria"][:5],
                }
                for vid in false_pathogenic_ids[:10]
            ],
            "top_false_benign": [
                {
                    "id": vid,
                    "gene": unified_dict[vid]["gene"],
                    "variant": unified_dict[vid]["variation"],
                    "disease": unified_dict[vid]["disease"],
                    "ground_truth": unified_dict[vid]["ground_truth"],
                    "predicted": preds[vid]["prediction"],
                    "criteria": preds[vid]["criteria"][:5],
                }
                for vid in false_benign_ids[:10]
            ],
        }

    # -------------------------------------------------------------------------
    # PAIRWISE MODEL CONCORDANCE
    # -------------------------------------------------------------------------
    model_keys = [m["key"] for m in models_summary]
    concordance_matrix = {k1: {} for k1 in model_keys}

    for k1 in model_keys:
        for k2 in model_keys:
            if k1 == k2:
                concordance_matrix[k1][k2] = {"exact_pct": 100.0, "dir_pct": 100.0, "overlap": len(model_predictions[k1])}
                continue
            common = set(model_predictions[k1].keys()) & set(model_predictions[k2].keys())
            if not common:
                concordance_matrix[k1][k2] = {"exact_pct": 0.0, "dir_pct": 0.0, "overlap": 0}
                continue
            exact_agrees = sum(1 for vid in common if model_predictions[k1][vid]["prediction"] == model_predictions[k2][vid]["prediction"])
            dir_agrees = sum(1 for vid in common if get_direction(model_predictions[k1][vid]["prediction"]) == get_direction(model_predictions[k2][vid]["prediction"]))
            concordance_matrix[k1][k2] = {
                "exact_pct": round(exact_agrees / len(common) * 100, 1),
                "dir_pct": round(dir_agrees / len(common) * 100, 1),
                "overlap": len(common),
            }

    # -------------------------------------------------------------------------
    # CURATED REPRESENTATIVE VARIANTS FOR INTERACTIVE EXPLORER
    # -------------------------------------------------------------------------
    explorer_variants = []
    # Round-robin across categories so every category is represented
    by_category = defaultdict(list)
    for vid, u in unified_dict.items():
        by_category[u["category"]].append(vid)
    queues = [by_category[c] for c in CATEGORY_ORDER if by_category.get(c)]
    sample_vids = []
    while len(sample_vids) < 250 and any(queues):
        for q in queues:
            if q and len(sample_vids) < 250:
                sample_vids.append(q.pop(0))
    for vid in sample_vids:
        u = unified_dict[vid]
        preds_for_var = {}
        for m_key in model_keys:
            if vid in model_predictions[m_key]:
                preds_for_var[m_key] = model_predictions[m_key][vid]["prediction"]
            else:
                preds_for_var[m_key] = "Pending"

        explorer_variants.append({
            "id": vid,
            "gene": u["gene"],
            "variation": u["variation"],
            "disease": u["disease"],
            "category": u["category"],
            "expert_panel": u["expert_panel"],
            "ground_truth": u["ground_truth"],
            "ground_truth_direction": u["ground_truth_direction"],
            "ground_truth_criteria": u["criteria_met"][:5],
            "predictions": preds_for_var,
        })

    # -------------------------------------------------------------------------
    # LIVE RE-RUN BACKGROUND JOB MONITORING
    # -------------------------------------------------------------------------
    live_jobs = {}
    for job_name, pid_file, log_file, target_total in [
        ("Sonnet 5.5 Re-Run", "run_overnight_sonnet.pid", "run_overnight_sonnet_*.log", 5760),
        ("Opus 5.5 Re-Run", "run_overnight_opus.pid", "run_overnight_opus_*.log", 8387),
    ]:
        p_path = REPO_ROOT / pid_file
        pid = None
        status = "Inactive"
        if p_path.exists():
            try:
                pid = int(p_path.read_text().strip())
                status = "Running"
            except Exception:
                pass

        # Find latest log
        logs = sorted(glob.glob(str(REPO_ROOT / log_file)))
        latest_log = logs[-1] if logs else ""
        current_progress = 0
        latest_line = ""
        if latest_log and os.path.exists(latest_log):
            try:
                with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "Progress:" in line:
                            match = re.search(r"Progress:\s*(\d+)/(\d+)", line)
                            if match:
                                current_progress = int(match.group(1))
                                latest_line = line.strip()
            except Exception:
                pass

        live_jobs[job_name] = {
            "pid": pid,
            "status": status,
            "log_path": str(latest_log),
            "progress_count": current_progress,
            "target_total": target_total,
            "progress_pct": round(current_progress / target_total * 100, 1) if target_total else 0,
            "latest_log_snippet": latest_line,
        }

    # -------------------------------------------------------------------------
    # FINAL ASSEMBLED DASHBOARD PAYLOAD
    # -------------------------------------------------------------------------
    payload = {
        "metadata": {
            "title": "AIVA Variant Benchmark",
            "subtitle": "Anthropic Claude vs Frontiers & Classical Baselines on ClinGen Curated Variant Classification",
            "evaluation_date": datetime.now().strftime("%B %d, %Y"),
            "total_variants": total_cohort,
            "categories": CATEGORY_ORDER,
            "classification_labels": CLASSIFICATION_LABELS,
            "direction_labels": DIRECTION_LABELS,
            "excluded_models": excluded_models,
        },
        "models": models_summary,
        "confusion_matrices": models_confusion,
        "categories_data": models_categories,
        "criteria_data": models_criteria,
        "safety_data": models_safety,
        "concordance": concordance_matrix,
        "explorer_variants": explorer_variants,
        "live_jobs": live_jobs,
    }

    carry_over_archived_models(payload, excluded)

    out_file = REPO_ROOT / "dashboard" / "data" / "benchmark_data.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[{datetime.now().strftime('%T')}] Wrote dashboard data to {out_file}")
    print(f"Data file size: {out_file.stat().st_size / 1024:.1f} KB")

    return payload


def load_previous_dataset() -> dict:
    """Dataset embedded in the current dashboard/index.html, if any."""
    html_path = REPO_ROOT / "dashboard" / "index.html"
    if not html_path.exists():
        return {}
    html = html_path.read_text(encoding="utf-8")
    marker = "window.BENCHMARK_DATA = "
    start = html.find(marker)
    if start == -1:
        return {}
    try:
        data, _ = json.JSONDecoder().raw_decode(html, start + len(marker))
    except json.JSONDecodeError:
        return {}
    return data


def carry_over_archived_models(payload: dict, excluded: set[str]) -> None:
    """
    Keep models whose raw result files are not in this checkout (for example
    runs excluded by .gitignore) by copying their computed results from the
    previous build. They are flagged "archived" and lack variant-level
    comparisons against models that were added later.
    """
    previous = load_previous_dataset()
    current = {m["key"] for m in payload["models"]}
    for m in previous.get("models", []):
        listed = {x["key"] for x in payload["metadata"]["excluded_models"]}
        if m["key"] in excluded and m["key"] not in current and m["key"] not in listed:
            payload["metadata"]["excluded_models"].append({"key": m["key"], "name": m["name"]})
    archived = [m for m in previous.get("models", [])
                if m["key"] not in current and m["key"] not in excluded and m["key"] not in RETIRED_MODELS
                and not m.get("imported")
                and m["key"] in previous.get("confusion_matrices", {})]
    if not archived:
        return

    for m in archived:
        k = m["key"]
        color = MODEL_COLORS.get(k, m.get("color", FALLBACK_COLORS[0]))
        m = dict(m, archived=True, color=color, color_dark=MODEL_COLORS_DARK.get(k, color))
        payload["models"].append(m)
        payload["confusion_matrices"][k] = previous["confusion_matrices"][k]
        for section in ("categories_data", "criteria_data", "safety_data"):
            if k in previous.get(section, {}):
                payload[section][k] = previous[section][k]
        cats = payload["categories_data"].get(k, {})
        for r in cats.values():
            r.setdefault("exact_correct", round(r["exact_accuracy"] * r["count"] / 100))
            r.setdefault("directional_correct", round(r["directional_accuracy"] * r["count"] / 100))

        old_conc = previous.get("concordance", {}).get(k, {})
        payload["concordance"][k] = {o: v for o, v in old_conc.items() if o in payload["concordance"] or o == k}
        for o, v in old_conc.items():
            if o in payload["concordance"] and o != k:
                payload["concordance"][o][k] = v

        old_preds = {v["id"]: v["predictions"].get(k) for v in previous.get("explorer_variants", [])}
        for v in payload["explorer_variants"]:
            if old_preds.get(v["id"]):
                v["predictions"][k] = old_preds[v["id"]]
        print(f"  Carried over {m['name']} from the previous build (raw results not found).")


if __name__ == "__main__":
    build_dashboard_dataset()
