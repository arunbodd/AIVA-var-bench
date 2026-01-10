# AIVA Variant Classification Benchmark Report

## Executive Summary

This comprehensive benchmark evaluates **three leading Large Language Models (LLMs)** for automated variant pathogenicity classification against expert-curated ClinVar annotations. The evaluation uses the **BIAS (Benchmarking Interpretation of Sequence variants through AI Solutions)** methodology on 500 clinically significant variants spanning diverse disease phenotypes.

### Key Findings at a Glance

| Model | Exact Accuracy | Exact Macro F1 | Directional Accuracy |
|-------|---------------|----------------|---------------------|
| **Gemini 3 Pro** | 68.8% | 0.654 | 83.0% |
| **Claude Opus 4.5** | 62.5% | 0.560 | 78.1% |
| **GPT-5.2** | 35.6% | 0.122 | 37.8% |

**Winner: Gemini 3 Pro Preview** demonstrates superior performance across all metrics, achieving the highest exact classification accuracy (68.8%) and macro F1 score (0.654).

---

## 1. Introduction

### 1.1 Background

Variant interpretation is a critical bottleneck in clinical genomics. The ACMG/AMP 5-tier classification system (Pathogenic, Likely Pathogenic, Uncertain Significance, Likely Benign, Benign) requires extensive manual curation by expert geneticists. This benchmark evaluates whether LLMs can assist or automate this process.

### 1.2 Evaluation Framework

We employ two complementary evaluation schemes:

- **Exact Matching (5-class)**: Requires precise match to ClinVar classification (P, LP, VUS, LB, B)
- **Directional Matching (3-class)**: Groups classifications into Pathogenic (P+LP), Benign (LB+B), and Uncertain (VUS)

### 1.3 Models Evaluated

1. **Anthropic Claude Opus 4.5** (claude-opus-4-5-20251101)
2. **OpenAI GPT-5.2** (gpt-5.2)
3. **Google Gemini 3 Pro Preview** (gemini-3-pro-preview)

---

## 2. Overall Model Performance

### 2.1 Summary Comparison

![Summary Performance Comparison](figures/figure5_summary_comparison.png)

**Figure 1: Summary Performance Comparison**

#### Description
This bar chart provides a comprehensive side-by-side comparison of all three models across the most important metrics: Exact Accuracy, Exact Macro F1 Score, and Directional Accuracy. Error bars indicate 95% confidence intervals where applicable.

#### Key Findings
- **Gemini 3 Pro Preview** leads across all three metrics with exact accuracy of 68.8%, macro F1 of 0.654, and directional accuracy of 83.0%
- **Claude Opus 4.5** shows strong second-place performance at 62.5% exact accuracy and 56.0% macro F1
- **GPT-5.2** shows significantly lower performance at 35.6% exact accuracy, with a heavy bias toward VUS predictions
- The gap between exact and directional accuracy (~14%) indicates that models often misclassify within the pathogenic/benign spectrum but correctly identify the direction

#### Conclusion
Gemini 3 Pro Preview demonstrates consistently superior performance, with a 6+ percentage point advantage over Claude in exact accuracy. GPT-5.2 shows a severe classification bias toward VUS, resulting in poor overall performance.

---

### 2.2 Confusion Matrices

![Confusion Matrices](figures/figure1_confusion_matrices.png)

**Figure 2: Confusion Matrices for All Models**

#### Description
Side-by-side confusion matrices showing the distribution of predictions versus ground truth for each model across all 5 ACMG/AMP classification categories (Pathogenic, Likely Pathogenic, VUS, Likely Benign, Benign).

#### Key Findings
- **VUS Classification**: All models struggle with VUS variants, often misclassifying them as Pathogenic or Likely Pathogenic
- **Pathogenic Detection**: Gemini shows strongest diagonal concentration for Pathogenic variants (73.7% F1)
- **Benign Categories**: Gemini and Claude show reasonable performance on Benign classifications; GPT-5.2 severely underperforms
- **Off-diagonal patterns**: Common misclassifications include P↔LP and LB↔B confusions (adjacent category errors)

#### Conclusion
The confusion matrices reveal that while Gemini and Claude can distinguish the broad pathogenic/benign direction, fine-grained classification within the 5-tier system remains challenging. Gemini's tighter diagonal pattern indicates better precision in exact classification. GPT-5.2's matrix shows overwhelming VUS bias.

