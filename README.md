# BQL Skill Research Project: Autonomous Multi-Agent System

> **Quick Install:** See [Installation & Usage](#installation--usage) below to get started immediately.

## Table of Contents

- [Installation & Usage](#installation--usage)
- [Objective](#objective)
- [High-Level Architecture](#high-level-architecture)

## Installation & Usage

### Prerequisites

- Python 3.12+
- [beancount](https://github.com/beancount/beancount) 3.2+
- [beanquery](https://github.com/beancount/beanquery) 0.2+

### Install as a Pi Skill

This project includes a Pi-compatible skill. When opened in pi, the skill auto-loads:

```bash
# The skill is at .pi/skills/bql-skill/SKILL.md
# pi discovers it automatically when you open this directory
```

### Manual Install

```bash
git clone <this-repo>
cd bql-skill
pip install beancount beanquery pyyaml
```

### Quick Start

```bash
# Run full multi-agent pipeline
python run_pipeline.py

# Run only the evaluator (Agent 3)
python run_pipeline.py --agent 3

# Continuous improvement loop
python run_pipeline.py --loop --max-iterations 10

# Unit tests
python -m unittest tests.test_core -v
```

### Skill Prompt

The generated BQL skill prompt is at [`skill/prompt.md`](skill/prompt.md). Load this when converting natural language finance questions into BQL queries.

### Cross-Platform Installation

Install to any agent platform:

```bash
# Auto-detect platform and install (Claude Code, Copilot, Cursor, Windsurf, etc.)
./install.sh

# Install to specific platform
./install.sh --platform claude
./install.sh --platform cursor
./install.sh --platform copilot

# Install to all detected platforms
./install.sh --all

# Preview without installing
./install.sh --dry-run
```

Supported platforms: Claude Code, GitHub Copilot, VS Code Copilot, Cursor, Windsurf, Cline, Gemini CLI, Goose, OpenCode, Codex CLI, Roo Code, Kilo Code, Pi, and 10+ others.

### After Installation

Open a new agent session and use:

```
/bql-query-skill How much did I spend on food last month?
```

Or ask naturally: *"Query my Beancount ledger for restaurant expenses in Q1"*

---

## Objective

Build a production-grade Beancount Query Language (BQL / BeanQuery) skill capable of answering real-world personal finance questions against previously unseen Beancount ledgers.

The goal is NOT to summarize documentation.

The goal is to create a continuously improving system that:

1. Learns BQL from documentation, source code, examples, and real-world ledgers.
2. Maps natural language financial questions into correct BQL queries.
3. Executes and validates those queries.
4. Learns from failures.
5. Generalizes to unseen ledgers.
6. Achieves stable performance through automated evaluation loops.

---

# High-Level Architecture

```text
                 ┌────────────────────┐
                 │ Agent 1            │
                 │ Corpus Builder     │
                 └─────────┬──────────┘
                           │
                           ▼
                Training / Holdout Corpus
                           │
                           ▼
                 ┌────────────────────┐
                 │ Agent 2            │
                 │ Skill Builder      │
                 └─────────┬──────────┘
                           │
                           ▼
                      BQL Skill
                           │
                           ▼
                 ┌────────────────────┐
                 │ Agent 3            │
                 │ Independent Auditor│
                 └─────────┬──────────┘
                           │
                     Failure Reports
                           │
                           ▼
                 ┌────────────────────┐
                 │ Agent 4            │
                 │ Adversarial User   │
                 └─────────┬──────────┘
                           │
                 Hard Test Cases
                           │
                           ▼
                     Agent 2 Loop
```

---

# Core Design Principles

## Principle 1: Artifact-Based Communication

Agents must communicate through repository artifacts.

Do NOT rely on chat history.

All communication must happen through:

* Markdown reports
* YAML files
* JSON files
* Pull requests
* GitHub issues
* GitHub project items

Every agent should be reproducible from repository state alone.

---

## Principle 2: Evaluation Over Memorization

The system must optimize for:

```text
Natural Language
    ↓
Intent Understanding
    ↓
Accounting Concept Mapping
    ↓
BQL Generation
    ↓
Execution
    ↓
Correct Result
```

The evaluator should compare:

```text
Generated Result
vs
Expected Result
```

NOT:

```text
Generated Query
vs
Expected Query
```

Multiple BQL queries may be valid.

Correctness is determined by output.

---

## Principle 3: Holdout Validation

Agent 2 must never train against the entire corpus.

Separate:

```text
corpus/train/
```

from:

```text
corpus/holdout/
```

Holdout data is reserved for evaluation.

---

# Repository Structure

```text
repository/
│
├── corpus/
│   ├── train/
│   ├── holdout/
│   ├── repositories/
│   ├── ledgers/
│   ├── synthetic/
│   └── metadata/
│
├── benchmark/
│   ├── questions/
│   ├── expected_results/
│   ├── categories/
│   └── evaluation_runs/
│
├── skill/
│   ├── prompt.md
│   ├── knowledge_base/
│   ├── query_patterns/
│   ├── ontology/
│   └── repair_rules/
│
├── reports/
│   ├── auditor/
│   ├── failures/
│   ├── regressions/
│   └── coverage/
│
├── automation/
│   ├── agent1/
│   ├── agent2/
│   ├── agent3/
│   └── agent4/
│
└── docs/
```

---

# Agent 1 — Corpus Builder

## Mission

Continuously discover, collect, normalize, and catalog Beancount data sources.

Agent 1 never writes the BQL skill.

Agent 1 only produces datasets.

---

## Sources

### Official Sources

* https://github.com/beancount/beanquery
* https://github.com/beancount/beancount
* https://github.com/beancount/beancount/tree/master/examples
* https://beancount.io/docs/Basics/beancount-query-language
* https://beancount.github.io/docs/

### Fava Examples

* https://fava.pythonanywhere.com/example-beancount-file/
* https://fava.pythonanywhere.com/example-beancount-file/income_statement/

### Community Sources

Search GitHub for:

* *.bean
* *.beancount
* beanquery
* beancount
* fava

Search:

* PlaintextAccounting repositories
* Beancount issue trackers
* BeanQuery issue trackers
* Fava issue trackers
* Reddit discussions
* Blog posts

---

## Outputs

### Ledger Corpus

Collect:

* personal ledgers
* investment ledgers
* crypto ledgers
* rental property ledgers
* business ledgers
* multi-currency ledgers

---

### Repository Catalog

For every repository extract:

```yaml
repo:
accounts:
currencies:
commodities:
tags:
links:
metadata_fields:
investment_usage:
multi_currency:
```

---

### Query Corpus

Collect:

```yaml
question:
query:
source:
notes:
```

---

### Ground Truth Corpus

Build:

```yaml
id:
ledger:
question:
expected_result:
category:
difficulty:
```

---

# Agent 2 — Skill Builder

## Mission

Create and continuously improve the BQL skill.

---

## Inputs

* Official documentation
* Source code
* Query corpus
* Ledger corpus
* Auditor reports
* Failure reports
* Adversarial reports

---

## Outputs

### Primary Skill

```text
skill/prompt.md
```

---

### Knowledge Base

Extract:

* grammar
* syntax
* functions
* operators
* clauses
* aggregation
* inventory handling
* account hierarchies
* metadata handling
* commodity handling
* pricing semantics

---

### Personal Finance Ontology

Map:

```text
Net Worth
→ Assets - Liabilities

Savings Rate
→ Income vs Expenses

Portfolio Allocation
→ Investment Accounts

Cash Flow
→ Inflows / Outflows

Burn Rate
→ Expenses over Time
```

---

### Query Pattern Library

Create:

```yaml
intent:
question_examples:
query_template:
required_assumptions:
output_shape:
```

Examples:

* monthly spending
* net worth
* income statement
* cash flow
* portfolio allocation
* capital gains
* dividends
* subscriptions
* recurring expenses

---

### Repair Rules

Handle:

* syntax errors
* unknown functions
* account hierarchy mistakes
* inventory mistakes
* cost basis mistakes
* pricing mistakes
* date filtering mistakes
* multi-currency mistakes

---

### Self-Improvement Workflow

When failures occur:

1. Categorize failure.
2. Find supporting documentation.
3. Search examples.
4. Search source code.
5. Update prompt.
6. Add regression test.
7. Re-run benchmark.

---

# Agent 3 — Independent Auditor

## Mission

Evaluate the skill objectively.

Agent 3 must not help improve the skill directly.

Its only responsibility is scoring.

---

## Inputs

* skill
* ledger
* benchmark question

---

## Hidden Inputs

```yaml
expected_result:
```

---

## Evaluation Process

1. Load ledger.
2. Ask question.
3. Let skill generate BQL.
4. Execute BQL.
5. Compare actual result against expected result.
6. Generate evaluation report.

---

## Failure Categories

### Syntax

* invalid query

### Semantic

* wrong accounts

### Aggregation

* incorrect grouping

### Inventory

* units vs cost basis confusion

### Pricing

* market value confusion

### Multi-Currency

* FX handling errors

### Time

* date filtering errors

### Metadata

* tag/link filtering failures

---

## Evaluation Output

```yaml
test_id:
pass:
category:
failure_type:
severity:
explanation:
```

---

# Agent 4 — Adversarial User

## Mission

Continuously discover weaknesses.

---

## Responsibilities

Generate difficult questions.

Focus on:

### Ambiguity

Examples:

```text
How much did I spend on food?

What counts as food?
```

---

### Investments

```text
How much AAPL do I own?

Shares?
Cost basis?
Market value?
```

---

### Multi-Currency

```text
What is my net worth?
```

Questions:

* in which currency?
* cost?
* market value?

---

### Tax

```text
What was my taxable income?
```

---

### Date Logic

```text
Last quarter
```

Calendar quarter?

Rolling quarter?

---

### Metadata

Questions involving:

* tags
* links
* metadata fields

---

## Output

```yaml
question:
category:
difficulty:
reasoning:
```

---

# Benchmark Design

The benchmark is the central artifact.

---

## Categories

### Spending Analysis

* category spending
* merchant spending
* recurring expenses
* subscriptions

---

### Budgeting

* monthly trends
* budget vs actual
* overspending

---

### Cash Flow

* income
* expenses
* burn rate

---

### Net Worth

* asset tracking
* liability tracking

---

### Investments

* allocation
* dividends
* gains
* performance

---

### Taxes

* taxable income
* deductions
* gains

---

### Multi-Currency

* FX conversion
* mixed portfolios

---

### Advanced

* metadata
* tags
* links
* custom fields

---

# Benchmark Example

```yaml
id: 001

ledger: sample.bean

question: >
  What were my restaurant expenses
  during the last quarter?

expected_result:
  total: 324.50

category: spending

difficulty: medium
```

Important:

Never store expected query.

Only store expected result.

---

# Scoring Framework

Do not use a single score.

Track category scores.

Example:

```yaml
spending: 95
budgeting: 94
cashflow: 96
networth: 97
investments: 88
tax: 85
multicurrency: 82
metadata: 91
```

---

# Regression Tracking

Store every evaluation run.

```text
benchmark/evaluation_runs/
```

Example:

```yaml
run:
timestamp:
overall:
spending:
budgeting:
cashflow:
networth:
investments:
multicurrency:
tax:
metadata:
```

Never accept improvements that create major regressions elsewhere.

---

# GitHub Project Workflow

Recommended columns:

```text
Inbox

Corpus Collection

Corpus Review

Benchmark Creation

Ready For Evaluation

Evaluation Running

Failed

Skill Improvement

Ready For Retest

Passed

Archived
```

---

# Artifact Templates

## Failure Report

```yaml
question:

ledger:

generated_query:

generated_result:

expected_result:

failure_type:

category:

severity:

recommended_area:
```

---

## Skill Improvement Report

```yaml
failure_reference:

root_cause:

documentation_found:

examples_found:

prompt_changes:

new_tests_added:
```

---

## Coverage Report

```yaml
category:

coverage_percent:

examples:

gaps:

recommendations:
```

---

# Success Criteria

The project is considered mature when:

```yaml
overall_score: >=95

spending: >=95
budgeting: >=95
cashflow: >=95
networth: >=95

investments: >=90
multicurrency: >=90
tax: >=90

metadata: >=90
```

and

```yaml
consecutive_runs: >=3
regression_rate: <2%
```

and

All holdout datasets continue to pass.

---

# Final Deliverables

## 1. Corpus

* Real-world ledgers
* Synthetic ledgers
* Holdout ledgers
* Repository catalog

## 2. Benchmark

* 500–1000+ finance questions
* Expected results
* Difficulty labels
* Category labels

## 3. BQL Skill

* Production prompt
* Knowledge base
* Query pattern library
* Repair procedures

## 4. Evaluation Framework

* Automated testing
* Category scoring
* Regression detection
* Coverage reports

## 5. Research Reports

* Failure analysis
* Gap analysis
* Coverage analysis
* Improvement history

The final outcome should be a reproducible research system that continuously improves BQL competence and validates performance on previously unseen Beancount ledgers.
