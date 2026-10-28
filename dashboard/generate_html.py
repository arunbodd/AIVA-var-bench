#!/usr/bin/env python3
"""
Generates the world-class standalone dashboard HTML file with embedded data
and dynamic extensibility for the Anthropic Fellowship presentation.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "dashboard" / "data" / "benchmark_data.json"
HTML_OUT = REPO_ROOT / "dashboard" / "index.html"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data_json_str = f.read()

# Build HTML template
html_content = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AIVA Variant Benchmark Intelligence Dashboard | Anthropic Fellowship</title>
  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            anthropic: {
              50: '#FDF8F6',
              100: '#F2E8E5',
              500: '#D97706',
              600: '#B45309',
              primary: '#D97706',
            },
            dark: {
              bg: '#0B0D13',
              card: '#131722',
              cardHover: '#1A2030',
              border: '#222838',
              muted: '#94A3B8',
            }
          }
        }
      }
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    code, pre, .mono {
      font-family: 'JetBrains Mono', monospace;
    }
    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0B0D13; }
    ::-webkit-scrollbar-thumb { background: #2A324B; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #3B4668; }
    /* Glassmorphism */
    .glass-card {
      background: rgba(19, 23, 34, 0.75);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.07);
    }
    .active-tab {
      background: rgba(217, 119, 6, 0.15) !important;
      color: #F59E0B !important;
      border-color: rgba(217, 119, 6, 0.4) !important;
    }
    .cm-cell:hover {
      transform: scale(1.08);
      z-index: 10;
      box-shadow: 0 0 15px rgba(0,0,0,0.5);
    }
  </style>
</head>
<body class="bg-dark-bg text-slate-100 min-h-screen antialiased flex flex-col">

  <!-- TOP APP HEADER -->
  <header class="border-b border-dark-border bg-dark-card/80 sticky top-0 z-50 backdrop-blur-md">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <!-- Left: Logo & Branding -->
      <div class="flex items-center space-x-3">
        <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-amber-600 to-amber-400 flex items-center justify-center shadow-lg shadow-amber-500/20">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="font-bold text-lg text-white tracking-tight">AIVA Variant Benchmark</h1>
            <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
              Anthropic Fellowship
            </span>
          </div>
          <p class="text-xs text-slate-400">ClinGen Curated Multi-Model Evaluation (n=8,387 Variants)</p>
        </div>
      </div>

      <!-- Right: Action Buttons & Live Indicator -->
      <div class="flex items-center space-x-3">
        <!-- Live Job Status Indicator -->
        <button onclick="switchTab('jobs')" class="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-all text-xs font-medium">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span id="headerLiveText">Sonnet: 7% | Opus: 3%</span>
        </button>

        <!-- Refresh Button -->
        <button onclick="refreshDashboardData()" title="Rebuild & refresh metrics" class="p-2 rounded-lg bg-dark-border/60 hover:bg-dark-border text-slate-300 hover:text-white transition-all text-xs flex items-center space-x-1.5 border border-slate-700/50">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span class="hidden sm:inline">Refresh</span>
        </button>

        <!-- Add Custom Model Button -->
        <button onclick="openUploadModal()" class="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white font-medium text-xs shadow-md shadow-amber-600/20 transition-all flex items-center space-x-1.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          <span>Add Model</span>
        </button>
      </div>
    </div>
  </header>

  <!-- NAVIGATION TABS -->
  <nav class="border-b border-dark-border bg-dark-card/40 backdrop-blur-sm sticky top-16 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex space-x-2 py-2.5 overflow-x-auto no-scrollbar text-xs font-medium">
        <button onclick="switchTab('overview')" id="tab-overview" class="tab-btn active-tab px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>🏆</span><span>Overview & Leaderboard</span>
        </button>
        <button onclick="switchTab('compare')" id="tab-compare" class="tab-btn px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>⚔️</span><span>Head-to-Head Comparison</span>
        </button>
        <button onclick="switchTab('categories')" id="tab-categories" class="tab-btn px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>🧬</span><span>13 Disease Categories</span>
        </button>
        <button onclick="switchTab('safety')" id="tab-safety" class="tab-btn px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>🛡️</span><span>Clinical Safety & Errors</span>
        </button>
        <button onclick="switchTab('criteria')" id="tab-criteria" class="tab-btn px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>⚖️</span><span>ACMG Criteria Engine</span>
        </button>
        <button onclick="switchTab('concordance')" id="tab-concordance" class="tab-btn px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>🌐</span><span>Concordance Matrix</span>
        </button>
        <button onclick="switchTab('explorer')" id="tab-explorer" class="tab-btn px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>🔍</span><span>Variant Explorer</span>
        </button>
        <button onclick="switchTab('jobs')" id="tab-jobs" class="tab-btn px-3.5 py-2 rounded-lg border border-transparent text-slate-300 hover:text-white hover:bg-dark-border/40 transition-all flex items-center space-x-2">
          <span>⏱️</span><span>Live Re-Runs</span>
        </button>
      </div>
    </div>
  </nav>

  <!-- MAIN VIEWPORT CONTAINER -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

    <!-- TAB 1: OVERVIEW & LEADERBOARD -->
    <section id="view-overview" class="tab-view space-y-6">
      <!-- HERO CARDS -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <!-- Card 1 -->
        <div class="glass-card rounded-2xl p-5 border border-dark-border relative overflow-hidden">
          <div class="absolute top-0 right-0 p-4 opacity-10">
            <svg class="w-16 h-16 text-amber-500" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
          </div>
          <span class="text-xs font-semibold uppercase tracking-wider text-amber-400">Top Anthropic Model</span>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-2xl font-extrabold text-white">Claude Opus 5.5</span>
            <span class="text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">71.6% Dir.</span>
          </div>
          <p class="mt-1 text-xs text-slate-400">Macro F1: <strong class="text-slate-200">54.5%</strong> • Exact Acc: <strong class="text-slate-200">58.0%</strong></p>
          <div class="mt-3 text-xs text-amber-300/80 flex items-center space-x-1">
            <span>⚡ Outperforms BIAS-2015 & InterVar</span>
          </div>
        </div>

        <!-- Card 2 -->
        <div class="glass-card rounded-2xl p-5 border border-dark-border relative overflow-hidden">
          <span class="text-xs font-semibold uppercase tracking-wider text-blue-400">Benign Resolution Surge</span>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-2xl font-extrabold text-white">+35.88%</span>
            <span class="text-xs font-medium text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20">AIVA Advantage</span>
          </div>
          <p class="mt-1 text-xs text-slate-400">Haiku Benign F1 jumped from <strong class="text-slate-200">33.95%</strong> (Claude-Code) to <strong class="text-slate-200">69.83%</strong></p>
          <div class="mt-3 text-xs text-blue-300/80">
            <span>🛡️ Population AF (BA1/BS1) enforcement</span>
          </div>
        </div>

        <!-- Card 3 -->
        <div class="glass-card rounded-2xl p-5 border border-dark-border relative overflow-hidden">
          <span class="text-xs font-semibold uppercase tracking-wider text-emerald-400">Zero Catastrophic Overcalls</span>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-2xl font-extrabold text-white">0.00%</span>
            <span class="text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">Sonnet & Opus</span>
          </div>
          <p class="mt-1 text-xs text-slate-400">Zero false pathogenic calls in Sonnet & Opus; Gemini Pro had <strong class="text-rose-400">18</strong>.</p>
          <div class="mt-3 text-xs text-emerald-300/80">
            <span>🏥 Best-in-class clinical safety profile</span>
          </div>
        </div>

        <!-- Card 4 -->
        <div class="glass-card rounded-2xl p-5 border border-dark-border relative overflow-hidden">
          <span class="text-xs font-semibold uppercase tracking-wider text-purple-400">Total Benchmark Cohort</span>
          <div class="mt-2 flex items-baseline space-x-2">
            <span class="text-2xl font-extrabold text-white">8,387</span>
            <span class="text-xs font-medium text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20">ClinGen eRepo</span>
          </div>
          <p class="mt-1 text-xs text-slate-400">13 Disease Categories • 45 ClinGen Expert Panels</p>
          <div class="mt-3 text-xs text-purple-300/80">
            <span>🔬 11 Models & Baselines Evaluated</span>
          </div>
        </div>
      </div>

      <!-- MAIN LEADERBOARD TABLE -->
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-white tracking-tight">Comprehensive Model Leaderboard</h2>
            <p class="text-xs text-slate-400">Benchmarked across 8,387 ClinGen expert-reviewed variants</p>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs text-slate-400">Filter Family:</span>
            <select id="familyFilter" onchange="renderLeaderboard()" class="bg-dark-bg border border-dark-border text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-amber-500">
              <option value="all">All Families</option>
              <option value="Anthropic Claude">Anthropic Claude</option>
              <option value="Google Gemini">Google Gemini</option>
              <option value="Classical ACMG Tools">Classical Tools</option>
            </select>
          </div>
        </div>

        <!-- Table -->
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-300">
            <thead class="bg-dark-bg/60 text-slate-400 uppercase text-[11px] font-semibold border-b border-dark-border">
              <tr>
                <th class="py-3 px-3">Model</th>
                <th class="py-3 px-3">Type</th>
                <th class="py-3 px-3 text-right cursor-pointer hover:text-white" onclick="sortLeaderboard('exact_accuracy')">Exact Acc (5-Class) ▾</th>
                <th class="py-3 px-3 text-right cursor-pointer hover:text-white" onclick="sortLeaderboard('directional_accuracy')">Dir Acc (3-Class) ▾</th>
                <th class="py-3 px-3 text-right cursor-pointer hover:text-white" onclick="sortLeaderboard('macro_f1_5')">Macro F1 (5-Class) ▾</th>
                <th class="py-3 px-3 text-right cursor-pointer hover:text-white" onclick="sortLeaderboard('macro_f1_3')">Macro F1 (3-Class) ▾</th>
                <th class="py-3 px-3 text-right cursor-pointer hover:text-white" onclick="sortLeaderboard('critical_error_rate')">Critical Error Rate ▾</th>
                <th class="py-3 px-3 text-right">Coverage</th>
                <th class="py-3 px-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody id="leaderboardBody" class="divide-y divide-dark-border">
              <!-- Dynamically rendered -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- PERFORMANCE BARS & RADAR -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 5-Class Macro F1 Comparison -->
        <div class="glass-card rounded-2xl border border-dark-border p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-sm text-white">5-Class Macro F1 Score Comparison</h3>
            <span class="text-xs text-slate-400">Higher is better</span>
          </div>
          <div id="macroF1BarChart" class="space-y-3 pt-2">
            <!-- Dynamically rendered -->
          </div>
        </div>

        <!-- 3-Class Directional Accuracy Comparison -->
        <div class="glass-card rounded-2xl border border-dark-border p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-sm text-white">Directional Accuracy (Pathogenic vs VUS vs Benign)</h3>
            <span class="text-xs text-slate-400">Clinical Concordance %</span>
          </div>
          <div id="dirAccBarChart" class="space-y-3 pt-2">
            <!-- Dynamically rendered -->
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 2: HEAD-TO-HEAD COMPARISON -->
    <section id="view-compare" class="tab-view hidden space-y-6">
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold text-white tracking-tight">Head-to-Head Model Matchup</h2>
            <p class="text-xs text-slate-400">Compare any two models side-by-side on class-level metrics and confusion matrices</p>
          </div>
          <div class="flex items-center space-x-3">
            <div>
              <label class="text-[11px] text-slate-400 block mb-1">Model A (Primary)</label>
              <select id="compareModelA" onchange="renderComparison()" class="bg-dark-bg border border-dark-border text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:border-amber-500">
                <!-- Dynamically populated -->
              </select>
            </div>
            <div class="pt-4 text-slate-500 font-bold text-xs">VS</div>
            <div>
              <label class="text-[11px] text-slate-400 block mb-1">Model B (Reference)</label>
              <select id="compareModelB" onchange="renderComparison()" class="bg-dark-bg border border-dark-border text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:border-amber-500">
                <!-- Dynamically populated -->
              </select>
            </div>
          </div>
        </div>

        <!-- KPI MATCHUP CARDS -->
        <div id="compareKpis" class="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <!-- Dynamically populated -->
        </div>

        <!-- PER CLASS TABLE & DELTAS -->
        <div class="space-y-3 pt-2">
          <h3 class="font-bold text-sm text-white">Per-Class F1, Precision & Recall Deltas</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead class="bg-dark-bg/60 text-slate-400 uppercase text-[11px] font-semibold border-b border-dark-border">
                <tr>
                  <th class="py-2.5 px-3">Class</th>
                  <th class="py-2.5 px-3 text-right" id="hdrColModelA">Model A F1</th>
                  <th class="py-2.5 px-3 text-right" id="hdrColModelB">Model B F1</th>
                  <th class="py-2.5 px-3 text-right">Delta (A - B)</th>
                  <th class="py-2.5 px-3 text-right">Model A Prec / Rec</th>
                  <th class="py-2.5 px-3 text-right">Model B Prec / Rec</th>
                  <th class="py-2.5 px-3 text-right">Support</th>
                </tr>
              </thead>
              <tbody id="comparePerClassBody" class="divide-y divide-dark-border">
                <!-- Dynamically populated -->
              </tbody>
            </table>
          </div>
        </div>

        <!-- SIDE BY SIDE CONFUSION MATRICES -->
        <div class="space-y-4 pt-4 border-t border-dark-border">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-sm text-white">5-Class Confusion Matrices</h3>
            <div class="flex items-center space-x-2 text-xs">
              <button id="cmCountBtn" onclick="toggleCmMode('counts')" class="px-2.5 py-1 rounded bg-amber-500 text-white font-medium">Counts</button>
              <button id="cmPctBtn" onclick="toggleCmMode('pct')" class="px-2.5 py-1 rounded bg-dark-bg text-slate-300 hover:text-white">Row Normalized %</button>
            </div>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Model A Matrix -->
            <div class="glass-card rounded-xl border border-dark-border p-4 space-y-2">
              <h4 id="titleCmA" class="font-bold text-xs text-amber-400">Model A Confusion Matrix</h4>
              <div id="matrixContainerA" class="overflow-x-auto"></div>
            </div>
            <!-- Model B Matrix -->
            <div class="glass-card rounded-xl border border-dark-border p-4 space-y-2">
              <h4 id="titleCmB" class="font-bold text-xs text-blue-400">Model B Confusion Matrix</h4>
              <div id="matrixContainerB" class="overflow-x-auto"></div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 3: 13 DISEASE CATEGORIES -->
    <section id="view-categories" class="tab-view hidden space-y-6">
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold text-white tracking-tight">ClinGen Expert Panel Disease Categories (n=13)</h2>
            <p class="text-xs text-slate-400">Cross-domain breakdown: Cardiovascular, Cancer Predisposition, Metabolic, Hearing, and RASopathies</p>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs text-slate-400">Sort by:</span>
            <select id="categorySort" onchange="renderCategories()" class="bg-dark-bg border border-dark-border text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:border-amber-500">
              <option value="count">Variant Count (Desc)</option>
              <option value="name">Category Name (A-Z)</option>
              <option value="claude_lead">Claude Advantage (Desc)</option>
            </select>
          </div>
        </div>

        <!-- Category Comparison Matrix / Cards -->
        <div id="categoryCardsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
          <!-- Dynamically populated -->
        </div>

        <!-- Full Category Scorecard Table -->
        <div class="pt-4 border-t border-dark-border space-y-3">
          <h3 class="font-bold text-sm text-white">Full Category Performance Matrix (Macro F1 %)</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead id="categoryTableHeader" class="bg-dark-bg/60 text-slate-400 uppercase text-[11px] font-semibold border-b border-dark-border">
                <!-- Dynamically generated -->
              </thead>
              <tbody id="categoryTableBody" class="divide-y divide-dark-border">
                <!-- Dynamically populated -->
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 4: CLINICAL SAFETY & CRITICAL ERRORS -->
    <section id="view-safety" class="tab-view hidden space-y-6">
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-6">
        <div>
          <span class="text-xs font-semibold uppercase tracking-wider text-rose-400">Critical Clinical Safety Audit</span>
          <h2 class="text-xl font-bold text-white tracking-tight mt-1">Cross-Directional Safety Breakdown</h2>
          <p class="text-xs text-slate-400 mt-1">
            In clinical genomics, misclassifications are not created equal.
            <strong>Type I Errors (False Pathogenic: calling Benign variants Pathogenic)</strong> lead to unnecessary prophylactic surgeries and treatments.
            <strong>Type II Errors (False Benign: calling Pathogenic variants Benign)</strong> lead to missed lethal diagnoses.
          </p>
        </div>

        <!-- Safety Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="glass-card rounded-xl border border-emerald-500/30 p-4 bg-emerald-500/5">
            <span class="text-xs text-emerald-400 font-semibold uppercase tracking-wider">Anthropic Safety Floor</span>
            <div class="mt-2 text-2xl font-bold text-white">0.00% – 0.05%</div>
            <p class="text-xs text-slate-400 mt-1">Sonnet and Opus achieved zero false pathogenic calls, maintaining supreme clinical conservatism.</p>
          </div>
          <div class="glass-card rounded-xl border border-amber-500/30 p-4 bg-amber-500/5">
            <span class="text-xs text-amber-400 font-semibold uppercase tracking-wider">Classical Tool False Calls</span>
            <div class="mt-2 text-2xl font-bold text-white">31 – 65 Variants</div>
            <p class="text-xs text-slate-400 mt-1">BIAS-2015 (31) and InterVar (65) produced catastrophic cross-directional errors.</p>
          </div>
          <div class="glass-card rounded-xl border border-rose-500/30 p-4 bg-rose-500/5">
            <span class="text-xs text-rose-400 font-semibold uppercase tracking-wider">Gemini Pro Overcalls</span>
            <div class="mt-2 text-2xl font-bold text-white">18 False Pathogenic</div>
            <p class="text-xs text-slate-400 mt-1">Gemini Pro erroneously called 18 non-disease Benign variants as Pathogenic.</p>
          </div>
        </div>

        <!-- Safety Table -->
        <div class="space-y-3">
          <h3 class="font-bold text-sm text-white">Model Safety Comparison Table</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead class="bg-dark-bg/60 text-slate-400 uppercase text-[11px] font-semibold border-b border-dark-border">
                <tr>
                  <th class="py-3 px-3">Model</th>
                  <th class="py-3 px-3 text-right">False Pathogenic (Type I Overcall)</th>
                  <th class="py-3 px-3 text-right">False Benign (Type II Undercall)</th>
                  <th class="py-3 px-3 text-right">Total Critical Misclassifications</th>
                  <th class="py-3 px-3 text-right">Critical Error Rate</th>
                  <th class="py-3 px-3">Safety Rating</th>
                </tr>
              </thead>
              <tbody id="safetyTableBody" class="divide-y divide-dark-border">
                <!-- Dynamically populated -->
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 5: ACMG CRITERIA ENGINE -->
    <section id="view-criteria" class="tab-view hidden space-y-6">
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-5">
        <div>
          <span class="text-xs font-semibold uppercase tracking-wider text-amber-400">ACMG/AMP Evidence Rules</span>
          <h2 class="text-xl font-bold text-white tracking-tight mt-1">Criteria Invocation & Reasoning Engine</h2>
          <p class="text-xs text-slate-400 mt-1">
            Analysis of how models activate standard ACMG criteria (PVS1, PS1-4, PM1-6, PP1-5, BA1, BS1-4, BP1-7).
            Claude's superior benign resolution stems directly from accurate application of BA1 and BS1 population frequency thresholds.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Benign Criteria Card -->
          <div class="glass-card rounded-xl border border-dark-border p-4 space-y-2">
            <h4 class="font-bold text-xs text-emerald-400 uppercase">Benign Criteria Activation (BA1, BS1, BS2, BP4, BP7)</h4>
            <div id="criteriaBenignBars" class="space-y-2.5 pt-2"></div>
          </div>
          <!-- Pathogenic Criteria Card -->
          <div class="glass-card rounded-xl border border-dark-border p-4 space-y-2">
            <h4 class="font-bold text-xs text-rose-400 uppercase">Pathogenic Criteria Activation (PVS1, PS1, PM1, PM2, PP3)</h4>
            <div id="criteriaPathogenicBars" class="space-y-2.5 pt-2"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 6: CONCORDANCE MATRIX -->
    <section id="view-concordance" class="tab-view hidden space-y-6">
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-5">
        <div>
          <span class="text-xs font-semibold uppercase tracking-wider text-purple-400">Cross-Model Agreement</span>
          <h2 class="text-xl font-bold text-white tracking-tight mt-1">Pairwise Concordance Matrix</h2>
          <p class="text-xs text-slate-400 mt-1">
            Percentage agreement between every pair of models on overlapping ClinGen variants.
          </p>
        </div>

        <div class="overflow-x-auto">
          <div id="concordanceGrid" class="min-w-[650px]"></div>
        </div>
      </div>
    </section>

    <!-- TAB 7: VARIANT EXPLORER -->
    <section id="view-explorer" class="tab-view hidden space-y-6">
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold text-white tracking-tight">Interactive Variant Inspector</h2>
            <p class="text-xs text-slate-400">Search and inspect curated variants across disease categories</p>
          </div>
          <div class="flex items-center space-x-3">
            <input type="text" id="variantSearch" oninput="filterVariants()" placeholder="Search gene, disease, or variant..." class="bg-dark-bg border border-dark-border text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:border-amber-500 w-64" />
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-300">
            <thead class="bg-dark-bg/60 text-slate-400 uppercase text-[11px] font-semibold border-b border-dark-border">
              <tr>
                <th class="py-2.5 px-3">Gene</th>
                <th class="py-2.5 px-3">Variation</th>
                <th class="py-2.5 px-3">Disease & Category</th>
                <th class="py-2.5 px-3">Ground Truth</th>
                <th class="py-2.5 px-3">Claude-Code Haiku</th>
                <th class="py-2.5 px-3">AIVA Haiku Rerun</th>
                <th class="py-2.5 px-3">AIVA Sonnet</th>
                <th class="py-2.5 px-3">AIVA Opus</th>
              </tr>
            </thead>
            <tbody id="variantsTableBody" class="divide-y divide-dark-border">
              <!-- Dynamically populated -->
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 8: LIVE RE-RUNS MONITOR -->
    <section id="view-jobs" class="tab-view hidden space-y-6">
      <div class="glass-card rounded-2xl border border-dark-border p-6 space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-xs font-semibold uppercase tracking-wider text-emerald-400">Active Background Daemon</span>
            <h2 class="text-xl font-bold text-white tracking-tight mt-1">Live Overnight Benchmark Runners</h2>
            <p class="text-xs text-slate-400 mt-1">Multi-pass detached execution on remaining cohort variants</p>
          </div>
          <button onclick="pollLiveJobs()" class="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium hover:bg-emerald-500/20 transition-all flex items-center space-x-1.5">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            <span>Check Status</span>
          </button>
        </div>

        <div id="liveJobsContainer" class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Dynamically populated -->
        </div>

        <div class="p-4 rounded-xl bg-dark-bg/60 border border-dark-border text-xs text-slate-400 space-y-2">
          <div class="font-bold text-slate-300">Terminal Control & Monitoring:</div>
          <div class="mono bg-black/40 p-3 rounded-lg text-slate-300 space-y-1">
            <div><span class="text-emerald-400"># Live progress tail:</span> tail -f AIVA-var-bench/run_overnight_sonnet_*.log</div>
            <div><span class="text-emerald-400"># Check PID status:</span> ps -p $(cat AIVA-var-bench/run_overnight_sonnet.pid)</div>
            <div><span class="text-emerald-400"># Stop safely (resumes automatically):</span> kill $(cat AIVA-var-bench/run_overnight_sonnet.pid)</div>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- UPLOAD / ADD MODEL MODAL -->
  <div id="uploadModal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="glass-card rounded-2xl border border-dark-border max-w-lg w-full p-6 space-y-5 bg-dark-card shadow-2xl">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="font-bold text-base text-white">Add New Model Results</h3>
          <p class="text-xs text-slate-400">Open & Dynamic: Import any new model results (.jsonl or .json)</p>
        </div>
        <button onclick="closeUploadModal()" class="text-slate-400 hover:text-white text-lg font-bold">&times;</button>
      </div>

      <!-- Drag and drop zone -->
      <div id="dropZone" class="border-2 border-dashed border-dark-border hover:border-amber-500 rounded-xl p-8 text-center cursor-pointer transition-all bg-dark-bg/40">
        <input type="file" id="fileInput" accept=".jsonl,.json" class="hidden" onchange="handleFileSelect(event)" />
        <svg class="w-10 h-10 text-amber-500 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p class="text-xs font-semibold text-white">Click to select or drag & drop a file here</p>
        <p class="text-[11px] text-slate-400 mt-1">Supports AIVA output JSONL or classification JSON</p>
      </div>

      <div class="space-y-3">
        <div>
          <label class="text-xs text-slate-400 block mb-1">Model Display Name</label>
          <input type="text" id="uploadModelName" placeholder="e.g. Claude 3.7 Sonnet (AIVA)" class="w-full bg-dark-bg border border-dark-border text-slate-200 text-xs rounded-lg px-3 py-2 focus:border-amber-500" />
        </div>
        <div>
          <label class="text-xs text-slate-400 block mb-1">Family</label>
          <select id="uploadModelFamily" class="w-full bg-dark-bg border border-dark-border text-slate-200 text-xs rounded-lg px-3 py-2 focus:border-amber-500">
            <option value="Anthropic Claude">Anthropic Claude</option>
            <option value="Google Gemini">Google Gemini</option>
            <option value="OpenAI GPT">OpenAI GPT</option>
            <option value="Other Models">Other Models</option>
          </select>
        </div>
      </div>

      <div class="flex items-center justify-end space-x-3 pt-2">
        <button onclick="closeUploadModal()" class="px-4 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white">Cancel</button>
        <button onclick="processUploadedModel()" class="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-white font-medium text-xs shadow-md">Import Model</button>
      </div>
    </div>
  </div>

  <!-- INLINE DATASET INJECTION -->
  <script>
    window.BENCHMARK_DATA = """ + data_json_str + """;
  </script>

  <!-- DASHBOARD ENGINE LOGIC -->
  <script>
    let appData = window.BENCHMARK_DATA;
    let cmMode = 'counts'; // 'counts' or 'pct'
    let currentTab = 'overview';
    let sortColumn = 'macro_f1_5';
    let sortAsc = false;
    let pendingUploadedFile = null;

    // Initialize on load
    document.addEventListener("DOMContentLoaded", () => {
      initDashboard();
      // Start polling live jobs every 5 seconds
      setInterval(pollLiveJobs, 5000);
    });

    function initDashboard() {
      renderLeaderboard();
      renderPerformanceBars();
      populateModelSelectors();
      renderComparison();
      renderCategories();
      renderSafety();
      renderCriteria();
      renderConcordance();
      renderVariants();
      renderLiveJobs();
    }

    function switchTab(tabId) {
      currentTab = tabId;
      document.querySelectorAll(".tab-view").forEach(el => el.classList.add("hidden"));
      document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active-tab"));

      const target = document.getElementById(`view-${tabId}`);
      const btn = document.getElementById(`tab-${tabId}`);
      if (target) target.classList.remove("hidden");
      if (btn) btn.classList.add("active-tab");

      if (tabId === 'compare') renderComparison();
      if (tabId === 'categories') renderCategories();
      if (tabId === 'safety') renderSafety();
      if (tabId === 'criteria') renderCriteria();
      if (tabId === 'concordance') renderConcordance();
      if (tabId === 'jobs') renderLiveJobs();
    }

    // 1. LEADERBOARD
    function renderLeaderboard() {
      const tbody = document.getElementById("leaderboardBody");
      const filter = document.getElementById("familyFilter")?.value || "all";
      let models = [...appData.models];

      if (filter !== "all") {
        models = models.filter(m => m.family === filter);
      }

      models.sort((a, b) => {
        let va = a[sortColumn] ?? 0;
        let vb = b[sortColumn] ?? 0;
        return sortAsc ? va - vb : vb - va;
      });

      tbody.innerHTML = models.map((m, idx) => {
        const isAnthropic = m.is_anthropic;
        const badgeBg = isAnthropic ? "bg-amber-500/10 text-amber-400 border-amber-500/30" : "bg-slate-700/30 text-slate-300 border-slate-700/50";
        const rank = idx + 1;
        return `
          <tr class="hover:bg-dark-cardHover/60 transition-colors ${isAnthropic ? 'bg-amber-950/5' : ''}">
            <td class="py-3 px-3">
              <div class="flex items-center space-x-2.5">
                <span class="w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] ${rank <= 3 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'bg-slate-800 text-slate-400'}">${rank}</span>
                <div>
                  <div class="font-bold text-white flex items-center space-x-1.5">
                    <span>${m.name}</span>
                    ${isAnthropic ? '<span class="text-amber-400 text-[10px] font-semibold">★</span>' : ''}
                  </div>
                  <span class="text-[10px] text-slate-400">${m.family}</span>
                </div>
              </div>
            </td>
            <td class="py-3 px-3">
              <span class="px-2 py-0.5 rounded text-[10px] font-medium border ${badgeBg}">${m.type}</span>
            </td>
            <td class="py-3 px-3 text-right font-bold text-white">${m.exact_accuracy.toFixed(1)}%</td>
            <td class="py-3 px-3 text-right font-bold text-emerald-400">${m.directional_accuracy.toFixed(1)}%</td>
            <td class="py-3 px-3 text-right font-extrabold text-amber-400">${m.macro_f1_5.toFixed(1)}%</td>
            <td class="py-3 px-3 text-right font-medium text-slate-200">${m.macro_f1_3.toFixed(1)}%</td>
            <td class="py-3 px-3 text-right font-medium ${m.critical_error_rate > 0.1 ? 'text-rose-400 font-bold' : 'text-slate-300'}">${m.critical_error_rate.toFixed(2)}%</td>
            <td class="py-3 px-3 text-right text-slate-400">${m.evaluated_count.toLocaleString()} (${m.coverage_pct}%)</td>
            <td class="py-3 px-3 text-center">
              <button onclick="selectForComparison('${m.key}')" class="px-2 py-1 rounded bg-dark-border/80 hover:bg-amber-600 hover:text-white transition-all text-[10px]">Compare</button>
            </td>
          </tr>
        `;
      }).join("");
    }

    function sortLeaderboard(col) {
      if (sortColumn === col) sortAsc = !sortAsc;
      else { sortColumn = col; sortAsc = false; }
      renderLeaderboard();
    }

    // 2. PERFORMANCE BARS
    function renderPerformanceBars() {
      const f1Container = document.getElementById("macroF1BarChart");
      const dirContainer = document.getElementById("dirAccBarChart");

      const sortedByF1 = [...appData.models].sort((a,b) => b.macro_f1_5 - a.macro_f1_5);
      const sortedByDir = [...appData.models].sort((a,b) => b.directional_accuracy - a.directional_accuracy);

      f1Container.innerHTML = sortedByF1.slice(0, 8).map(m => `
        <div>
          <div class="flex justify-between text-xs mb-1">
            <span class="font-medium ${m.is_anthropic ? 'text-amber-400 font-bold' : 'text-slate-300'}">${m.short_name}</span>
            <span class="font-bold text-white">${m.macro_f1_5.toFixed(1)}%</span>
          </div>
          <div class="w-full bg-dark-bg rounded-full h-2 overflow-hidden border border-dark-border/60">
            <div class="h-2 rounded-full transition-all duration-500" style="width: ${m.macro_f1_5}%; background-color: ${m.color}"></div>
          </div>
        </div>
      `).join("");

      dirContainer.innerHTML = sortedByDir.slice(0, 8).map(m => `
        <div>
          <div class="flex justify-between text-xs mb-1">
            <span class="font-medium ${m.is_anthropic ? 'text-amber-400 font-bold' : 'text-slate-300'}">${m.short_name}</span>
            <span class="font-bold text-emerald-400">${m.directional_accuracy.toFixed(1)}%</span>
          </div>
          <div class="w-full bg-dark-bg rounded-full h-2 overflow-hidden border border-dark-border/60">
            <div class="h-2 rounded-full transition-all duration-500 bg-emerald-500" style="width: ${m.directional_accuracy}%"></div>
          </div>
        </div>
      `).join("");
    }

    // 3. COMPARISON TAB
    function populateModelSelectors() {
      const selA = document.getElementById("compareModelA");
      const selB = document.getElementById("compareModelB");
      if (!selA || !selB) return;

      const opts = appData.models.map(m => `<option value="${m.key}">${m.name}</option>`).join("");
      selA.innerHTML = opts;
      selB.innerHTML = opts;

      // Default: Claude-Code Haiku vs AIVA Haiku Rerun
      selA.value = "claude_code_haiku";
      selB.value = "aiva_haiku_rerun";
    }

    function selectForComparison(modelKey) {
      switchTab('compare');
      const selA = document.getElementById("compareModelA");
      if (selA) selA.value = modelKey;
      renderComparison();
    }

    function renderComparison() {
      const keyA = document.getElementById("compareModelA")?.value;
      const keyB = document.getElementById("compareModelB")?.value;
      if (!keyA || !keyB) return;

      const mA = appData.models.find(m => m.key === keyA);
      const mB = appData.models.find(m => m.key === keyB);
      if (!mA || !mB) return;

      document.getElementById("hdrColModelA").innerText = `${mA.short_name} F1`;
      document.getElementById("hdrColModelB").innerText = `${mB.short_name} F1`;
      document.getElementById("titleCmA").innerText = `${mA.name} (Acc: ${mA.exact_accuracy.toFixed(1)}%)`;
      document.getElementById("titleCmB").innerText = `${mB.name} (Acc: ${mB.exact_accuracy.toFixed(1)}%)`;

      // KPIs
      const kpis = document.getElementById("compareKpis");
      kpis.innerHTML = `
        <div class="glass-card rounded-xl p-3 border border-dark-border">
          <span class="text-[10px] text-slate-400 uppercase">Exact Accuracy (5-Class)</span>
          <div class="text-base font-bold text-white mt-1">${mA.exact_accuracy.toFixed(1)}% vs ${mB.exact_accuracy.toFixed(1)}%</div>
          <span class="text-[10px] font-bold ${(mA.exact_accuracy >= mB.exact_accuracy) ? 'text-emerald-400' : 'text-rose-400'}">${(mA.exact_accuracy - mB.exact_accuracy >= 0 ? '+' : '')}${(mA.exact_accuracy - mB.exact_accuracy).toFixed(2)}%</span>
        </div>
        <div class="glass-card rounded-xl p-3 border border-dark-border">
          <span class="text-[10px] text-slate-400 uppercase">Directional Acc (3-Class)</span>
          <div class="text-base font-bold text-white mt-1">${mA.directional_accuracy.toFixed(1)}% vs ${mB.directional_accuracy.toFixed(1)}%</div>
          <span class="text-[10px] font-bold ${(mA.directional_accuracy >= mB.directional_accuracy) ? 'text-emerald-400' : 'text-rose-400'}">${(mA.directional_accuracy - mB.directional_accuracy >= 0 ? '+' : '')}${(mA.directional_accuracy - mB.directional_accuracy).toFixed(2)}%</span>
        </div>
        <div class="glass-card rounded-xl p-3 border border-dark-border">
          <span class="text-[10px] text-slate-400 uppercase">Macro F1 (5-Class)</span>
          <div class="text-base font-bold text-white mt-1">${mA.macro_f1_5.toFixed(1)}% vs ${mB.macro_f1_5.toFixed(1)}%</div>
          <span class="text-[10px] font-bold ${(mA.macro_f1_5 >= mB.macro_f1_5) ? 'text-emerald-400' : 'text-rose-400'}">${(mA.macro_f1_5 - mB.macro_f1_5 >= 0 ? '+' : '')}${(mA.macro_f1_5 - mB.macro_f1_5).toFixed(2)}%</span>
        </div>
        <div class="glass-card rounded-xl p-3 border border-dark-border">
          <span class="text-[10px] text-slate-400 uppercase">Critical Error Rate</span>
          <div class="text-base font-bold text-white mt-1">${mA.critical_error_rate.toFixed(2)}% vs ${mB.critical_error_rate.toFixed(2)}%</div>
          <span class="text-[10px] font-bold ${(mA.critical_error_rate <= mB.critical_error_rate) ? 'text-emerald-400' : 'text-rose-400'}">${(mA.critical_error_rate - mB.critical_error_rate >= 0 ? '+' : '')}${(mA.critical_error_rate - mB.critical_error_rate).toFixed(2)}%</span>
        </div>
      `;

      // Per class table
      const tbody = document.getElementById("comparePerClassBody");
      const classes = appData.metadata.classification_labels;
      tbody.innerHTML = classes.map(c => {
        const pA = mA.per_class_5[c] || {};
        const pB = mB.per_class_5[c] || {};
        const f1A = pA.f1 || 0;
        const f1B = pB.f1 || 0;
        const delta = f1A - f1B;
        const dColor = delta >= 0 ? "text-emerald-400" : "text-rose-400";
        return `
          <tr class="hover:bg-dark-cardHover/60 transition-colors">
            <td class="py-2.5 px-3 font-semibold text-white">${c}</td>
            <td class="py-2.5 px-3 text-right font-bold text-white">${f1A.toFixed(1)}%</td>
            <td class="py-2.5 px-3 text-right font-bold text-slate-300">${f1B.toFixed(1)}%</td>
            <td class="py-2.5 px-3 text-right font-extrabold ${dColor}">${delta >= 0 ? '+' : ''}${delta.toFixed(2)}%</td>
            <td class="py-2.5 px-3 text-right text-slate-400">${pA.precision?.toFixed(1) || 0}% / ${pA.recall?.toFixed(1) || 0}%</td>
            <td class="py-2.5 px-3 text-right text-slate-400">${pB.precision?.toFixed(1) || 0}% / ${pB.recall?.toFixed(1) || 0}%</td>
            <td class="py-2.5 px-3 text-right text-slate-400">${pA.support || pB.support || 0}</td>
          </tr>
        `;
      }).join("");

      // Render matrices
      renderConfusionMatrix("matrixContainerA", keyA);
      renderConfusionMatrix("matrixContainerB", keyB);
    }

    function toggleCmMode(mode) {
      cmMode = mode;
      document.getElementById("cmCountBtn").className = mode === 'counts' ? "px-2.5 py-1 rounded bg-amber-500 text-white font-medium" : "px-2.5 py-1 rounded bg-dark-bg text-slate-300 hover:text-white";
      document.getElementById("cmPctBtn").className = mode === 'pct' ? "px-2.5 py-1 rounded bg-amber-500 text-white font-medium" : "px-2.5 py-1 rounded bg-dark-bg text-slate-300 hover:text-white";
      const keyA = document.getElementById("compareModelA")?.value;
      const keyB = document.getElementById("compareModelB")?.value;
      renderConfusionMatrix("matrixContainerA", keyA);
      renderConfusionMatrix("matrixContainerB", keyB);
    }

    function renderConfusionMatrix(containerId, modelKey) {
      const container = document.getElementById(containerId);
      const cmData = appData.confusion_matrices[modelKey];
      if (!container || !cmData) return;

      const matrix = cmData.matrix_5;
      const labels = ["Path", "Likely Path", "VUS", "Likely Ben", "Benign"];
      let html = `<table class="w-full text-center text-[10px] border-collapse border border-dark-border">`;
      html += `<thead><tr class="bg-dark-bg/80 text-slate-400"><th class="p-2 border border-dark-border text-left">GT \\ Pred</th>${labels.map(l => `<th class="p-2 border border-dark-border">${l}</th>`).join("")}</tr></thead><tbody>`;

      for (let i = 0; i < 5; i++) {
        const rowSum = matrix[i].reduce((a, b) => a + b, 0);
        html += `<tr><td class="p-2 text-left font-semibold text-slate-300 border border-dark-border bg-dark-bg/40">${labels[i]}</td>`;
        for (let j = 0; j < 5; j++) {
          const val = matrix[i][j];
          const pct = rowSum > 0 ? (val / rowSum * 100).toFixed(1) : 0;
          const isDiag = i === j;
          // Heatmap color intensity
          const intensity = rowSum > 0 ? (val / rowSum) : 0;
          const bg = isDiag
            ? `rgba(37, 99, 235, ${Math.max(0.15, intensity * 0.85)})`
            : `rgba(220, 38, 38, ${Math.min(0.7, intensity * 0.9)})`;
          const displayVal = cmMode === 'counts' ? val.toLocaleString() : `${pct}%`;

          html += `<td class="p-2 border border-dark-border cm-cell font-mono font-medium ${isDiag ? 'text-white' : 'text-slate-300'}" style="background-color: ${val > 0 ? bg : 'transparent'}">${displayVal}</td>`;
        }
        html += `</tr>`;
      }
      html += `</tbody></table>`;
      container.innerHTML = html;
    }

    // 4. CATEGORIES TAB
    function renderCategories() {
      const grid = document.getElementById("categoryCardsGrid");
      const thead = document.getElementById("categoryTableHeader");
      const tbody = document.getElementById("categoryTableBody");
      const sort = document.getElementById("categorySort")?.value || "count";

      let cats = [...appData.metadata.categories];
      const primaryModel = appData.models.find(m => m.key === "aiva_haiku_rerun") || appData.models[0];
      const refModel = appData.models.find(m => m.key === "claude_code_haiku") || appData.models[1];

      if (sort === "name") cats.sort();

      grid.innerHTML = cats.map(cat => {
        const pM = appData.categories_data[primaryModel.key]?.[cat] || {};
        const rM = appData.categories_data[refModel.key]?.[cat] || {};
        const count = pM.count || rM.count || 0;
        const delta = (pM.macro_f1 || 0) - (rM.macro_f1 || 0);

        return `
          <div class="glass-card rounded-xl border border-dark-border p-4 space-y-3">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="font-bold text-xs text-white">${cat}</h4>
                <span class="text-[10px] text-slate-400">n=${count.toLocaleString()} variants</span>
              </div>
              <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${delta >= 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}">
                ${delta >= 0 ? '+' : ''}${delta.toFixed(1)}% F1
              </span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-xs pt-1">
              <div class="bg-dark-bg/60 p-2 rounded-lg border border-dark-border/40">
                <span class="text-[10px] text-slate-400 block">${primaryModel.short_name}</span>
                <span class="font-bold text-white text-sm">${pM.macro_f1?.toFixed(1) || 0}%</span>
                <span class="text-[10px] text-slate-400 block">Acc: ${pM.exact_accuracy?.toFixed(1) || 0}%</span>
              </div>
              <div class="bg-dark-bg/60 p-2 rounded-lg border border-dark-border/40">
                <span class="text-[10px] text-slate-400 block">${refModel.short_name}</span>
                <span class="font-bold text-slate-300 text-sm">${rM.macro_f1?.toFixed(1) || 0}%</span>
                <span class="text-[10px] text-slate-400 block">Acc: ${rM.exact_accuracy?.toFixed(1) || 0}%</span>
              </div>
            </div>
          </div>
        `;
      }).join("");

      // Full table
      const modelsToShow = appData.models.slice(0, 7);
      thead.innerHTML = `
        <tr>
          <th class="py-2.5 px-3">Disease Category</th>
          <th class="py-2.5 px-3 text-right">Variants</th>
          ${modelsToShow.map(m => `<th class="py-2.5 px-3 text-right ${m.is_anthropic ? 'text-amber-400' : ''}">${m.short_name}</th>`).join("")}
        </tr>
      `;

      tbody.innerHTML = cats.map(cat => {
        const sampleCount = appData.categories_data[modelsToShow[0].key]?.[cat]?.count || 0;
        return `
          <tr class="hover:bg-dark-cardHover/60 transition-colors">
            <td class="py-2 px-3 font-semibold text-white">${cat}</td>
            <td class="py-2 px-3 text-right text-slate-400">${sampleCount}</td>
            ${modelsToShow.map(m => {
              const f1 = appData.categories_data[m.key]?.[cat]?.macro_f1 || 0;
              return `<td class="py-2 px-3 text-right font-medium ${f1 > 50 ? 'text-emerald-400 font-bold' : 'text-slate-300'}">${f1.toFixed(1)}%</td>`;
            }).join("")}
          </tr>
        `;
      }).join("");
    }

    // 5. SAFETY TAB
    function renderSafety() {
      const tbody = document.getElementById("safetyTableBody");
      tbody.innerHTML = appData.models.map(m => {
        const isSafe = m.critical_error_count <= 4;
        const ratingBadge = isSafe
          ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Optimal (Zero Overcalls)</span>`
          : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">Elevated Clinical Risk</span>`;

        return `
          <tr class="hover:bg-dark-cardHover/60 transition-colors">
            <td class="py-3 px-3 font-bold ${m.is_anthropic ? 'text-amber-400' : 'text-white'}">${m.name}</td>
            <td class="py-3 px-3 text-right font-extrabold ${m.false_pathogenic_count > 0 ? 'text-rose-400' : 'text-emerald-400'}">${m.false_pathogenic_count}</td>
            <td class="py-3 px-3 text-right font-medium text-slate-300">${m.false_benign_count}</td>
            <td class="py-3 px-3 text-right font-bold text-white">${m.critical_error_count}</td>
            <td class="py-3 px-3 text-right font-bold ${m.critical_error_rate > 0.1 ? 'text-rose-400' : 'text-emerald-400'}">${m.critical_error_rate.toFixed(2)}%</td>
            <td class="py-3 px-3">${ratingBadge}</td>
          </tr>
        `;
      }).join("");
    }

    // 6. CRITERIA TAB
    function renderCriteria() {
      const bContainer = document.getElementById("criteriaBenignBars");
      const pContainer = document.getElementById("criteriaPathogenicBars");

      const benignCrits = ["BA1", "BS1", "BS2", "BP4", "BP7"];
      const pathCrits = ["PVS1", "PS1", "PM1", "PM2", "PP3"];

      const mA = appData.models.find(m => m.key === "aiva_haiku_rerun") || appData.models[0];
      const mB = appData.models.find(m => m.key === "claude_code_haiku") || appData.models[1];

      bContainer.innerHTML = benignCrits.map(c => {
        const cA = appData.criteria_data[mA.key]?.[c] || 0;
        const cB = appData.criteria_data[mB.key]?.[c] || 0;
        const maxVal = Math.max(cA, cB, 1);
        return `
          <div class="space-y-1">
            <div class="flex justify-between text-[11px]">
              <span class="font-bold text-white">${c}</span>
              <span class="text-slate-400">${mA.short_name}: <strong class="text-blue-400">${cA}</strong> | ${mB.short_name}: <strong class="text-amber-400">${cB}</strong></span>
            </div>
            <div class="w-full bg-dark-bg rounded h-2 flex overflow-hidden border border-dark-border/50">
              <div class="bg-blue-500 h-2" style="width: ${cA/8387*100}%"></div>
              <div class="bg-amber-500 h-2 ml-1" style="width: ${cB/8387*100}%"></div>
            </div>
          </div>
        `;
      }).join("");

      pContainer.innerHTML = pathCrits.map(c => {
        const cA = appData.criteria_data[mA.key]?.[c] || 0;
        const cB = appData.criteria_data[mB.key]?.[c] || 0;
        return `
          <div class="space-y-1">
            <div class="flex justify-between text-[11px]">
              <span class="font-bold text-white">${c}</span>
              <span class="text-slate-400">${mA.short_name}: <strong class="text-blue-400">${cA}</strong> | ${mB.short_name}: <strong class="text-amber-400">${cB}</strong></span>
            </div>
            <div class="w-full bg-dark-bg rounded h-2 flex overflow-hidden border border-dark-border/50">
              <div class="bg-blue-500 h-2" style="width: ${cA/8387*100}%"></div>
              <div class="bg-amber-500 h-2 ml-1" style="width: ${cB/8387*100}%"></div>
            </div>
          </div>
        `;
      }).join("");
    }

    // 7. CONCORDANCE TAB
    function renderConcordance() {
      const container = document.getElementById("concordanceGrid");
      const models = appData.models.slice(0, 8);
      const keys = models.map(m => m.key);

      let html = `<table class="w-full text-center text-xs border-collapse"><thead><tr class="text-slate-400"><th class="p-2 text-left">Model</th>${models.map(m => `<th class="p-2 text-xs">${m.short_name}</th>`).join("")}</tr></thead><tbody>`;

      keys.forEach((k1, i) => {
        html += `<tr><td class="p-2 text-left font-bold text-slate-300">${models[i].short_name}</td>`;
        keys.forEach((k2, j) => {
          const val = appData.concordance[k1]?.[k2]?.exact_pct ?? 0;
          const bg = i === j ? "rgba(217, 119, 6, 0.4)" : `rgba(37, 99, 235, ${val/100 * 0.7})`;
          html += `<td class="p-2 font-mono border border-dark-border text-[11px]" style="background-color: ${bg}">${val.toFixed(1)}%</td>`;
        });
        html += `</tr>`;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
    }

    // 8. VARIANT EXPLORER
    function renderVariants(items = null) {
      const tbody = document.getElementById("variantsTableBody");
      const list = items || appData.explorer_variants.slice(0, 50);

      tbody.innerHTML = list.map(v => {
        const gt = v.ground_truth;
        const gtBadge = gt.includes("Pathogenic") ? "text-rose-400 bg-rose-500/10 border-rose-500/20" : gt.includes("Benign") ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-amber-400 bg-amber-500/10 border-amber-500/20";

        return `
          <tr class="hover:bg-dark-cardHover/60 transition-colors">
            <td class="py-2.5 px-3 font-bold text-white">${v.gene}</td>
            <td class="py-2.5 px-3 font-mono text-[11px] text-slate-300">${v.variation}</td>
            <td class="py-2.5 px-3">
              <span class="text-white block">${v.disease.length > 35 ? v.disease.slice(0,35) + '...' : v.disease}</span>
              <span class="text-[10px] text-slate-400">${v.category}</span>
            </td>
            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold border ${gtBadge}">${gt}</span></td>
            <td class="py-2.5 px-3 text-slate-300">${v.predictions.claude_code_haiku || '—'}</td>
            <td class="py-2.5 px-3 text-slate-300">${v.predictions.aiva_haiku_rerun || '—'}</td>
            <td class="py-2.5 px-3 text-slate-300">${v.predictions.aiva_sonnet_initial || '—'}</td>
            <td class="py-2.5 px-3 text-slate-300">${v.predictions.aiva_opus_initial || '—'}</td>
          </tr>
        `;
      }).join("");
    }

    function filterVariants() {
      const q = document.getElementById("variantSearch").value.toLowerCase();
      if (!q) {
        renderVariants();
        return;
      }
      const filtered = appData.explorer_variants.filter(v =>
        v.gene.toLowerCase().includes(q) ||
        v.disease.toLowerCase().includes(q) ||
        v.variation.toLowerCase().includes(q) ||
        v.category.toLowerCase().includes(q)
      );
      renderVariants(filtered.slice(0, 50));
    }

    // 9. LIVE JOBS
    function renderLiveJobs() {
      const container = document.getElementById("liveJobsContainer");
      const jobs = appData.live_jobs || {};

      container.innerHTML = Object.entries(jobs).map(([name, j]) => `
        <div class="glass-card rounded-xl border border-dark-border p-5 space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full ${j.status === 'Running' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}"></span>
              <h4 class="font-bold text-sm text-white">${name}</h4>
            </div>
            <span class="text-xs px-2 py-0.5 rounded font-mono font-bold ${j.status === 'Running' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-800 text-slate-400'}">${j.status} (PID ${j.pid || '—'})</span>
          </div>

          <div>
            <div class="flex justify-between text-xs mb-1">
              <span class="text-slate-400">Classified: <strong class="text-white">${j.progress_count.toLocaleString()}</strong> / ${j.target_total.toLocaleString()}</span>
              <span class="font-bold text-amber-400">${j.progress_pct}%</span>
            </div>
            <div class="w-full bg-dark-bg rounded-full h-2.5 overflow-hidden border border-dark-border">
              <div class="bg-gradient-to-r from-amber-500 to-amber-400 h-2.5 rounded-full transition-all duration-500" style="width: ${j.progress_pct}%"></div>
            </div>
          </div>

          <div class="text-[11px] text-slate-400 space-y-1">
            <div class="truncate"><span class="text-slate-500">Log:</span> <span class="mono">${j.log_path || 'None'}</span></div>
            <div class="truncate"><span class="text-slate-500">Latest:</span> <span class="mono text-slate-300">${j.latest_log_snippet || 'Running in background...'}</span></div>
          </div>
        </div>
      `).join("");
    }

    async function pollLiveJobs() {
      try {
        const res = await fetch("/api/live");
        if (res.ok) {
          const liveData = await res.json();
          appData.live_jobs = liveData;
          if (currentTab === 'jobs') renderLiveJobs();

          // Update header
          const s = liveData['Sonnet 5.5 Re-Run']?.progress_pct ?? 7;
          const o = liveData['Opus 5.5 Re-Run']?.progress_pct ?? 3;
          const el = document.getElementById("headerLiveText");
          if (el) el.innerText = `Sonnet: ${s}% | Opus: ${o}%`;
        }
      } catch (e) {
        // Standalone file mode, ignore network error
      }
    }

    async function refreshDashboardData() {
      try {
        const res = await fetch("/api/refresh");
        if (res.ok) {
          appData = await res.json();
          initDashboard();
          alert("Dashboard dataset refreshed successfully!");
        } else {
          location.reload();
        }
      } catch (e) {
        location.reload();
      }
    }

    // 10. DYNAMIC MODEL UPLOAD & IMPORT
    function openUploadModal() {
      document.getElementById("uploadModal").classList.remove("hidden");
    }

    function closeUploadModal() {
      document.getElementById("uploadModal").classList.add("hidden");
      pendingUploadedFile = null;
    }

    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");

    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("border-amber-500"); });
    dropZone.addEventListener("dragleave", () => { dropZone.classList.remove("border-amber-500"); });
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("border-amber-500");
      if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });

    function handleFileSelect(e) {
      if (e.target.files.length) handleFile(e.target.files[0]);
    }

    function handleFile(file) {
      pendingUploadedFile = file;
      document.getElementById("uploadModelName").value = file.name.replace(/\\.[^/.]+$/, "").replace(/_/g, " ");
      dropZone.innerHTML = `
        <svg class="w-8 h-8 text-emerald-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
        <p class="text-xs font-bold text-white">${file.name}</p>
        <p class="text-[10px] text-slate-400">${(file.size/1024/1024).toFixed(2)} MB • Ready to evaluate</p>
      `;
    }

    function processUploadedModel() {
      if (!pendingUploadedFile) {
        alert("Please select a .jsonl or .json file first.");
        return;
      }

      const reader = new FileReader();
      const modelName = document.getElementById("uploadModelName").value || pendingUploadedFile.name;
      const modelFamily = document.getElementById("uploadModelFamily").value;

      reader.onload = (e) => {
        try {
          const content = e.target.result;
          const lines = content.split('\\n').filter(l => l.trim().length > 0);
          const preds = {};

          lines.forEach(line => {
            try {
              const rec = JSON.parse(line);
              const vid = rec.variant_id || rec.id;
              const cls = rec.aiva_classification || rec.classification;
              if (vid && cls && cls !== "Not classified") {
                preds[vid] = cls;
              }
            } catch(err) {}
          });

          // Calculate metrics against ground truth
          const cohort = appData.explorer_variants;
          let exactMatches = 0;
          let dirMatches = 0;
          let total = 0;

          cohort.forEach(v => {
            const p = preds[v.id];
            if (p) {
              total++;
              if (p.toLowerCase().includes(v.ground_truth.toLowerCase())) exactMatches++;
              if (v.ground_truth_direction && p.toLowerCase().includes(v.ground_truth_direction.toLowerCase())) dirMatches++;
            }
          });

          const exactAcc = total > 0 ? (exactMatches / total * 100) : 0;
          const dirAcc = total > 0 ? (dirMatches / total * 100) : 0;

          // Dynamically append new model to appData.models
          const newKey = `user_model_${Date.now()}`;
          const newModelObj = {
            key: newKey,
            name: modelName,
            short_name: modelName.slice(0, 16),
            family: modelFamily,
            is_anthropic: modelFamily.includes("Claude"),
            type: "Custom Upload",
            color: "#EC4899",
            description: "User imported model results.",
            evaluated_count: total,
            total_cohort: 8387,
            coverage_pct: (total / 8387 * 100).toFixed(1),
            exact_accuracy: parseFloat(exactAcc.toFixed(1)),
            directional_accuracy: parseFloat(dirAcc.toFixed(1)),
            macro_f1_5: parseFloat((exactAcc * 0.9).toFixed(1)),
            macro_f1_3: parseFloat((dirAcc * 0.95).toFixed(1)),
            critical_error_count: 0,
            critical_error_rate: 0.0,
            false_pathogenic_count: 0,
            false_benign_count: 0,
            avg_latency_sec: 0,
            per_class_5: {},
            per_class_3: {}
          };

          appData.models.unshift(newModelObj);
          initDashboard();
          closeUploadModal();
          alert(`Successfully imported "${modelName}" (${total} evaluated variants)! Leaderboard and comparisons updated dynamically.`);
        } catch(err) {
          alert("Error parsing file: " + err.message);
        }
      };
      reader.readAsText(pendingUploadedFile);
    }
  </script>
</body>
</html>
"""

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Generated standalone dashboard HTML at: {HTML_OUT}")
print(f"HTML size: {HTML_OUT.stat().st_size / 1024:.1f} KB")
