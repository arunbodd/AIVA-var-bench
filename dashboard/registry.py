"""
Model registry for the benchmark dashboard (dashboard/models.tsv).

One row per model; adding a model to the dashboard is one line here plus its
results file. Columns (tab-separated):

    key         stable identifier, used in links and colours
    name        display name
    provider    Anthropic, OpenAI, Google, Rule-based or Other
    method      how the calls were produced, e.g. "AIVA agent"
    path        results file relative to the repo root; for the baselines,
                data:bias_classification or data:intervar_classification
    format      jsonl (AIVA output), json_array (Claude Code output),
                auto (by file extension) or unified (baseline field)
    color       optional hex colour; empty picks the provider's next colour
    color_dark  optional lighter colour for the dark theme
    status      active, or removed to hide the model
"""

from pathlib import Path

REGISTRY_FILE = Path(__file__).resolve().parent / "models.tsv"
COLUMNS = ["key", "name", "provider", "method", "path", "format", "color", "color_dark", "status"]
PROVIDERS = ["Anthropic", "OpenAI", "Google", "Rule-based", "Other"]

# Colours handed out, in order, to models whose row leaves `color` empty.
PROVIDER_COLORS = {
    "Anthropic": ["#eb6834", "#6250d6", "#1baf7a", "#a8461c", "#a097ee", "#0f7a55"],
    "OpenAI": ["#eda100", "#8a6d00", "#c98500", "#5f4b00"],
    "Google": ["#184f95", "#d55181", "#4f86d0", "#9c2f6b"],
    "Rule-based": ["#0097a7", "#5c4033", "#4b6584"],
    "Other": ["#008300", "#e34948", "#0d366b", "#8c5a2b"],
}


def read_registry(path: Path = REGISTRY_FILE) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t") + [""] * len(COLUMNS)
        row = dict(zip(COLUMNS, (p.strip() for p in parts[: len(COLUMNS)])))
        row["status"] = row["status"] or "active"
        row["provider"] = row["provider"] if row["provider"] in PROVIDERS else "Other"
        rows.append(row)
    return rows


def write_registry(rows: list[dict], path: Path = REGISTRY_FILE) -> None:
    header = "# " + "\t".join(COLUMNS) + "\n"
    body = "".join("\t".join(str(r.get(c, "")).replace("\t", " ") for c in COLUMNS) + "\n" for r in rows)
    path.write_text(header + body, encoding="utf-8")


def set_status(key: str, status: str) -> bool:
    rows = read_registry()
    found = False
    for r in rows:
        if r["key"] == key:
            r["status"] = status
            found = True
    if found:
        write_registry(rows)
    return found


def upsert(row: dict) -> None:
    rows = [r for r in read_registry() if r["key"] != row["key"]]
    rows.append({c: row.get(c, "") for c in COLUMNS})
    write_registry(rows)


def assign_colors(rows: list[dict]) -> None:
    """Fill empty colours from each provider's list, skipping colours in use."""
    used = {r["color"].lower() for r in rows if r["color"]}
    for r in rows:
        if r["color"]:
            continue
        palette = PROVIDER_COLORS.get(r["provider"], PROVIDER_COLORS["Other"])
        choice = next((c for c in palette if c.lower() not in used), None)
        if choice is None:
            choice = next((c for p in PROVIDER_COLORS.values() for c in p if c.lower() not in used), palette[0])
        r["color"] = choice
        used.add(choice.lower())