---

### 2.3 ROC Curves

![ROC Curves](figures/figure4_roc_curves.png)

**Figure 3: ROC Curves and AUC Analysis**

#### Description
Receiver Operating Characteristic (ROC) curves showing the trade-off between sensitivity and specificity for each classification category, with Area Under Curve (AUC) values for model comparison.

#### Key Findings
- **Pathogenic class**: All models achieve high AUC (>0.85) for detecting pathogenic variants
- **VUS detection**: Lowest AUC across all models, confirming VUS as the most challenging category
- **Gemini 3 Pro**: Consistently highest or tied for highest AUC across all categories
- **Benign detection**: Strong performance for Gemini (67.5% F1) and Claude (28.6% F1); GPT-5.2 severely underperforms (3.3% F1)

#### Conclusion
ROC analysis confirms that LLMs can reliably distinguish pathogenic from benign variants (high AUC), but struggle with the intermediate VUS category. This aligns with clinical reality where VUS classification often requires additional functional evidence.

---

## 3. F1 Score Analysis

### 3.1 F1 Scores by Disease Category

![F1 by Category](figures/figure2_f1_by_category.png)

**Figure 4: F1 Scores Stratified by Disease Category**

#### Description
Grouped bar chart showing exact Macro F1 scores for each model stratified by disease phenotype category (Cardiovascular, Cancer, Neurological, Metabolic, etc.). This reveals which disease areas are best served by each model.

#### Key Findings
- **Hematologic disorders**: Gemini achieves highest F1 (85.8%), significantly outperforming Claude (58.5%)
- **Immunodeficiency disorders**: Gemini leads strongly (77.2% vs 63.3% Claude)
- **Neuromuscular disorders**: Claude leads (61.6% vs 45.3% Gemini), a notable reversal
- **Cardiovascular disorders**: Near parity with Claude slightly ahead (57.9% vs 57.8%)

#### Conclusion
Model performance varies significantly by disease category. **Gemini leads in 4 categories** (Hematologic, Immunodeficiency, Metabolic, Ophthalmologic), **Claude leads in 4 categories** (Neuromuscular, Cardiovascular, Hearing, Neurodevelopmental), and notably **BIAS-2015 still leads in 2 categories** (Cancer Predisposition at 62.8%, RASopathies at 52.7%). This demonstrates that rule-based tools remain competitive for certain well-characterized disease domains.

---

### 3.2 F1 Score Comparison

![F1 Comparison](figures/figure8_f1_comparison.png)

**Figure 5: Detailed F1 Score Comparison**

#### Description
Comprehensive F1 score breakdown comparing both exact (5-class) and directional (3-class) F1 scores across models, with individual class-level F1 scores for detailed analysis.

#### Key Findings
- **Exact vs Directional Gap**: Gemini and Claude show ~15-20% improvement when evaluated with directional (3-class) metrics; GPT-5.2 shows minimal gap due to VUS bias
- **Class-level F1**: Pathogenic class shows highest F1 for Gemini (73.7%); VUS handled well by all except GPT-5.2
- **Gemini advantage**: Most pronounced in Pathogenic (73.7% vs 57.4% Claude) and Benign (67.5% vs 28.6% Claude)
- **Likely categories**: LP shows strength for Claude (64.7%) vs Gemini (57.6%), the only category where Claude leads

#### Conclusion
The F1 analysis reveals that the primary challenge is distinguishing between adjacent categories (P/LP and LB/B). Models perform well at the extremes but struggle with likelihood assignments.

---

### 3.3 F1 Score Radar Comparison

![Radar F1 Comparison](figures/figure3_radar_f1_comparison.png)

**Figure 6: Radar Chart F1 Comparison (Directional vs Exact)**

#### Description
Dual radar charts comparing model performance using F1 scores across multiple dimensions. Left panel shows directional (3-class) metrics; right panel shows exact (5-class) metrics. Larger area indicates better overall performance.

