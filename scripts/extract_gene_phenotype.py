"""
Extract gene and phenotype information from benchmarking results.

Usage:
    python scripts/extract_gene_phenotype.py results/classifications_*.jsonl
    python scripts/extract_gene_phenotype.py Results_500_benchmarked/classifications_*.jsonl --output gene_phenotype_summary.tsv
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_jsonl(filepath: Path) -> list[dict]:
    """Load JSONL file."""
    results = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def extract_gene_phenotype_data(filepaths: list[Path]) -> dict:
    """
    Extract unique gene-phenotype-variant combinations from result files.
    
    Returns:
        Dict with variant_id as key, containing gene, disease, variant info
    """
    variants = {}
    
    for fp in filepaths:
        for r in load_jsonl(fp):
            vid = r.get("variant_id")
            if not vid:
                continue
                
            # Only add if not already present (avoid duplicates from multiple models)
            if vid not in variants:
                variants[vid] = {
                    "variant_id": vid,
                    "variant": r.get("variant", ""),
                    "gene": r.get("gene", "Unknown"),
                    "disease": r.get("disease", ""),
                    "expert_panel": r.get("expert_panel", ""),
                    "ground_truth": r.get("ground_truth", ""),
                    "ground_truth_criteria": ", ".join(r.get("ground_truth_criteria", []))
                }
    
    return variants


def generate_gene_summary(variants: dict) -> dict:
    """
    Generate summary statistics by gene.
    
    Returns:
        Dict with gene as key, containing counts and phenotypes
    """
    gene_data = defaultdict(lambda: {
        "count": 0,
        "phenotypes": set(),
        "expert_panels": set(),
        "classifications": defaultdict(int)
    })
    
    for v in variants.values():
        gene = v["gene"] or "Unknown"
        gene_data[gene]["count"] += 1
        
        if v["disease"]:
            gene_data[gene]["phenotypes"].add(v["disease"])
        if v["expert_panel"]:
            gene_data[gene]["expert_panels"].add(v["expert_panel"])
        if v["ground_truth"]:
            gene_data[gene]["classifications"][v["ground_truth"]] += 1
    
    # Convert sets to lists for serialization
    for gene in gene_data:
        gene_data[gene]["phenotypes"] = sorted(gene_data[gene]["phenotypes"])
        gene_data[gene]["expert_panels"] = sorted(gene_data[gene]["expert_panels"])
        gene_data[gene]["classifications"] = dict(gene_data[gene]["classifications"])
    
    return dict(gene_data)


def write_variant_tsv(variants: dict, output_path: Path):
    """Write per-variant data to TSV file."""
    fieldnames = [
        "variant_id", "variant", "gene", "disease", 
        "expert_panel", "ground_truth", "ground_truth_criteria"
    ]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        
        # Sort by gene, then by variant
        sorted_variants = sorted(variants.values(), key=lambda x: (x["gene"] or "ZZZ", x["variant"]))
        
        for v in sorted_variants:
            writer.writerow(v)
    
    print(f"Wrote {len(variants)} variants to {output_path}")


def write_gene_summary_tsv(gene_data: dict, output_path: Path):
    """Write gene summary to TSV file."""
    fieldnames = [
        "gene", "variant_count", "phenotypes", "expert_panels",
        "pathogenic", "likely_pathogenic", "vus", "likely_benign", "benign"
    ]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        
        # Sort by variant count descending
        sorted_genes = sorted(gene_data.items(), key=lambda x: -x[1]["count"])
        
        for gene, data in sorted_genes:
            row = {
                "gene": gene,
                "variant_count": data["count"],
                "phenotypes": "; ".join(data["phenotypes"]),
                "expert_panels": "; ".join(data["expert_panels"]),
                "pathogenic": data["classifications"].get("Pathogenic", 0),
                "likely_pathogenic": data["classifications"].get("Likely Pathogenic", 0),
                "vus": data["classifications"].get("Uncertain Significance", 0),
                "likely_benign": data["classifications"].get("Likely Benign", 0),
                "benign": data["classifications"].get("Benign", 0)
            }
            writer.writerow(row)
    
    print(f"Wrote {len(gene_data)} genes to {output_path}")


def print_summary(variants: dict, gene_data: dict):
    """Print summary to console."""
    print("\n" + "=" * 80)
    print("GENE AND PHENOTYPE SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal variants: {len(variants)}")
    print(f"Unique genes: {len(gene_data)}")
    
    # Top genes
    print("\n" + "-" * 80)
    print("TOP 15 GENES BY VARIANT COUNT")
    print("-" * 80)
    print(f"{'Gene':<20} {'Count':>8} {'Phenotypes':>12} {'Expert Panels':>15}")
    print("-" * 80)
    
    sorted_genes = sorted(gene_data.items(), key=lambda x: -x[1]["count"])[:15]
    for gene, data in sorted_genes:
        print(f"{gene:<20} {data['count']:>8} {len(data['phenotypes']):>12} {len(data['expert_panels']):>15}")
    
    # Classification distribution
    print("\n" + "-" * 80)
    print("CLASSIFICATION DISTRIBUTION")
    print("-" * 80)
    
    class_counts = defaultdict(int)
    for v in variants.values():
        if v["ground_truth"]:
            class_counts[v["ground_truth"]] += 1
    
    for cls in ["Pathogenic", "Likely Pathogenic", "Uncertain Significance", "Likely Benign", "Benign"]:
        count = class_counts.get(cls, 0)
        pct = 100 * count / len(variants) if variants else 0
        print(f"  {cls:<25} {count:>6} ({pct:>5.1f}%)")
    
    # Unique phenotypes
    all_phenotypes = set()
    for data in gene_data.values():
        all_phenotypes.update(data["phenotypes"])
    
    print(f"\nTotal unique phenotypes/diseases: {len(all_phenotypes)}")


def main():
    parser = argparse.ArgumentParser(description="Extract gene and phenotype data from benchmark results")
    parser.add_argument("files", nargs="+", help="Input JSONL result files (supports wildcards)")
    parser.add_argument("--output", "-o", default="gene_phenotype_variants.tsv",
                        help="Output TSV file for per-variant data (default: gene_phenotype_variants.tsv)")
    parser.add_argument("--gene-summary", "-g", default="gene_summary.tsv",
                        help="Output TSV file for gene summary (default: gene_summary.tsv)")
    parser.add_argument("--output-dir", "-d", help="Output directory (default: same as first input file)")
    
    args = parser.parse_args()
    
    # Expand file paths
    filepaths = []
    for pattern in args.files:
        p = Path(pattern)
        if p.exists():
            filepaths.append(p)
        else:
            # Try glob
            parent = p.parent if p.parent.exists() else Path(".")
            matches = list(parent.glob(p.name))
            filepaths.extend(matches)
    
    if not filepaths:
        print("Error: No input files found")
        sys.exit(1)
    
    # Filter to only classification files
    filepaths = [f for f in filepaths if f.name.startswith("classifications_") and f.suffix == ".jsonl"]
    
    if not filepaths:
        print("Error: No classification JSONL files found")
        sys.exit(1)
    
    print(f"Processing {len(filepaths)} file(s)...")
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = filepaths[0].parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract data
    variants = extract_gene_phenotype_data(filepaths)
    gene_data = generate_gene_summary(variants)
    
    # Print summary
    print_summary(variants, gene_data)
    
    # Write output files
    variant_output = output_dir / args.output
    gene_output = output_dir / args.gene_summary
    
    write_variant_tsv(variants, variant_output)
    write_gene_summary_tsv(gene_data, gene_output)
    
    print(f"\nDone! Files saved to {output_dir}")


if __name__ == "__main__":
    main()
