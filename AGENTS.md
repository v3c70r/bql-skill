# bql-query-skill

Natural Language Beancount Query Language (BQL) skill. Converts finance questions into correct BeanQuery 0.2.0 queries and executes them against Beancount ledger files.

## ⚠️ Critical: BeanQuery 0.2.0 Rules

This skill targets **beanquery 0.2.0**, which differs significantly from older beancount v2 BQL. You MUST follow these rules:

1. **No `SUM()` on Amount types** — `SUM(COST(position))` returns empty tuple. Sum in post-processing.
2. **No `LIMIT`** — filter by date/payee instead.
3. **No `JOIN`** — use `entries` table for account context.
4. **`postings` has NO `account` column** — only `position`. `transactions` has `accounts` as a SET.
5. **`accounts` is a SET** — filter with `'Expenses:Food' IN accounts`.
6. **Date filters:** `year(date) = 2024 AND month(date) = 1` — string comparisons fail.
7. **Payee:** `payee ~ 'Restaurant'` (regex), not `payee = '...'`.
8. **No `position > 0`** — parse error. Filter sign in post-processing.
9. **Base query:** `SELECT position FROM postings WHERE ...`
10. **Narration for tickers:** `narration ~ 'AAPL'` for stock filtering.

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

## Response Format

Always respond with:

```yaml
intent: <what the user wants>
query: |
  SELECT position FROM postings WHERE ...
post_process: sum_positive | max | count | avg
explanation: <why this query works>
```

## Key Files

- `SKILL.md` — Full skill definition with all query patterns
- `references/prompt.md` — Complete BQL knowledge base (10.5K chars)
- `references/knowledge_base/` — Tables, functions, operators reference
- `references/query_patterns/` — 12 reusable query templates
- `references/ontology/` — Personal finance concept → BQL mappings
- `references/repair_rules/` — Error recovery rules by category
- `scripts/run_pipeline.py` — Full 4-agent pipeline orchestrator
- `scripts/run_evaluation.py` — Standalone evaluation runner
- `corpus/synthetic/` — 6 synthetic Beancount ledgers

## Pipeline Commands

```bash
python run_pipeline.py                          # Full pipeline
python run_pipeline.py --agent 3                # Auditor only
python run_pipeline.py --loop --max-iterations 10  # Improvement loop
python run_evaluation.py                        # Standalone eval
python -m unittest tests.test_core -v           # Unit tests
```

## Reporting Issues

Found a gap? Open an issue at: https://github.com/v3c70r/bql-skill/issues/new/choose