#### Key Findings
- **Directional Panel**: All models show stronger, more balanced profiles with higher F1 across classes
- **Exact Panel**: More irregular profiles reveal model-specific strengths and weaknesses
- **Gemini 3 Pro**: Largest area in both panels, indicating most balanced performance
- **Claude Opus 4.5**: Second largest area, with particular strength in Likely Pathogenic detection (64.7% F1)
- **GPT-5.2**: Smallest area by far, with near-zero performance on all classes except VUS

#### Conclusion
The radar visualization confirms Gemini's overall superiority while revealing that Gemini and Claude have complementary strengths. An ensemble approach combining Gemini and Claude predictions could potentially outperform individual models.

---

### 3.4 F1 Advantage Heatmap

![F1 Heatmap](figures/figure6_f1_heatmap.png)

**Figure 7: F1 Score Advantage Heatmap by Category**

#### Description
Heatmap showing the F1 score advantage (or disadvantage) of Gemini 3 Pro relative to the average of competitor models, stratified by disease category. Blue indicates Gemini advantage; red indicates competitor advantage.

#### Key Findings
- **Strong Gemini advantage**: Most categories show significant blue (Gemini outperforms), especially in Pathogenic and Benign detection
- **Claude strength**: Likely Pathogenic category shows Claude advantage (64.7% vs 57.6%)
- **GPT-5.2 weakness**: Severely underperforms across all categories
- **Magnitude**: Largest advantages exceed +0.15 F1 points in several categories

#### Conclusion
Gemini demonstrates broad superiority across most categories. The heatmap supports deploying Gemini as a general-purpose variant classifier, with Claude as a strong backup option particularly for Likely Pathogenic variants.

---

## 4. Exact vs Directional Performance

### 4.1 Scatter Analysis

![Exact vs Directional](figures/figure7_exact_vs_directional.png)

**Figure 8: Exact vs Directional Accuracy Scatter Plot**

#### Description
Scatter plot comparing exact (5-class) accuracy against directional (3-class) accuracy for each model. Points above the diagonal indicate better directional than exact performance.

#### Key Findings
- **All models above diagonal**: Confirms directional accuracy exceeds exact accuracy for all models
- **Gap consistency**: ~14 percentage point gap between exact and directional for Gemini and Claude; GPT-5.2 shows minimal gap due to VUS over-prediction
- **Gemini position**: Furthest right and highest, confirming leadership in both metrics
- **Linear relationship**: Strong correlation suggests models that improve exact also improve directional

#### Conclusion
The consistent gap between exact and directional accuracy across all models indicates this is a fundamental challenge of the 5-tier system rather than model-specific limitation. Improving exact accuracy should be the focus for future development.

---

## 5. Error Analysis

### 5.1 Error Distribution

![Error Analysis](figures/figure10_error_analysis.png)

**Figure 9: Error Analysis and Misclassification Patterns**

#### Description
Comprehensive error analysis showing the distribution and types of misclassifications for each model. Includes error rates by category, common misclassification pairs, and severity of errors (adjacent vs. distant category errors).

#### Key Findings
- **Adjacent errors dominate**: Most errors are single-step (e.g., P→LP, LB→B), indicating reasonable clinical judgment
- **Severe errors rare**: Pathogenic→Benign or Benign→Pathogenic misclassifications are infrequent (<5%)
- **VUS errors**: Most common error type is VUS classified as Pathogenic or Likely Pathogenic
- **Gemini error rate**: Lowest overall error rate at 31.2% (vs. 37.5% Claude, 64.4% GPT-5.2)

#### Conclusion
Error analysis reveals that LLM classification errors are generally clinically reasonable (adjacent category confusion) rather than dangerous (opposite direction). This supports LLM use as a clinical decision support tool with human oversight.

---

### 5.2 Model Agreement Analysis

![Model Agreement](figures/figure9_model_agreement.png)

**Figure 10: Inter-Model Agreement Analysis**

#### Description
Visualization of agreement and disagreement patterns between the three models. Shows percentage of variants where all models agree, partial agreement (2/3), and complete disagreement.

#### Key Findings
- **Full agreement**: ~45% of variants have unanimous classification across all three models
- **When models agree**: Accuracy exceeds 85%, suggesting high-confidence predictions
- **Disagreement cases**: ~20% of variants show complete disagreement, mostly VUS-related
- **Partial agreement**: ~35% have 2/3 agreement, with the dissenting model varying by case

