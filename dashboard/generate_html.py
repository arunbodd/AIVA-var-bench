#!/usr/bin/env python3
"""
Generates the standalone benchmark dashboard (dashboard/index.html).

Reads dashboard/data/benchmark_data.json (written by build_data.py). If that
file is absent, the dataset already embedded in the current index.html is
reused, so the page can be restyled without re-running every model.

The ground-truth label for every cohort variant is also embedded so that
imported result files are scored against the full cohort in the browser.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from config import CLASSIFICATION_LABELS
from scripts.metrics import normalize_classification

DATA_FILE = REPO_ROOT / "dashboard" / "data" / "benchmark_data.json"
UNIFIED_FILE = REPO_ROOT / "data" / "erepo_bias_intervar_merged.jsonl"
HTML_OUT = REPO_ROOT / "dashboard" / "index.html"
TEMPLATE_FILE = REPO_ROOT / "dashboard" / "template.html"

DATA_MARKER = "window.BENCHMARK_DATA = "


def load_benchmark_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    if HTML_OUT.exists():
        html = HTML_OUT.read_text(encoding="utf-8")
        start = html.find(DATA_MARKER)
        if start != -1:
            start += len(DATA_MARKER)
            data, _ = json.JSONDecoder().raw_decode(html, start)
            print(f"{DATA_FILE} not found; reusing dataset embedded in {HTML_OUT.name}")
            return data
    sys.exit(f"No dataset found. Run dashboard/build_data.py first (expected {DATA_FILE}).")


def load_ground_truth_index() -> dict:
    """Map variant id -> index into CLASSIFICATION_LABELS."""
    index = {}
    if not UNIFIED_FILE.exists():
        return index
    with open(UNIFIED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            label = normalize_classification(item.get("classification", ""))
            if label in CLASSIFICATION_LABELS:
                index[item["id"]] = CLASSIFICATION_LABELS.index(label)
    return index


def to_script_json(obj) -> str:
    # Escape "</" so embedded strings can never close the <script> element.
    return json.dumps(obj, separators=(",", ":")).replace("</", "<\\/")


def main():
    data = load_benchmark_data()
    data["ground_truth_index"] = load_ground_truth_index()

    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    html = template.replace("__BENCHMARK_DATA__", to_script_json(data))

    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Generated standalone dashboard HTML at: {HTML_OUT}")
    print(f"HTML size: {HTML_OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
