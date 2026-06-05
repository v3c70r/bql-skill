# BQL Skill — Natural Language Beancount Query

Convert natural language finance questions into BQL (BeanQuery) queries and execute them against Beancount ledger files. Cross-platform agent skill with an autonomous 4-agent improvement pipeline.

## What This Is

A reusable agent skill that answers questions like:

> *"How much did I spend on food last month?"*
> *"What is my net worth?"*
> *"How many AAPL shares do I own?"*
> *"Show my cash flow this year"*

The skill generates correct BQL queries, executes them, and returns results. It ships with 6 synthetic ledgers, 19 benchmark questions, a full knowledge base, and a pipeline that continuously improves itself.

**Built for beanquery 0.2.0** — handles all its schema quirks (no SUM on Amounts, no LIMIT, no JOIN, SET-type accounts column).

---

## Quick Install (Any Platform)

```bash
git clone https://github.com/v3c70r/bql-skill.git
cd bql-skill

# Auto-detect your platform and install
./install.sh

# Or pick a specific platform
./install.sh --platform claude      # Claude Code
./install.sh --platform cursor      # Cursor
./install.sh --platform copilot     # GitHub Copilot
./install.sh --platform windsurf    # Windsurf

# Install to all detected platforms
./install.sh --all

# Preview what would happen
./install.sh --dry-run
```

**Supported platforms:** Claude Code, GitHub Copilot, VS Code Copilot, Cursor, Windsurf, Cline, Gemini CLI, Goose, OpenCode, Codex CLI, Roo Code, Kilo Code, Pi, and 10+ others.

---

## How to Use

### As an End User (after installing)

Open a new agent session and ask a question about your Beancount ledger:

```
/bql-query-skill How much did I spend on restaurants last quarter?
```

Or use natural language — the skill auto-activates when you mention BQL, beancount, ledger queries, or finance questions:

```
Query my ledger at ~/finances/2024.bean — what were my top 5 expenses?
Show my portfolio allocation from my beancount file
```

The skill will:
1. Parse your intent
2. Generate the correct BQL query for beanquery 0.2.0
3. Execute it against your ledger
4. Return the results

### As a Developer (running the pipeline)

```bash
# Install dependencies
pip install beancount beanquery pyyaml

# Run the full 4-agent pipeline
python run_pipeline.py

# Run individual agents
python run_pipeline.py --agent 1    # Corpus Builder — generates ledgers, ground truth
python run_pipeline.py --agent 2    # Skill Builder — builds knowledge base, patterns
python run_pipeline.py --agent 3    # Auditor — evaluates against benchmarks
python run_pipeline.py --agent 4    # Adversarial User — finds weaknesses

# Continuous improvement loop (Agent 3 ↔ Agent 2)
python run_pipeline.py --loop --max-iterations 10

# Standalone evaluation with real beanquery execution
python run_evaluation.py

# Unit tests
python -m unittest tests.test_core -v
```

---

## Current Status

| Metric | Value |
|--------|-------|
| **Benchmark questions** | 19 across 6 categories |
| **Execution success** | 100% (19/19) |
| **Unit tests** | 34 (all passing) |
| **Synthetic ledgers** | 6 (personal, investment, multi-currency, business, rental, crypto) |
| **Query patterns** | 12 reusable templates |
| **Finance concepts** | 14 mapped to BQL |
| **Repair rules** | 21 across 8 error categories |
| **Adversarial questions** | 31 designed to expose weaknesses |
| **Category scores** | 100% spending, budgeting, cashflow, networth, investments, multicurrency |

---

## Key Files (for an Agent Reading This)

When you need to work with this skill, here is where everything lives:

### Entry Points
| File | Purpose |
|------|---------|
| `SKILL.md` | Cross-platform skill definition. Starts with `# /bql-query-skill`. This is what agents load first. |
| `AGENTS.md` | Companion instruction file for tools that prefer AGENTS.md over SKILL.md. |
| `install.sh` | Cross-platform installer. Run `./install.sh --dry-run` to see what it does. |

### Skill Knowledge (load these on demand)
| Path | Contents |
|------|----------|
| `references/prompt.md` | Full BQL skill prompt (10.5K chars). BeanQuery 0.2.0 schema, functions, operators. |
| `references/knowledge_base/` | BQL reference: 25 keywords, 9 tables, 22 functions, 16 operators. YAML + JSON. |
| `references/query_patterns/` | 12 reusable BQL query templates with example questions. |
| `references/ontology/` | 14 personal finance concepts mapped to BQL (net worth, savings rate, cash flow, etc.). |
| `references/repair_rules/` | 21 error recovery rules: syntax, semantic, aggregation, inventory, pricing, multi-currency, date, metadata errors. |

