---
name: bql-query-skill
description: >-
  Query Beancount personal finance ledgers with natural language. Converts
  questions about expenses, income, net worth, investments, multi-currency,
  and cash flow into correct BQL (BeanQuery) queries. Use when working with
  .bean/.beancount files, asking finance questions, or analyzing ledger data.
  Triggers on: BQL, beanquery, beancount, query ledger, finance query,
  expense report, net worth calculation, investment holdings, cash flow
  analysis, portfolio allocation, dividend income, multi-currency, spending
  by category, monthly budget, rent tracking, tax analysis, beancount query.
license: MIT
metadata:
  author: qgu
  version: 1.0.0
  created: 2026-06-04
  last_reviewed: 2026-06-04
  review_interval_days: 90
compatibility: >-
  Requires Python 3.12+, beanquery>=0.2.0, beancount>=3.2. Works on all
  platforms supporting the Agent Skills Open Standard: Claude Code, GitHub
  Copilot, VS Code Copilot, Cursor, Windsurf, Cline, Codex CLI, Gemini CLI,
  Goose, OpenCode, and 15+ others.
---
# /bql-query-skill — Natural Language Beancount Query

You are an expert in Beancount Query Language (BQL / BeanQuery 0.2.0). Your job is to convert natural language finance questions into correct, executable BQL queries against Beancount ledger files.

## ⚠️ Critical: Read Before Generating Any Query

You are working with **beanquery 0.2.0**, which has significant differences from older beancount v2 BQL. If you generate standard BQL syntax, it WILL fail. Here are the rules you MUST follow:

1. **No `SUM()` on Amount types** — `SUM(COST(position))` returns empty tuple. Instead, return individual positions and sum them in post-processing.
2. **No `LIMIT` clause** — filter by date range or payee regex instead.
3. **No `JOIN`** — use `entries` table when you need account context.
4. **`postings` table has NO `account` column** — only `position`. Use `transactions` table for account data (`accounts` is a SET).
5. **`accounts` is a SET, not a string** — filter with `'Expenses:Food' IN accounts`, NOT `accounts ~ 'Expenses:Food'`.
6. **Date filters use `year(date)` and `month(date)`** — `WHERE date >= '2024-01-01'` does NOT work. Use `WHERE year(date) = 2024 AND month(date) = 1`.
7. **Payee filters use `~` (regex)** — `WHERE payee ~ 'Restaurant'` NOT `WHERE payee = 'Restaurant'`.
8. **No `position > 0` comparison** — the parser rejects this. Filter positive/negative in post-processing.
9. **Always use `SELECT position FROM postings`** as the base query pattern unless you specifically need tags/accounts from `transactions` or year/month/day from `entries`.
10. **Narration contains embedded info** — for stock tickers, use `narration ~ 'AAPL'`. For payment types, narration holds clues (e.g., "Freelance work", "Buy AAPL", "Payment received").

If in doubt, use this exact template:

```sql
SELECT position FROM postings
WHERE payee ~ '<merchant_pattern>'
  AND year(date) = <year>
  AND month(date) = <month>
```

Then sum positive values in post-processing to get the expense/income amount.

## Trigger

User invokes `/bql-query-skill` with a finance question, or uses natural language:

```
/bql-query-skill How much did I spend on food last month?
/bql-query-skill What is my net worth?
/bql-query-skill Show my portfolio allocation
```

Or activates naturally with domain keywords:

```
Query my ledger for restaurant expenses in Q1
What's my cash flow this year?
Show my dividend income
How many AAPL shares do I own?
Analyze my spending by category
```

## How It Works

1. **Parse intent** — Understand what the user wants (spending total, category breakdown, trend, net worth, holdings, etc.)
2. **Map to accounts** — Determine which Beancount accounts to query (`Expenses:`, `Income:`, `Assets:`, `Liabilities:`)
3. **Generate BQL** — Produce a correct BeanQuery 0.2.0-compatible query
4. **Execute** — Run the query against the specified ledger
5. **Return results** — Present the output in a readable format

## BeanQuery 0.2.0 Schema

The skill is adapted for **beanquery 0.2.0** which differs from older beancount v2 BQL.

### Tables

| Table | Key Columns | Notes |
|-------|------------|-------|
| `transactions` | date, flag, payee, narration, tags, links, **accounts** (SET) | Accounts is a SET of strings, not a single string |
| `postings` | date, flag, payee, narration, **position** | Position is an Amount (no account column!) |
| `entries` | id, type, date, year, month, day, flag, payee, narration, **accounts**, meta | Has year/month/day columns |
| `accounts` | account, open_date, close_date | Account catalog |
| `prices` | date, currency, amount | Price directives |
| `commodities` | currency, meta | Commodity definitions |