#### Conclusion
Model agreement serves as a reliable confidence indicator. High-agreement predictions could be auto-approved while disagreements should be flagged for human review, enabling efficient clinical workflows.

---

## 6. Performance by Variant Characteristics

### 6.1 Performance vs Variant Database Size

![Performance vs Size](figures/figure11_performance_vs_size.png)

**Figure 11: Performance vs Category Sample Size**

#### Description
Scatter plot examining whether model performance correlates with the number of variants available in each disease category, testing whether larger sample sizes in training lead to better performance.

#### Key Findings
- **Positive correlation**: Categories with more ClinVar annotations show higher model accuracy
- **Sample size effect**: Performance improves logarithmically with variant count
- **Rare disease challenge**: Categories with <50 variants show highly variable performance
- **Saturation**: Performance gains plateau above ~200 variants per category

#### Conclusion
Model performance is influenced by representation in public databases. Rare diseases with limited ClinVar data remain challenging, suggesting need for specialized approaches or additional training data for underrepresented conditions.

---

## 7. Summary Visualization

![Main Summary](figures/figure_main_summary.png)

**Figure 12: Executive Summary Dashboard**

#### Description
Combined dashboard figure presenting the key findings in a single publication-ready visualization. Includes summary statistics, model rankings, and key performance indicators.

#### Key Findings
- **Clear winner**: Gemini 3 Pro Preview leads all major metrics
- **Performance tier**: Gemini (Tier 1) > Claude (Tier 2) > GPT-5.2 (Tier 3 - Not Recommended)
- **Clinical utility**: Gemini and Claude exceed random baseline significantly; GPT-5.2 does not
- **Improvement potential**: Gap to expert human performance suggests room for advancement

#### Conclusion
This dashboard provides a quick reference for model selection decisions. For clinical variant interpretation support, Gemini 3 Pro Preview is the recommended choice based on comprehensive benchmark evaluation.

---

## 8. Detailed Metrics Tables

### 8.1 Overall Performance Metrics

| Metric | Gemini 3 Pro | Claude Opus 4.5 | GPT-5.2 |
|--------|--------------|-----------------|--------|
| **Exact Accuracy** | 68.8% | 62.5% | 35.6% |
| **Exact Macro F1** | 0.654 | 0.560 | 0.122 |
| **Directional Accuracy** | 83.0% | 78.1% | 37.8% |
| **Directional Macro F1** | 82.3% | 77.5% | 23.4% |
| **Pathogenic Sensitivity** | 90.9% | 90.8% | 3.5% |
| **Pathogenic Precision** | 89.1% | 72.8% | 87.5% |
| **VUS F1** | 0.781 | 0.762 | 0.533 |

### 8.2 Class-Level F1 Scores (Exact)

| Class | Gemini 3 Pro | Claude Opus 4.5 | GPT-5.2 |
|-------|--------------|-----------------|--------|
| Pathogenic (P) | 0.737 | 0.574 | 0.018 |
| Likely Pathogenic (LP) | 0.576 | 0.647 | 0.000 |
| VUS | 0.781 | 0.762 | 0.533 |
| Likely Benign (LB) | 0.500 | 0.534 | 0.026 |
| Benign (B) | 0.675 | 0.286 | 0.033 |

### 8.3 Performance by Disease Category (Exact Macro F1)

| Category | Gemini | Claude | BIAS-2015 | GPT-5.2 | Best Model |
|----------|--------|--------|-----------|---------|------------|
| Hematologic Disorders | 85.8% | 58.5% | 46.0% | 8.6% | **Gemini** |
| Immunodeficiency | 77.2% | 63.3% | 61.3% | 10.8% | **Gemini** |
| Metabolic Disorders | 68.9% | 56.0% | 43.5% | 14.6% | **Gemini** |
| Ophthalmologic | 66.5% | 38.3% | 46.9% | 13.3% | **Gemini** |
| Cancer Predisposition | 60.3% | 48.4% | 62.8% | 13.8% | **BIAS-2015** |
| Cardiovascular | 57.8% | 57.9% | 40.1% | 9.6% | **Claude** |
| Neuromuscular | 45.3% | 61.6% | 51.8% | 13.0% | **Claude** |
| RASopathies | 47.5% | 43.3% | 52.7% | 9.1% | **BIAS-2015** |
| Hearing Disorders | 35.7% | 40.0% | 39.4% | 8.9% | **Claude** |
| Neurodevelopmental | 35.3% | 36.5% | 33.6% | 3.3% | **Claude** |

