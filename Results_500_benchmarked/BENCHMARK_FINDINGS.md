# AIVA Benchmarking Results: 500-Variant Analysis

**Date:** January 10, 2026  
**Dataset:** 500 expert-reviewed variants from ClinGen Expert Panels (eRepo)  
**Ground Truth:** ClinGen Expert Panel classifications

---

## Executive Summary

AIVA with Gemini 3 Pro achieves **68.8% exact accuracy**, outperforming both BIAS-2015 (61.2%) and InterVar (48.2%) in variant classification. AIVA models also demonstrate superior sensitivity for detecting pathogenic variants (90.9%) compared to existing tools.

---

## 1. Overall Accuracy Comparison

| Tool | Exact Accuracy (5-class) | Directional Accuracy (3-class) | Macro F1 | Dir F1 |
|------|--------------------------|-------------------------------|----------|--------|
| **AIVA (Gemini 3 Pro)** | **68.8%** | 83.0% | **65.4%** | 82.3% |
| AIVA (Claude Opus 4.5) | 62.5% | 78.1% | 56.0% | 77.5% |
| BIAS-2015 | 61.2% | **83.6%** | 53.0% | 83.8% |
| InterVar | 48.2% | 63.6% | 40.2% | 64.0% |
| AIVA (GPT 5.2) | 35.6% | 37.8% | 12.2% | 23.4% |

### Key Observations

- **AIVA (Gemini 3 Pro)** achieves the highest exact 5-class accuracy (+7.6% over BIAS-2015, +20.6% over InterVar)
- **BIAS-2015** has slightly better directional accuracy (83.6% vs 83.0%), but lower exact accuracy
- **InterVar** significantly underperforms all other tools
- **GPT 5.2** has a critical bias toward VUS classification (95.6% of predictions), making it unsuitable for clinical use

---

## 2. BIAS-2015 Style Metrics (Sensitivity, Specificity, Precision, F1)

### Pathogenic/Likely Pathogenic (P/LP) Detection

| Tool | Sensitivity | Specificity | Precision | F1 |
|------|-------------|-------------|-----------|-----|
| **AIVA (Gemini 3 Pro)** | **90.9%** | **92.7%** | **89.1%** | **90.0%** |
| AIVA (Claude Opus 4.5) | 90.8% | 77.2% | 72.8% | 80.8% |
| BIAS-2015 | 87.4% | 91.1% | 86.5% | 86.9% |
| InterVar | 59.1% | 91.1% | 81.3% | 68.4% |
| AIVA (GPT 5.2) | 3.5% | 99.7% | 87.5% | 6.8% |

### Benign/Likely Benign (B/LB) Detection

| Tool | Sensitivity | Specificity | Precision | F1 |
|------|-------------|-------------|-----------|-----|
| **BIAS-2015** | **84.0%** | 96.6% | 88.5% | **86.2%** |
| AIVA (Gemini 3 Pro) | 69.8% | **97.6%** | **90.2%** | 78.7% |
| AIVA (Claude Opus 4.5) | 67.0% | 96.7% | 86.8% | 75.6% |
| InterVar | 53.8% | 95.0% | 77.1% | 63.4% |
| AIVA (GPT 5.2) | 5.9% | 96.9% | 36.8% | 10.1% |

### Variant of Uncertain Significance (VUS) Detection

| Tool | Sensitivity | Specificity | Precision | F1 |
|------|-------------|-------------|-----------|-----|
| AIVA (Gemini 3 Pro) | 83.1% | 83.0% | 73.8% | 78.2% |
| BIAS-2015 | 79.2% | **86.8%** | **77.5%** | **78.4%** |
| AIVA (Claude Opus 4.5) | 71.5% | 91.1% | 81.5% | 76.2% |
| InterVar | 74.9% | 57.1% | 50.2% | 60.1% |
| AIVA (GPT 5.2) | **95.6%** | 6.0% | 37.0% | 53.4% |

---

## 3. Per-Class F1 Scores (5-class Breakdown)

| Class | InterVar | BIAS-2015 | Claude Opus | Gemini 3 Pro | GPT 5.2 |
|-------|----------|-----------|-------------|--------------|---------|
| Pathogenic | 45.9% | 64.1% | 57.4% | **73.7%** | 1.8% |
| Likely Pathogenic | 33.5% | 16.5% | **64.7%** | 57.6% | 0.0% |
| Uncertain Significance | 60.1% | **78.4%** | 76.2% | 78.1% | 53.3% |
| Likely Benign | 44.8% | 35.4% | **53.4%** | 50.0% | 2.6% |
| Benign | 17.0% | **70.6%** | 28.6% | 67.5% | 3.3% |
| **Macro F1** | 40.2% | 53.0% | 56.0% | **65.4%** | 12.2% |

### Observations

- **Gemini 3 Pro** excels at Pathogenic classification (73.7% F1)
- **Claude Opus** is best at Likely Pathogenic (64.7% F1)
- **BIAS-2015** performs best on Benign (70.6% F1) and VUS (78.4% F1)
- **InterVar** struggles across all categories, especially Benign (17.0% F1)

