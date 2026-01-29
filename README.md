# AIVA Variant Classification Benchmark

Benchmark suite for evaluating AIVA's AI-powered variant classification against expert-curated classifications from the [ClinGen Evidence Repository (eRepo)](https://erepo.clinicalgenome.org/evrepo/).

## Key Results

AIVA (powered by Gemini 3 Pro) achieves **80.5% macro F1** on 8,387 expert-curated variants across 11 disease categories:

| Metric | Score |
|--------|-------|
| Overall Macro F1 | 80.5% |
| Pathogenic/Likely Pathogenic F1 | 87.4% |
| VUS F1 | 73.3% |
| Benign/Likely Benign F1 | 80.9% |

**AIVA outperforms BIAS-2015 and InterVar in 9 of 11 disease categories.**

See [BENCHMARK_FINDINGS.md](Results_Gemini_Pro_Analysis/BENCHMARK_FINDINGS.md) for detailed analysis.

## Overview

This tool measures how well AIVA's variant classification aligns with expert panel (VCEP) curations using ACMG/AMP guidelines. It supports two benchmarking workflows:

### Workflow A: Quick AIVA Model Comparison
Compare different LLM models within AIVA using a sample of eRepo variants.

### Workflow B: 4-Way Tool Comparison
Compare AIVA against InterVar and BIAS-2015 using pre-computed predictions from the [BIAS-2015 paper](https://github.com/bitscopic/BIAS-2015).

**Metrics calculated:**
- **Classification accuracy** (5-class and 3-class directional)
- **Per-class precision, recall, and F1 scores**
- **ACMG criteria agreement** (which evidence codes each tool identifies)
- **Confusion matrices** for error analysis

## Quick Start

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your AIVA_API_TOKEN

# Workflow A: Quick model comparison (5 min)
python scripts/parse_erepo.py --sample-size 50
python scripts/compare_models.py --models google/gemini-3-flash-preview --limit 10
python scripts/benchmark.py

# Workflow B: 4-way tool comparison (requires BIAS-2015 data)
python scripts/parse_bias_data.py
python scripts/compare_models.py --models google/gemini-3-flash-preview --input data/bias_unified.jsonl --limit 100
python scripts/compare_tools.py --aiva-results results/classifications_*.jsonl
```

## Setup

```bash
# Clone and enter directory
cd aiva-bench

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API access
cp .env.example .env
# Edit .env with your AIVA API token
```

## Configuration

Edit `config.py` or set environment variables:

| Setting | Default | Description |
|---------|---------|-------------|
| `AIVA_API_URL` | `http://localhost:8000` | AIVA API endpoint |
| `AIVA_API_TOKEN` | - | AIVA API token for authentication |
| `DEFAULT_MODEL` | `google/gemini-3-flash-preview` | LLM model for classification |
| `DEFAULT_ASSEMBLY` | `GRCh38` | Genome assembly |
| `CONCURRENCY_LIMIT` | `5` | Max concurrent API requests |

## Project Structure

```
aiva-var-bench/
├── config.py                    # Configuration settings
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── data/
│   ├── erepo-tabbed.tsv         # Raw eRepo download
│   ├── bias_unified.jsonl       # Unified BIAS-2015 dataset (7,617 variants)
│   └── erepo_bias_intervar_merged.jsonl  # Merged dataset with all predictions
├── Results_Gemini_Pro_Analysis/ # Main benchmark results
│   ├── BENCHMARK_FINDINGS.md    # Comprehensive benchmark report
│   ├── classifications_*.jsonl  # Raw classification results
│   ├── metrics_by_category.tsv  # Performance metrics by disease category
│   ├── category_summary.tsv     # Dataset composition summary
│   └── figures/                 # Publication-quality visualizations
│       └── png/
│           ├── figure11_scorecard.png
│           ├── figure_sankey_flow_matplotlib.png
│           ├── figure_combined_summary.png
│           └── variant_distribution_by_category.png
└── scripts/
    ├── parse_erepo.py           # Parse & sample eRepo data
    ├── parse_bias_data.py       # Parse BIAS-2015 data
    ├── compare_models.py        # Compare multiple AIVA models
    ├── compare_tools.py         # 4-way tool comparison
    ├── benchmark.py             # Calculate detailed metrics
    ├── benchmark_analysis.py    # End-to-end analysis pipeline
    └── generate_results.py      # Metrics calculation & figure generation
```

## Usage

### Workflow A: Quick AIVA Model Comparison

Use this to compare different LLM models within AIVA on a sample of eRepo variants.

#### Step 1: Parse eRepo Data

Download the eRepo TSV from [ClinGen](https://erepo.clinicalgenome.org/evrepo/) and parse it:

```bash
# Parse and create stratified sample (default: 200 variants)
python scripts/parse_erepo.py

# Custom sample size
python scripts/parse_erepo.py --sample-size 500
```

**Output:**
- `data/parsed_variants.jsonl` - All parsed variants
- `data/sample_200.jsonl` - Stratified sample

#### Step 2: Run Classification & Compare Models

```bash
# Compare multiple models on the sample
python scripts/compare_models.py --models google/gemini-3-flash-preview openai/gpt-4o

# Limit variants for quick testing
python scripts/compare_models.py --models google/gemini-3-flash-preview --limit 20
```

# New Feature: Parallel Execution
You can use the `--parallel` flag to run multiple models concurrently, significantly speeding up the benchmarking process.

```bash
python scripts/compare_models.py \
  --models openai/gpt-5.2 google/gemini-3-pro-preview anthropic/claude-opus-4-5-20251101 \
  --input data/bias_unified.jsonl \
  --parallel \
  --concurrency 5
```

When using `--parallel`:
- Progress bars are replaced with periodic status updates to avoid console conflicts.
- Each model runs in its own concurrent task.

**New Feature: Custom Output Directory**
You can now specify where to save results using `--output-dir`.

```bash
# Step 1: Download BIAS-2015 data (see below)

# Step 2: Parse and unify data
python scripts/parse_bias_data.py

# Step 3: Run AIVA classification
python scripts/compare_models.py \
  --models openai/gpt-5.2 google/gemini-3-pro-preview \
  --input data/sample_200.jsonl \
  --output-dir results/my_experiment_v1
```

### Full Analysis Pipeline

For comprehensive benchmarking with figures and scorecards:

```bash
# Use most recent results
python scripts/benchmark.py

# Specify input file
python scripts/benchmark.py --input results/classifications_*.jsonl
```

---

### Workflow B: 4-Way Tool Comparison (AIVA vs InterVar vs BIAS-2015)

Use this to compare AIVA against InterVar and BIAS-2015 on 7,617 variants from the BIAS-2015 paper.

#### Step 1: Download BIAS-2015 Supplementary Data

Download pre-computed predictions from the BIAS-2015 paper:

**Option A: Direct download (no AWS CLI required)**

Download: https://bias-2015.s3.amazonaws.com/bias_v2.0.0_supplementary_files.zip

**Option B: AWS CLI**

```bash
aws s3 cp s3://bias-2015/bias_v2.0.0_supplementary_files.zip /tmp/
```

Then extract and copy files:
```bash
unzip /tmp/bias_v2.0.0_supplementary_files.zip -d /tmp/bias_supp/
cp /tmp/bias_supp/bias_v2.0.0_supplementary_files/*.{tabbed,intervar,tsv,vcf} data/bias_2015/
```

## Script Reference

| Script | Purpose |
|--------|---------|
| `parse_erepo.py` | Parse ClinGen eRepo TSV, create stratified sample |
| `parse_bias_data.py` | Parse BIAS-2015 files, create unified dataset |
| `compare_models.py` | Run AIVA with multiple models, compare results |
| `compare_tools.py` | Compare AIVA vs InterVar vs BIAS-2015 |
| `benchmark.py` | Calculate detailed metrics |
| `benchmark_analysis.py` | End-to-end analysis pipeline with figures |
| `generate_results.py` | Metrics calculation and figure generation |

## Metrics Explained

### Classification Accuracy

| Metric | Description |
|--------|-------------|
| **Exact Match (5-class)** | % where AIVA matches expert classification exactly |
| **Directional (3-class)** | % correct when collapsed to Pathogenic/VUS/Benign |

### Per-Class Metrics

For each of the 5 ACMG classifications:
- **Precision**: When AIVA predicts this class, how often is it correct?
- **Recall**: Of all variants in this class, how many does AIVA identify?
- **F1**: Harmonic mean of precision and recall

## Rate Limiting

The classify script handles rate limits automatically:
- Exponential backoff on errors
- Special handling for 429 (rate limit) with longer delays
- Configurable concurrency to avoid overwhelming the API

If you encounter rate limits, reduce concurrency:
```bash
python scripts/compare_models.py --concurrency 1
```

## License

MIT License - see LICENSE file for details.

## Contact

Arun Boddapati, MHSPL Research Team
