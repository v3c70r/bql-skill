---
name: bql-skill
description: Beancount Query Language (BQL) skill for querying personal finance ledgers. Converts natural language questions into BQL queries, executes them against Beancount ledgers, evaluates results, and continuously improves through an autonomous multi-agent research loop. Use when working with .bean/.beancount files, asking finance questions about expenses/income/investments/net worth, or running the BQL research pipeline.
license: MIT
compatibility: Requires Python 3.12+, beanquery>=0.2.0, beancount>=3.2
---

# BQL (BeanQuery) Skill

Query Beancount personal finance ledgers using natural language. This skill converts questions like *"How much did I spend on food last month?"* into correct BQL queries and executes them against your Beancount files.

## Quick Start

### 1. Install Dependencies

```bash
pip install beancount beanquery pyyaml
```

### 2. Run the Full Pipeline

```bash
cd /path/to/bql-skill
python run_pipeline.py
```

This runs all 4 agents:
- **Agent 1 — Corpus Builder**: Generates synthetic ledgers, extracts metadata, builds ground truth
- **Agent 2 — Skill Builder**: Builds the BQL skill prompt, knowledge base, query patterns, and repair rules
- **Agent 3 — Auditor**: Evaluates the skill against all benchmark questions
- **Agent 4 — Adversarial User**: Generates challenging test cases to find weaknesses

### 3. Run Individual Agents

```bash
python run_pipeline.py --agent 1    # Corpus Builder only
python run_pipeline.py --agent 2    # Skill Builder only
python run_pipeline.py --agent 3    # Auditor only (evaluation)
python run_pipeline.py --agent 4    # Adversarial User only
```

### 4. Continuous Improvement Loop

```bash
python run_pipeline.py --loop --max-iterations 10
```

Runs the Auditor → Skill Builder → Auditor loop, learning from failures each iteration.

### 5. Standalone Evaluation

```bash
python run_evaluation.py
```

### 6. Run Tests

```bash
python -m unittest tests.test_core -v
```

## Using the Skill Prompt

The primary skill prompt is at `skill/prompt.md`. Load it when generating BQL queries from natural language questions. It contains:

- **BQL Syntax Reference**: Tables, columns, functions, operators
- **Query Patterns**: 12 reusable templates for common finance questions
- **Finance Ontology**: 14 concepts mapped to BQL (net worth → Assets - Liabilities)
- **Common Mistakes**: 8 error categories with fixes
- **Repair Rules**: 21 rules for syntax, semantic, aggregation, and other errors

## Repository Structure

```
bql-skill/
├── skill/prompt.md              # Primary BQL skill prompt
├── skill/knowledge_base/        # BQL reference (tables, functions, operators)
├── skill/query_patterns/        # 12 reusable BQL query templates
├── skill/ontology/              # Personal finance concept → BQL mappings
├── skill/repair_rules/          # Error recovery rules by category
├── corpus/synthetic/            # 6 synthetic Beancount ledgers
├── benchmark/questions/         # 19 benchmark questions
├── benchmark/expected_results/  # Expected results per question
├── automation/agent1/           # Corpus Builder
├── automation/agent2/           # Skill Builder
├── automation/agent3/           # Independent Auditor
├── automation/agent4/           # Adversarial User
├── automation/core/             # Shared library (BQL executor, evaluator)
└── tests/                       # 34 unit tests
```

## BeanQuery 0.2.0 Schema

The skill is adapted for beanquery 0.2.0 which differs from older beancount v2 BQL:

| Table | Key Columns |
|-------|------------|
| `transactions` | date, flag, payee, narration, tags, links, accounts (SET) |
| `postings` | date, flag, payee, narration, position |
| `entries` | id, type, date, year, month, day, flag, payee, narration, accounts, meta |
| `accounts` | account, open_date, close_date |
| `prices` | date, currency, amount |
| `commodities` | currency, meta |

**Note:** `SUM()` does not aggregate Amount types in this version. The system handles aggregation in Python post-processing.

## Evaluation Framework

The benchmark evaluates the skill across 8 categories:

| Category | Questions | Target Score |
|----------|-----------|-------------|
| spending | 6 | ≥95% |
| budgeting | 2 | ≥95% |
| cashflow | 3 | ≥95% |
| networth | 1 | ≥95% |
| investments | 4 | ≥90% |
| multicurrency | 3 | ≥90% |
| tax | 0 | ≥90% |
| metadata | 0 | ≥90% |

## Success Criteria

The project reaches maturity when:
- Overall score ≥ 95%
- All category scores meet targets
- 3+ consecutive runs above 95%
- Regression rate < 2%
- All holdout datasets pass
