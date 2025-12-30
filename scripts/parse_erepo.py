"""
Parse ClinGen eRepo TSV and create stratified samples for benchmarking.

Usage:
    python scripts/parse_erepo.py                    # Parse all, create default sample
    python scripts/parse_erepo.py --sample-size 500  # Create sample of 500
    python scripts/parse_erepo.py --full             # Parse all without sampling
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, RANDOM_SEED, DEFAULT_SAMPLE_SIZE, CLASSIFICATION_LABELS


@dataclass
class ERepoVariant:
    """Parsed variant from eRepo TSV."""
    id: str                          # UUID
    variation: str                   # Primary HGVS notation
    clinvar_id: str
    allele_registry_id: str
    hgvs_expressions: list[str]      # All HGVS expressions
    gene_symbol: str
    disease: str
    mondo_id: str
    mode_of_inheritance: str
    classification: str              # Ground truth (Assertion)
    criteria_met: list[str]
    criteria_not_met: list[str]
    summary: str
    pubmed_articles: list[str]
    expert_panel: str
    guideline_url: str
    approval_date: str
    published_date: str
    evidence_repo_link: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_list_field(value: str, delimiter: str = ",") -> list[str]:
    """Parse comma-separated field into list."""
    if not value or not value.strip():
        return []
    return [x.strip() for x in value.split(delimiter) if x.strip()]


def parse_erepo_tsv(filepath: Path) -> list[ERepoVariant]:
    """Parse eRepo TSV file and return list of variants."""
    variants = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)  # Skip header

        for row_num, row in enumerate(reader, start=2):
            if len(row) < 20:
                print(f"Warning: Row {row_num} has insufficient columns, skipping")
                continue

            # Skip retracted entries
            if row[17].lower() == "true":
                continue

            # Skip if no valid variant identifier
            if not row[0] and not row[3]:
                continue

            variant = ERepoVariant(
                id=row[19] if len(row) > 19 else f"row_{row_num}",
                variation=row[0],
                clinvar_id=row[1],
                allele_registry_id=row[2],
                hgvs_expressions=parse_list_field(row[3]),
                gene_symbol=row[4],
                disease=row[5],
                mondo_id=row[6],
                mode_of_inheritance=row[7],
                classification=row[8],
                criteria_met=parse_list_field(row[9]),
                criteria_not_met=parse_list_field(row[10]),
                summary=row[11],
                pubmed_articles=parse_list_field(row[12]),
                expert_panel=row[13],
                guideline_url=row[14],
                approval_date=row[15],
                published_date=row[16],
                evidence_repo_link=row[18]
            )
            variants.append(variant)

    return variants


def create_stratified_sample(
    variants: list[ERepoVariant],
    n: int,
    seed: int = RANDOM_SEED
) -> list[ERepoVariant]:
    """
    Create stratified sample maintaining class distribution.

    Args:
        variants: List of all variants
        n: Target sample size
        seed: Random seed for reproducibility

    Returns:
        Stratified sample of variants
    """
    random.seed(seed)

    # Group by classification
    by_class: dict[str, list[ERepoVariant]] = {}
    for v in variants:
        cls = v.classification
        if cls not in by_class:
            by_class[cls] = []
        by_class[cls].append(v)

    # Calculate proportional samples
    total = len(variants)
    sampled = []
    samples_per_class = {}

    for cls, cls_variants in by_class.items():
        proportion = len(cls_variants) / total
        n_sample = max(1, int(n * proportion))  # At least 1 per class
        n_sample = min(n_sample, len(cls_variants))  # Don't exceed available
        samples_per_class[cls] = n_sample

        random.shuffle(cls_variants)
        sampled.extend(cls_variants[:n_sample])

    # If we're short, add more from largest classes
    remaining = n - len(sampled)
    if remaining > 0:
        for cls in sorted(by_class.keys(), key=lambda k: len(by_class[k]), reverse=True):
            available = [v for v in by_class[cls] if v not in sampled]
            to_add = min(remaining, len(available))
            sampled.extend(available[:to_add])
            remaining -= to_add
            if remaining <= 0:
                break

    random.shuffle(sampled)
    return sampled[:n]


def save_jsonl(variants: list[ERepoVariant], filepath: Path):
    """Save variants to JSONL file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for v in variants:
            f.write(json.dumps(v.to_dict()) + "\n")
    print(f"Saved {len(variants)} variants to {filepath}")


def print_distribution(variants: list[ERepoVariant], label: str = ""):
    """Print classification distribution."""
    dist = Counter(v.classification for v in variants)
    total = len(variants)

    print(f"\n{label} Distribution ({total} total):")
    print("-" * 50)
    for cls in CLASSIFICATION_LABELS:
        count = dist.get(cls, 0)
        pct = 100 * count / total if total > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {cls:25} {count:5} ({pct:5.1f}%) {bar}")

    # Print any unexpected classifications
    unexpected = set(dist.keys()) - set(CLASSIFICATION_LABELS)
    if unexpected:
        print("\n  Unexpected classifications:")
        for cls in unexpected:
            print(f"    {cls}: {dist[cls]}")


def main():
    parser = argparse.ArgumentParser(description="Parse eRepo TSV and create samples")
    parser.add_argument("--input", default=str(DATA_DIR / "erepo-tabbed.tsv"),
                        help="Input TSV file path")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE,
                        help="Number of variants in sample")
    parser.add_argument("--full", action="store_true",
                        help="Save all variants without sampling")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED,
                        help="Random seed for sampling")

    args = parser.parse_args()

    # Parse TSV
    print(f"Parsing {args.input}...")
    variants = parse_erepo_tsv(Path(args.input))
    print(f"Parsed {len(variants)} variants (excluding retracted)")

    print_distribution(variants, "Full Dataset")

    # Save all parsed variants
    all_output = DATA_DIR / "parsed_variants.jsonl"
    save_jsonl(variants, all_output)

    if not args.full:
        # Create and save stratified sample
        sample = create_stratified_sample(variants, args.sample_size, args.seed)
        print_distribution(sample, f"Stratified Sample (n={len(sample)})")

        sample_output = DATA_DIR / f"sample_{len(sample)}.jsonl"
        save_jsonl(sample, sample_output)

        print(f"\nCreated sample file: {sample_output}")

    print("\nDone!")


if __name__ == "__main__":
    main()