---

## 4. Confusion Matrices (3-class Directional)

### AIVA (Gemini 3 Pro Preview)
```
                  Predicted ->
  Actual ↓        Pathogenic    VUS    Benign
  Pathogenic            180     18         0
  VUS                    22    152         9
  Benign                  0     36        83
```

### BIAS-2015
```
                  Predicted ->
  Actual ↓        Pathogenic    VUS    Benign
  Pathogenic            173     23         2
  VUS                    27    145        11
  Benign                  0     19       100
```

### InterVar
```
                  Predicted ->
  Actual ↓        Pathogenic    VUS    Benign
  Pathogenic            117     81         0
  VUS                    27    137        19
  Benign                  0     55        64
```

---

## 5. Dataset Characteristics

### Classification Distribution (Ground Truth)
| Classification | Count | Percentage |
|---------------|-------|------------|
| Pathogenic | 105 | 21.0% |
| Likely Pathogenic | 93 | 18.6% |
| Uncertain Significance | 183 | 36.6% |
| Likely Benign | 65 | 13.0% |
| Benign | 54 | 10.8% |

### Gene Distribution
- **Total unique genes:** 77
- **Total unique phenotypes/diseases:** 69
- **Most represented gene:** RUNX1 (78 variants, 15.6%)

### Top 10 Genes by Variant Count
| Gene | Count | Primary Phenotype |
|------|-------|-------------------|
| RUNX1 | 78 | Hereditary thrombocytopenia and hematologic cancer |
| PAH | 32 | Phenylketonuria |
| LDLR | 29 | Familial hypercholesterolemia |
| GCK | 23 | Monogenic diabetes |
| HNF1A | 21 | Monogenic diabetes |
| RYR1 | 21 | RYR1-related myopathy / Malignant hyperthermia |
| MYOC | 18 | Primary open angle glaucoma |
| CDH1 | 17 | Diffuse gastric and lobular breast cancer |
| GAA | 15 | Glycogen storage disease II |
| ITGA2B | 14 | Glanzmann thrombasthenia |

---

## 6. Key Findings

### Strengths of AIVA

1. **Superior pathogenic detection**: AIVA (Gemini) achieves 90.9% sensitivity for P/LP variants, exceeding BIAS-2015 (87.4%) and InterVar (59.1%)

2. **Better granular classification**: AIVA models distinguish between Pathogenic and Likely Pathogenic more accurately (Macro F1: 65.4% vs 53.0% for BIAS-2015)

3. **High specificity**: AIVA (Gemini) maintains 92.7% specificity for pathogenic variants, reducing false positives

4. **Consistent performance**: AIVA (Gemini and Claude) perform well across most classification categories

### Areas for Improvement

1. **Benign variant detection**: BIAS-2015 outperforms AIVA in B/LB sensitivity (84.0% vs 69.8%)

2. **Model selection matters**: GPT 5.2 shows severe VUS bias and is not suitable for clinical classification

3. **Gene-specific performance**: Further analysis needed to assess performance variations across different genes

---

## 7. Clinical Implications

| Metric | Winner | Clinical Relevance |
|--------|--------|-------------------|
| P/LP Sensitivity | AIVA (Gemini) | Fewer missed pathogenic variants |
| P/LP Specificity | AIVA (Gemini) | Fewer false pathogenic calls |
| B/LB Sensitivity | BIAS-2015 | Better at confirming benign variants |
| Overall Accuracy | AIVA (Gemini) | Most reliable for routine classification |

### Recommendation

For clinical variant classification workflows:
- **Primary tool**: AIVA with Gemini 3 Pro (best overall accuracy and pathogenic detection)
- **Secondary validation**: BIAS-2015 (especially for benign variant confirmation)
- **Avoid**: GPT 5.2 (severe classification bias)

---

## 8. Methodology

- **Benchmark dataset**: 500 variants randomly sampled from ClinGen Expert Panel reviews
- **Ground truth**: ClinGen Expert Panel classifications with ACMG/AMP criteria
- **Comparison tools**: 
  - AIVA (3 LLM backends: Gemini 3 Pro, Claude Opus 4.5, GPT 5.2)
  - BIAS-2015 (rule-based classifier)
  - InterVar (automated ACMG/AMP interpreter)
- **Metrics**: Exact accuracy, directional accuracy, sensitivity, specificity, precision, F1 score

---

## 9. Files Generated

| File | Description |
|------|-------------|
| `tool_comparison_detailed.txt` | Full comparison report with all metrics |
| `tool_comparison_detailed.jsonl` | Per-variant predictions from all tools |
| `gene_phenotype_variants.tsv` | Variant-level gene and phenotype data |
| `gene_summary.tsv` | Gene-level summary with classification distribution |
| `comparison_*.json` | Model comparison results |

---

*Report generated from AIVA-var-bench benchmarking suite*