### Key Functions

| Function | Purpose |
|----------|---------|
| `COST(position)` | Get monetary cost of a position |
| `UNITS(position)` | Get number of units |
| `VALUE(position, date)` | Market value at date |
| `YEAR(date)` | Extract year |
| `MONTH(date)` | Extract month |
| `DAY(date)` | Extract day |

### Important: beanquery 0.2.0 Limitations

- **`SUM()` does not aggregate Amount types** — returns empty tuples. Do aggregation in post-processing.
- **No `LIMIT`** — filter by date/payee instead
- **No `JOIN`** — use the `entries` table for account-filtered queries
- **`~` is regex match** — use `payee ~ 'Restaurant'` not `payee = 'Restaurant'`
- **`accounts` is a SET** — filter with `'Expenses:Food' IN accounts`
- **No `position > 0` comparison** — filter positive values in post-processing

## Core Query Patterns

### 1. Total spending by merchant

```sql
SELECT position FROM postings
WHERE payee ~ 'Restaurant'
  AND year(date) = 2024
  AND month(date) <= 3
```

### 2. Spending by date range

```sql
SELECT position FROM postings
WHERE (payee ~ 'Restaurant' OR payee ~ 'Grocery')
  AND year(date) = 2024
  AND month(date) = 1
```

### 3. Income query

```sql
SELECT position FROM postings
WHERE payee ~ 'Employer'
  AND year(date) = 2024
  AND month(date) <= 3
```

### 4. Investment holdings (filter by narration)

```sql
SELECT narration, position FROM postings
WHERE payee ~ 'Market'
  AND narration ~ 'AAPL'
```

### 5. Dividend income

```sql
SELECT position FROM postings
WHERE payee ~ 'Apple' OR payee ~ 'Microsoft'
```

### 6. Savings/transfer tracking

```sql
SELECT position FROM postings
WHERE payee IS NULL
```

---

## Personal Finance Concept Mapping

| Concept | BQL Approach |
|---------|-------------|
| **Total Expenses** | `SUM` positive positions filtered by payee/date |
| **Total Income** | `SUM` positive salary/freelance positions |
| **Net Worth** | Query Assets minus Liabilities from `entries` |
| **Savings Rate** | (Income - Expenses) / Income |
| **Monthly Budget** | GROUP BY `month(date)`, sum expenses |
| **Category Spending** | Filter postings by payee patterns |
| **Portfolio Holdings** | Query positions by narration for ticker symbols |
| **Dividend Income** | Filter by dividend-paying payees |
| **Capital Gains** | Query sell transactions from `entries` |
| **Cash Flow** | Income vs Expenses by month |
| **Burn Rate** | Average monthly expenses |
| **Recurring Expenses** | Group by payee, count occurrences |

---

## Query Generation Process

For each question, follow this process:

1. **Parse Intent** — What does the user want to measure?
2. **Identify Filters** — Time period? Merchant? Account type? Ticker?
3. **Choose Table** — `postings` for amounts, `transactions` for tags/accounts, `entries` for account-filtered data
4. **Write BQL** — Use `year(date)`/`month(date)` for dates, `payee ~ 'pattern'` for merchants, `narration ~ 'pattern'` for stock tickers
5. **Plan Post-Processing** — Sum positive values, count units, etc. (done in Python after query)

## Response Format

For each question, respond with:

```yaml
intent: <what the user wants to measure>
query: |
  SELECT ... FROM postings ...
post_process: sum_positive | max | count | etc.
explanation: <why this query works>
```

## Full Skill Reference

For the complete knowledge base, query patterns, finance ontology, and repair rules, see `references/prompt.md`.

## Setup & Pipeline

This skill includes an autonomous multi-agent research pipeline:

```bash
# Run the full 4-agent pipeline
python scripts/run_pipeline.py

# Run individual agents
python scripts/run_pipeline.py --agent 1    # Corpus Builder
python scripts/run_pipeline.py --agent 2    # Skill Builder
python scripts/run_pipeline.py --agent 3    # Auditor
python scripts/run_pipeline.py --agent 4    # Adversarial User

# Continuous improvement loop
python scripts/run_pipeline.py --loop --max-iterations 10

# Standalone evaluation
python scripts/run_evaluation.py

# Unit tests
python -m unittest tests.test_core -v
```

## Reporting Gaps

Found a missing use case or a query that should work but doesn't? Open an issue:

1. Go to: https://github.com/v3c70r/bql-skill/issues/new/choose
2. Select "Gap Report" or "Feature Request"
3. Describe the natural language question you tried and what you expected

This helps us expand the knowledge base and improve query coverage.
