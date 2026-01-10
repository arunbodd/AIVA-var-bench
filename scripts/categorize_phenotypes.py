#!/usr/bin/env python3
"""
Categorize phenotypes/diseases into broader disease categories based on ClinGen Expert Panels.

Usage:
    python scripts/categorize_phenotypes.py Results_500_benchmarked/gene_phenotype_variants.tsv
    python scripts/categorize_phenotypes.py Results_500_benchmarked/gene_phenotype_variants.tsv --output-dir Results_500_benchmarked
"""

import argparse
import csv
import sys
from collections import defaultdict, Counter
from pathlib import Path

# =============================================================================
# ClinGen Expert Panel (VCEP) to Broader Disease Category Mapping
# Based on actual ClinGen VCEP classifications from eRepo data
# =============================================================================

VCEP_TO_CATEGORY = {
    # -------------------------------------------------------------------------
    # CANCER / CANCER PREDISPOSITION
    # -------------------------------------------------------------------------
    "Myeloid Malignancy VCEP": "Cancer Predisposition",
    "CDH1 VCEP": "Cancer Predisposition",  # Diffuse gastric & lobular breast cancer
    "PTEN VCEP": "Cancer Predisposition",  # PTEN hamartoma tumor syndrome
    "TP53 VCEP": "Cancer Predisposition",  # Li-Fraumeni syndrome
    "VHL VCEP": "Cancer Predisposition",  # von Hippel-Lindau disease
    "Hereditary Breast, Ovarian and Pancreatic Cancer VCEP": "Cancer Predisposition",
    "ENIGMA BRCA1 and BRCA2 VCEP": "Cancer Predisposition",
    "InSiGHT Hereditary Colorectal Cancer/Polyposis VCEP": "Cancer Predisposition",
    "DICER1 and miRNA-Processing Gene VCEP": "Cancer Predisposition",
    
    # -------------------------------------------------------------------------
    # METABOLIC DISORDERS
    # -------------------------------------------------------------------------
    "Monogenic Diabetes VCEP": "Metabolic Disorders",
    "Phenylketonuria VCEP": "Metabolic Disorders",
    "Familial Hypercholesterolemia VCEP": "Metabolic Disorders",
    "Lysosomal Diseases VCEP": "Metabolic Disorders",  # Includes GAA (Pompe disease)
    "Cerebral Creatine Deficiency Syndromes VCEP": "Metabolic Disorders",
    "ACADVL VCEP": "Metabolic Disorders",  # Fatty acid oxidation disorder
    "Mitochondrial Diseases VCEP": "Metabolic Disorders",
    
    # -------------------------------------------------------------------------
    # CARDIOVASCULAR DISORDERS
    # -------------------------------------------------------------------------
    "Cardiomyopathy VCEP": "Cardiovascular Disorders",
    "FBN1 VCEP": "Cardiovascular Disorders",  # Marfan syndrome
    "Pulmonary Hypertension VCEP": "Cardiovascular Disorders",
    
    # -------------------------------------------------------------------------
    # HEMATOLOGIC DISORDERS (non-cancer)
    # -------------------------------------------------------------------------
    "Platelet Disorders VCEP": "Hematologic Disorders",  # Glanzmann thrombasthenia
    "von Willebrand Disease  VCEP": "Hematologic Disorders",
    "Coagulation Factor Deficiency VCEP": "Hematologic Disorders",  # Hemophilia
    "Thrombosis VCEP": "Hematologic Disorders",
    
    # -------------------------------------------------------------------------
    # IMMUNODEFICIENCY DISORDERS
    # -------------------------------------------------------------------------
    "Severe Combined Immunodeficiency Disease  VCEP": "Immunodeficiency Disorders",
    
    # -------------------------------------------------------------------------
    # NEURODEVELOPMENTAL DISORDERS
    # -------------------------------------------------------------------------
    "Rett and Angelman-like Disorders VCEP": "Neurodevelopmental Disorders",
    
    # -------------------------------------------------------------------------
    # NEUROMUSCULAR DISORDERS
    # -------------------------------------------------------------------------
    "Malignant Hyperthermia Susceptibility VCEP": "Neuromuscular Disorders",
    "Congenital Myopathies VCEP": "Neuromuscular Disorders",
    "Limb Girdle Muscular Dystrophy VCEP": "Neuromuscular Disorders",
    
    # -------------------------------------------------------------------------
    # OPHTHALMOLOGIC DISORDERS
    # -------------------------------------------------------------------------
    "Glaucoma VCEP": "Ophthalmologic Disorders",
    "Leber Congenital Amaurosis/early onset Retinal Dystrophy VCEP": "Ophthalmologic Disorders",
    "X-linked Inherited Retinal Disease VCEP": "Ophthalmologic Disorders",
    "ABCA4 VCEP": "Ophthalmologic Disorders",  # Stargardt disease
    
    # -------------------------------------------------------------------------
    # HEARING DISORDERS
    # -------------------------------------------------------------------------
    "Hearing Loss VCEP": "Hearing Disorders",
    
    # -------------------------------------------------------------------------
    # DEVELOPMENTAL SYNDROMES / RASopathies
    # -------------------------------------------------------------------------
    "RASopathy VCEP": "RASopathies / Developmental Syndromes",
    "Brain Malformations VCEP": "RASopathies / Developmental Syndromes",
    
    # -------------------------------------------------------------------------
    # OTHER SPECIALIZED VCEPs
    # -------------------------------------------------------------------------
    "Hereditary Hemorrhagic Telangiectasia VCEP": "Vascular Disorders",
    "Epilepsy Sodium Channel VCEP": "Epilepsy / Neurological",
    "Potassium Channel Arrhythmia VCEP": "Cardiovascular Disorders",
    "Antibody Deficiencies VCEP": "Immunodeficiency Disorders",
}

