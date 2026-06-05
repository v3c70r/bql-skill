# bql-query-skill

Natural Language Beancount Query Language (BQL) skill. Converts finance questions into correct BeanQuery 0.2.0 queries and executes them against Beancount ledger files.

## Activation

This skill activates when the user asks questions about Beancount ledger data, personal finance queries, or BQL execution. Natural language triggers include:

- "Query my ledger for..."
- "How much did I spend on..."
- "What is my net worth?"
- "Show my investment holdings"
- "Analyze my cash flow"
- "BQL query for..."
- "Beancount query..."

Or use the explicit command: `/bql-query-skill <question>`

## Usage

The skill works in two modes:

### 1. Direct Query Mode
User provides a natural language question + a Beancount ledger path. The skill generates and executes the BQL query:

```
User: "How much did I spend on restaurants last quarter? Ledger is at ~/finances/2024.bean"
```

### 2. Pipeline Mode
User runs the multi-agent research pipeline to build the skill knowledge base, evaluate against benchmarks, and improve:

```bash
python scripts/run_pipeline.py
```

## BeanQuery 0.2.0 Notes

- Use `postings` table for amount queries (no account column)
- Use `transactions` table for account/tag filtering (accounts is a SET)
- Use `year(date)`, `month(date)` for date filtering
- Use `payee ~ 'pattern'` for merchant matching
- `SUM()` does not aggregate Amount types — do aggregation in post-processing
- No `LIMIT`, no `JOIN`

## Key Files

- `SKILL.md` — Full skill definition and query patterns
- `references/prompt.md` — Complete BQL knowledge base (10.5K chars)
- `references/knowledge_base/` — Tables, functions, operators reference
- `references/query_patterns/` — 12 reusable query templates
- `references/ontology/` — Personal finance concept → BQL mappings
- `references/repair_rules/` — Error recovery rules by category
- `scripts/run_pipeline.py` — Full 4-agent pipeline orchestrator
- `scripts/run_evaluation.py` — Standalone evaluation runner
- `corpus/synthetic/` — 6 synthetic Beancount ledgers

## Reporting Issues

Found a gap? Open an issue at: https://github.com/v3c70r/bql-skill/issues/new/choose