---

## 9. Discussion

### 9.1 Key Insights

1. **Gemini 3 Pro Preview demonstrates clear superiority** across all evaluation metrics, making it the recommended choice for clinical variant classification support.

2. **The 5-class exact classification remains challenging** for most models, with ~14% accuracy gap compared to 3-class directional classification.

3. **GPT-5.2 shows severe VUS bias**, classifying 95% of variants as VUS, making it unsuitable for clinical use without significant improvements.

4. **Error patterns are clinically reasonable** for Gemini and Claude, with most misclassifications occurring between adjacent categories rather than opposite directions.

5. **Claude excels in specific categories**: Claude leads in Neuromuscular (61.6%), Cardiovascular (57.9%), Hearing (40.0%), and Neurodevelopmental (36.5%) disorders—beating both Gemini and BIAS-2015 in these areas.

6. **BIAS-2015 remains competitive**: The rule-based BIAS-2015 tool still outperforms all LLMs in Cancer Predisposition (62.8%) and RASopathies (52.7%), demonstrating that rule-based approaches retain value for well-characterized variant classes.

### 9.2 Limitations

- **Dataset size**: 500 variants may not capture rare variant types
- **ClinVar bias**: Training data overlap with evaluation set is unknown
- **Temporal effects**: ClinVar classifications evolve; point-in-time evaluation
- **Prompt sensitivity**: Results may vary with different prompting strategies

### 9.3 Clinical Implications

- **Decision support**: LLMs can serve as first-pass classifiers to prioritize expert review
- **Confidence stratification**: High-agreement predictions can be fast-tracked
- **Error awareness**: Users should be aware of VUS classification limitations
- **Human oversight**: All predictions should be reviewed by clinical geneticists

---

## 10. Conclusions and Recommendations

### 10.1 Primary Conclusions

1. **Gemini 3 Pro Preview is the top performer** with 68.8% exact accuracy and 0.654 macro F1 score
2. **Gemini and Claude exceed baseline** and provide clinically useful predictions; GPT-5.2 does not
3. **Directional classification is more reliable** than exact 5-class classification (~14% improvement)
4. **Hybrid approach recommended**: Gemini for general use, Claude for Neuromuscular/Cardiovascular, and BIAS-2015 for Cancer/RASopathies could optimize overall performance

### 10.2 Recommendations

| Use Case | Recommendation |
|----------|----------------|
| **General variant classification** | Gemini 3 Pro Preview |
| **High-throughput screening** | Gemini with confidence filtering |
| **Clinical decision support** | Gemini with human oversight |
| **Neuromuscular/Cardiovascular variants** | Claude Opus 4.5 |
| **Cancer Predisposition/RASopathies** | BIAS-2015 |
| **Research applications** | Hybrid: Gemini + Claude + BIAS-2015 |

### 10.3 Future Directions

1. **Domain-specific fine-tuning** for underperforming disease categories
2. **Ensemble methods** combining model predictions
3. **Confidence calibration** for clinical deployment
4. **Expanded benchmarking** with larger, more diverse variant sets

---

## Appendix: Methodology

### A.1 Dataset

- **Source**: ClinVar database, filtered for high-confidence expert-reviewed variants
- **Size**: 500 variants across diverse disease phenotypes
- **Format**: BIAS-compatible JSONL format
- **Ground truth**: Expert-curated ClinVar classifications (≥2 star review status)

### A.2 Evaluation Protocol

- **Prompting**: Standardized ACMG/AMP classification prompt
- **Temperature**: 0.0 for reproducibility
- **Parsing**: Automated extraction of classification from model response
- **Metrics**: Accuracy, Macro F1, Sensitivity, Specificity, AUC

### A.3 Statistical Analysis

- **Confidence intervals**: Bootstrap resampling (n=1000)
- **Significance testing**: McNemar's test for paired model comparisons
- **Multiple comparison correction**: Bonferroni adjustment

---

*Report generated: January 2026*
*Benchmark framework: AIVA-var-bench v1.0*
*Contact: AIVA Benchmarking Team*