### Pipeline Code
| Path | Purpose |
|------|---------|
| `run_pipeline.py` | Main orchestrator. Run `python run_pipeline.py` for full pipeline. |
| `run_evaluation.py` | Standalone evaluation with real beanquery execution. Run to see scores. |
| `automation/core/bql_executor.py` | BQL query execution — wraps beanquery Python API, handles Position/Amount serialization. |
| `automation/core/benchmark.py` | Benchmark system, evaluator, scoring, regression detection. |
| `automation/agent1/corpus_builder.py` | Agent 1 — generates synthetic ledgers, extracts metadata, builds ground truth. |
| `automation/agent2/skill_builder.py` | Agent 2 — builds skill prompt, knowledge base, query patterns, repair rules. |
| `automation/agent3/auditor.py` | Agent 3 — evaluates skill, scores by category, detects regressions. |
| `automation/agent4/adversarial_user.py` | Agent 4 — generates adversarial questions to find weaknesses. |

### Data Artifacts
| Path | Contents |
|------|----------|
| `corpus/synthetic/` | 6 Beancount ledger files (`simple_personal.bean`, `investment.bean`, `multicurrency.bean`, `business.bean`, `rental_property.bean`, `crypto.bean`) |
| `corpus/train/` | Training ground truth (15 records) |
| `corpus/holdout/` | Holdout ground truth (4 records, never used for training) |
| `benchmark/questions/` | 19 benchmark questions (YAML) |
| `benchmark/expected_results/` | Expected results per question |
| `benchmark/evaluation_runs/` | Historical evaluation run data |
| `tests/test_core.py` | 34 unit tests for BQL executor, normalization, comparison |

### GitHub Integration
| File | Purpose |
|------|---------|
| `.github/ISSUE_TEMPLATE/gap-report.md` | Template for users to report missing BQL use cases |
| `.github/ISSUE_TEMPLATE/feature-request.md` | Template for feature suggestions |

---

## Architecture

The system uses 4 agents that communicate through repository artifacts (files, not chat):

```
Agent 1 (Corpus Builder)     →  Synthetic ledgers, ground truth, query corpus
Agent 2 (Skill Builder)      →  skill/prompt.md, knowledge base, repair rules
Agent 3 (Auditor)            →  Evaluation reports, category scores, regression flags
Agent 4 (Adversarial User)   →  Hard test cases exposing weaknesses
                                  ↓
                            Agent 2 Loop  (learn from failures)
```

### BeanQuery 0.2.0 Adaptations

This version of beanquery differs significantly from classic beancount v2 BQL:

- **`SUM()` does not aggregate Amount types** — returns empty tuples. Aggregation is done in Python post-processing.
- **No `LIMIT`** — filter by date ranges or payee patterns instead.
- **No `JOIN`** — use the `entries` table when you need account-filtered data.
- **`accounts` column is a SET** — filter with `'Expenses:Food' IN accounts`, not regex.
- **`postings` table has no account column** — only `position` (Amount). Use `transactions` or `entries` for account context.
- **`position > 0` causes a parse error** — filter positive/negative in Python post-processing.
- **Date comparisons need `year(date)`/`month(date)`** — string comparisons like `date >= '2024-01-01'` don't work.

### Evaluation Approach

The evaluator does NOT compare generated queries against expected queries. It compares **results**:

1. Execute the BQL query against the ledger
2. Extract numeric values (handling Position/Amount types with currency info)
3. Compare against expected result (flat dict like `{"total": 236.8}`)
4. Score by category

---

## Reporting Gaps

Found a missing use case or a query that should work but doesn't?

1. Go to: https://github.com/v3c70r/bql-skill/issues/new/choose
2. Select **"Gap Report"**
3. Describe the natural language question you tried and the expected result

This feeds back into Agent 4 (adversarial testing) and Agent 2 (skill improvement).

---

## Success Criteria

The project reaches maturity when:
- Overall score ≥ 95% across 3 consecutive runs
- All category scores meet targets (spending/budgeting/cashflow/networth ≥ 95%, investments/multicurrency/tax/metadata ≥ 90%)
- Regression rate < 2%
- All holdout datasets pass

---

## License

MIT
