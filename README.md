# AIVA Variant Classification Benchmark

Benchmark suite for evaluating AIVA's AI-powered variant classification against expert-curated classifications from the [ClinGen Evidence Repository (eRepo)](https://erepo.clinicalgenome.org/evrepo/).

## Overview

This tool measures how well AIVA's variant classification aligns with expert panel (VCEP) curations using ACMG/AMP guidelines. It calculates:

- **Classification accuracy** (5-class and 3-class directional)
- **Per-class precision, recall, and F1 scores**
- **ACMG criteria agreement** (which evidence codes AIVA identifies correctly)
- **Confusion matrices** for error analysis

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
| `CONCURRENCY_LIMIT` | `5` | Max concurrent API requests (respects AIVA rate limit) |

## Usage

### 1. Parse eRepo Data

Download the eRepo TSV from [ClinGen](https://erepo.clinicalgenome.org/evrepo/) and parse it:

```bash
# Parse and create stratified sample (default: 200 variants)
python scripts/parse_erepo.py

# Custom sample size
python scripts/parse_erepo.py --sample-size 500

# Parse all without sampling
python scripts/parse_erepo.py --full
```

**Output:**
- `data/parsed_variants.jsonl` - All parsed variants
- `data/sample_200.jsonl` - Stratified sample

### 2. Run Classification

```bash
# Use default sample and model
python scripts/classify.py

# Specify model
python scripts/classify.py --model openai/gpt-4o

# Limit variants (for testing)
python scripts/classify.py --limit 10

# Adjust concurrency
python scripts/classify.py --concurrency 2
```

**Output:** `results/classifications_YYYYMMDD_HHMMSS.jsonl`

### 3. Calculate Metrics

```bash
# Use most recent results
python scripts/benchmark.py

# Specify input file
python scripts/benchmark.py --input results/classifications_20241229_123456.jsonl
```

**Output:** `results/metrics_YYYYMMDD_HHMMSS.json`

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

### Criteria Analysis

| Metric | Description |
|--------|-------------|
| **Avg Jaccard (normalized)** | Overlap of ACMG criteria (after normalizing modifiers like `_Supporting`) |
| **Direction Agreement** | % where AIVA's evidence leans the same direction (pathogenic vs benign) |
| **Per-Criterion P/R/F1** | How well AIVA identifies each specific criterion (PM2, PP3, etc.) |

### Evidence Direction

Criteria are grouped by evidence direction:
- **Pathogenic**: PVS1, PS1-4, PM1-6, PP1-5
- **Benign**: BA1, BS1-4, BP1-7

## Example Output

```
======================================================================
AIVA VARIANT CLASSIFICATION BENCHMARK RESULTS
======================================================================

Dataset: 200 variants
  Successful: 195 | Errors: 5 (2.5%)
  Compared: 195

============================== ACCURACY ==============================
  EXACT MATCH (5-class):     72.31%  (141/195)
  DIRECTIONAL (3-class):     89.74%  (175/195)

============================== CRITERIA ANALYSIS =====================
  Avg Jaccard (normalized): 0.312
  Evidence Direction Agreement: 85.6%

  Aggregate by Evidence Type:
    Pathogenic (PVS/PS/PM/PP): P=0.542 R=0.478 F1=0.508
    Benign (BA/BS/BP):         P=0.234 R=0.189 F1=0.209

  Per-Criterion Metrics (top 15 by support):
  Criterion  Type     Prec Recall     F1   TP   FP   FN Supp
  --------------------------------------------------------------
  PM2        PATH    0.892  0.943  0.917  150   18    9  159
  PP3        PATH    0.654  0.567  0.607   72   38   55  127
  ...
```

## Project Structure

```
aiva-bench/
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
├── data/
│   ├── erepo-tabbed.tsv  # Raw eRepo download
│   ├── parsed_variants.jsonl
│   └── sample_200.jsonl
├── results/
│   ├── classifications_*.jsonl
│   └── metrics_*.json
└── scripts/
    ├── parse_erepo.py    # Parse & sample eRepo data
    ├── classify.py       # Call AIVA API
    └── benchmark.py      # Calculate metrics
```

## Rate Limiting

The classify script handles rate limits automatically:
- Exponential backoff on errors
- Special handling for 429 (rate limit) with longer delays
- Configurable concurrency to avoid overwhelming the API

If you encounter rate limits, reduce concurrency:
```bash
python scripts/classify.py --concurrency 1
```