# Define broader category groupings for summary
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
    "RASopathies / Developmental Syndromes",
    "Epilepsy / Neurological",
    "Vascular Disorders",
    "Other",
]

def get_category(expert_panel: str) -> str:
    """Map an Expert Panel (VCEP) to its broader disease category."""
    if not expert_panel or expert_panel == "N/A":
        return "Other"
    
    # Direct lookup
    category = VCEP_TO_CATEGORY.get(expert_panel.strip())
    if category:
        return category
    
    # Try case-insensitive match
    expert_panel_lower = expert_panel.lower().strip()
    for vcep, cat in VCEP_TO_CATEGORY.items():
        if vcep.lower() == expert_panel_lower:
            return cat
    
    return "Other"


def main():
    parser = argparse.ArgumentParser(description="Categorize phenotypes into broader disease groups based on ClinGen Expert Panels")
    parser.add_argument("input_file", type=Path, help="Input TSV file (gene_phenotype_variants.tsv)")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory")
    parser.add_argument("--output-file", type=str, default="phenotype_categories.tsv", help="Output filename")
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    output_dir = args.output_dir or args.input_file.parent
    output_path = output_dir / args.output_file
    summary_path = output_dir / "category_summary.tsv"
    
    # Read input data
    variants = []
    with open(args.input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            # Use expert_panel column for categorization
            expert_panel = row.get("expert_panel", "")
            row["disease_category"] = get_category(expert_panel)
            variants.append(row)
    
    # Count categories
    category_counts = Counter(v["disease_category"] for v in variants)
    disease_by_category = defaultdict(set)
    gene_by_category = defaultdict(set)
    vcep_by_category = defaultdict(set)
    classification_by_category = defaultdict(lambda: defaultdict(int))
    
    for v in variants:
        cat = v["disease_category"]
        disease_by_category[cat].add(v.get("disease", ""))
        gene_by_category[cat].add(v.get("gene", ""))
        vcep_by_category[cat].add(v.get("expert_panel", ""))
        gt = v.get("ground_truth", "")
        classification_by_category[cat][gt] += 1
    
    # Print summary
    print("\n" + "=" * 110)
    print("DISEASE CATEGORY SUMMARY (Based on ClinGen Expert Panels)")
    print("=" * 110)
    print(f"\nTotal variants: {len(variants)}")
    print(f"Total categories: {len(category_counts)}")
    
    print("\n" + "-" * 110)
    print(f"{'Category':<40} {'Variants':>10} {'VCEPs':>8} {'Genes':>8} {'P/LP':>8} {'VUS':>8} {'B/LB':>8}")
    print("-" * 110)
    
    # Sort by predefined order, then by count for any not in order
    def sort_key(cat):
        try:
            return (CATEGORY_ORDER.index(cat), -category_counts[cat])
        except ValueError:
            return (len(CATEGORY_ORDER), -category_counts[cat])
    
    for cat in sorted(category_counts.keys(), key=sort_key):
        count = category_counts[cat]
        n_vceps = len(vcep_by_category[cat])
        n_genes = len(gene_by_category[cat])
        
        # Aggregate classifications
        cls_counts = classification_by_category[cat]
        p_lp = cls_counts.get("Pathogenic", 0) + cls_counts.get("Likely Pathogenic", 0)
        vus = cls_counts.get("Uncertain Significance", 0)
        b_lb = cls_counts.get("Benign", 0) + cls_counts.get("Likely Benign", 0)
        
        print(f"{cat:<40} {count:>10} {n_vceps:>8} {n_genes:>8} {p_lp:>8} {vus:>8} {b_lb:>8}")
    
    # Print VCEPs per category
    print("\n" + "=" * 110)
    print("EXPERT PANELS (VCEPs) BY CATEGORY")
    print("=" * 110)
    
    for cat in sorted(category_counts.keys(), key=sort_key):
        vceps = sorted(vcep_by_category[cat])
        print(f"\n{cat} ({category_counts[cat]} variants):")
        for vcep in vceps:
            if vcep:
                # Count variants per VCEP
                vcep_count = sum(1 for v in variants if v.get("expert_panel") == vcep)
                print(f"  - {vcep} ({vcep_count} variants)")
    
    # Write output files
    # 1. Variants with category
    fieldnames = list(variants[0].keys())
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(variants)
    
    print(f"\nWrote {len(variants)} variants with categories to {output_path}")
    
    # 2. Category summary
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["category", "variant_count", "vcep_count", "gene_count",
                        "pathogenic", "likely_pathogenic", "vus", "likely_benign", "benign",
                        "expert_panels", "genes"])
        
        for cat in sorted(category_counts.keys(), key=sort_key):
            cls_counts = classification_by_category[cat]
            vceps = "; ".join(sorted(v for v in vcep_by_category[cat] if v))
            genes = "; ".join(sorted(gene_by_category[cat]))
            
            writer.writerow([
                cat,
                category_counts[cat],
                len(vcep_by_category[cat]),
                len(gene_by_category[cat]),
                cls_counts.get("Pathogenic", 0),
                cls_counts.get("Likely Pathogenic", 0),
                cls_counts.get("Uncertain Significance", 0),
                cls_counts.get("Likely Benign", 0),
                cls_counts.get("Benign", 0),
                vceps,
                genes
            ])
    
    print(f"Wrote category summary to {summary_path}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
