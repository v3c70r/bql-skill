"""
Agent 2 — Skill Builder

Creates and continuously improves the BQL skill.

Inputs:
- Official documentation
- Source code
- Query corpus
- Ledger corpus
- Auditor reports
- Failure reports
- Adversarial reports

Outputs:
- skill/prompt.md — primary skill prompt
- skill/knowledge_base/ — extracted BQL knowledge
- skill/query_patterns/ — reusable query templates
- skill/ontology/ — personal finance concept mapping
- skill/repair_rules/ — error recovery rules
"""

import json
import yaml
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class QueryPattern:
    """A reusable query pattern template."""
    intent: str
    question_examples: list[str] = field(default_factory=list)
    query_template: str = ""
    required_assumptions: list[str] = field(default_factory=list)
    output_shape: str = ""
    category: str = ""

    def to_yaml(self) -> str:
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)


@dataclass
class FinanceConcept:
    """A personal finance concept mapped to BQL constructs."""
    concept: str
    formula: str
    bql_pattern: str
    examples: list[str] = field(default_factory=list)

    def to_yaml(self) -> str:
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)


class SkillBuilder:
    """Agent 2 main class. Builds and improves the BQL skill."""

    # BQL Keywords and syntax reference
    BQL_KEYWORDS = [
        "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "LIMIT",
        "AND", "OR", "NOT", "AS", "ON", "IN", "JOIN",
        "SUM", "AVG", "COUNT", "MIN", "MAX",
        "COST", "UNITS", "VALUE", "CONVERT",
        "OPEN", "CLOSE", "CLEAR",
    ]

    # BQL Table-like data sources
    BQL_TABLES = {
        "transactions": "All postings with their transaction context. Columns: date, flag, payee, narration, account, position, balance, links, tags, meta",
        "balances": "Account balances. Columns: account, balance",
        "inventory": "Commodity holdings. Columns: account, position",
        "commodities": "Commodity definitions. Columns: commodity, meta",
        "accounts": "Account definitions. Columns: account, open_date, close_date, meta",
        "prices": "Price directives. Columns: date, commodity, price",
        "events": "Event directives. Columns: date, type, description",
        "notes": "Note directives. Columns: date, account, comment",
        "documents": "Document directives. Columns: date, account, filename",
    }

    # BQL Functions reference
    BQL_FUNCTIONS = {
        # Aggregation
        "SUM(expr)": "Sum of expression values",
        "AVG(expr)": "Average of expression values",
        "COUNT(expr)": "Count of non-null expression values",
        "MIN(expr)": "Minimum of expression values",
        "MAX(expr)": "Maximum of expression values",
        "FIRST(expr)": "First value in group",
        "LAST(expr)": "Last value in group",

        # Position/Inventory
        "COST(position)": "Get cost value of a position (base currency)",
        "UNITS(position)": "Get number of units in a position",
        "COST(sum(position))": "Total cost of aggregated positions",
        "UNITS(sum(position))": "Total units of aggregated positions",
        "VALUE(position, date)": "Market value at given date (requires prices)",

        # String matching
        "account ~ 'pattern'": "Account name matches regex pattern",
        "payee ~ 'pattern'": "Payee matches regex pattern",
        "narration ~ 'pattern'": "Narration matches regex pattern",

        # Date functions
        "YEAR(date)": "Extract year from date",
        "MONTH(date)": "Extract month from date",
        "DAY(date)": "Extract day from date",

        # Metadata
        "ANY_METADATA('key')": "Get any metadata value for key",
        "META('key')": "Get metadata value",
        "ENTRY_META('key')": "Get entry-level metadata",

        # Conversion
        "CONVERT(position, 'CUR')": "Convert position to target currency",
    }

    # BQL Operators
    BQL_OPERATORS = {
        "=": "Equality",
        "!=": "Inequality",
        "<": "Less than",
        "<=": "Less than or equal",
        ">": "Greater than",
        ">=": "Greater than or equal",
        "~": "Regex match",
        "!~": "Regex non-match",
        "AND": "Logical AND",
        "OR": "Logical OR",
        "NOT": "Logical NOT",
        "IN": "Value in list",
        "IS NULL": "Check for null",
        "IS NOT NULL": "Check for non-null",
        "BETWEEN": "Range check",
        "LIKE": "SQL-like pattern match",
    }

    def __init__(self, skill_dir: str | Path = None):
        if skill_dir is None:
            skill_dir = Path(__file__).resolve().parent.parent.parent / "skill"
        self.skill_dir = Path(skill_dir)
        self.kb_dir = self.skill_dir / "knowledge_base"
        self.patterns_dir = self.skill_dir / "query_patterns"
        self.ontology_dir = self.skill_dir / "ontology"
        self.repair_dir = self.skill_dir / "repair_rules"

        for d in [self.kb_dir, self.patterns_dir, self.ontology_dir, self.repair_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def build_skill_prompt(self) -> str:
        """Build the primary BQL skill prompt."""
        prompt = self._generate_prompt()
        prompt_path = self.skill_dir / "prompt.md"
        prompt_path.write_text(prompt)
        return prompt

    def _generate_prompt(self) -> str:
        """Generate the comprehensive BQL skill prompt."""
        return """# BQL (BeanQuery) Skill

You are an expert in Beancount Query Language (BQL). Your task is to convert natural language questions about personal finances into correct, executable BQL queries.

## Core Principles

1. **Generate BQL, NOT SQL**: BQL has its own syntax, tables, and functions. Do not use standard SQL.
2. **Understand the intent**: Before writing a query, identify what the user actually wants to measure.
3. **Map to accounting concepts**: Translate natural language to accounting terms (expenses, income, assets, liabilities).
4. **Use correct functions**: Use COST() for monetary values, UNITS() for share/unit counts.
5. **Account for hierarchy**: Beancount uses colon-separated account names (e.g., Expenses:Food:Restaurants).
6. **Validate output shape**: Make sure the query returns the right columns for the question.

---

## BQL Data Tables

The following tables are available in BQL queries. Use these as FROM sources.

| Table | Description | Key Columns |
|-------|-------------|-------------|
| **transactions** | All postings with transaction context | date, flag, payee, narration, account, position, balance, links, tags, meta |
| **balances** | Account balances | account, balance |
| **inventory** | Commodity holdings | account, position |
| **accounts** | Account definitions | account, open_date, close_date, meta |
| **prices** | Price directives | date, commodity, price |
| **commodities** | Commodity definitions | commodity, meta |
| **events** | Event directives | date, type, description |
| **notes** | Note directives | date, account, comment |

---

## Key Functions

### Position/Amount Functions

| Function | Purpose | Example |
|----------|---------|---------|
| `COST(position)` | Monetary cost of a position | Get amount spent in base currency |
| `UNITS(position)` | Number of units | Get share count |
| `VALUE(position, date)` | Market value at date | Get current market value |
| `COST(sum(position))` | Total cost after GROUP BY | Sum expenses in a group |
| `UNITS(sum(position))` | Total units after GROUP BY | Sum shares in a group |

### Aggregation Functions

| Function | Purpose |
|----------|---------|
| `SUM(expr)` | Sum values |
| `AVG(expr)` | Average values |
| `COUNT(expr)` | Count non-null values |
| `MIN(expr)` | Minimum value |
| `MAX(expr)` | Maximum value |
| `FIRST(expr)` | First value in group |
| `LAST(expr)` | Last value in group |

### Date Functions

| Function | Purpose |
|----------|---------|
| `YEAR(date)` | Extract year |
| `MONTH(date)` | Extract month (1-12) |
| `DAY(date)` | Extract day |
| `QUARTER(date)` | Extract quarter (1-4) |

### String/Filter Functions

| Expression | Purpose |
|------------|---------|
| `account ~ 'pattern'` | Account name matches regex |
| `payee ~ 'pattern'` | Payee matches regex |
| `narration ~ 'pattern'` | Narration contains text |
| `ANY_METADATA('key')` | Get metadata value |

---

## BQL Syntax Reference

### Basic SELECT

```sql
SELECT column1, column2, ...
FROM tablename
```

### Filtering with WHERE

```sql
SELECT date, narration, account, position
FROM transactions
WHERE account ~ 'Expenses:'
  AND date >= '2024-01-01'
  AND date < '2024-02-01'
```

### Grouping with GROUP BY

```sql
SELECT account, SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Expenses:'
GROUP BY account
ORDER BY total DESC
```

### Date Filtering

```sql
-- Specific date range
WHERE date >= '2024-01-01' AND date < '2024-04-01'

-- Current year
WHERE YEAR(date) = 2024

-- By month
WHERE MONTH(date) = 1

-- Last quarter (calendar)
WHERE QUARTER(date) = 1 AND YEAR(date) = 2024
```

### Account Hierarchy Filtering

```sql
-- All expenses
WHERE account ~ 'Expenses:'

-- Specific sub-account
WHERE account ~ 'Expenses:Food'

-- Multiple accounts
WHERE account ~ 'Expenses:Food' OR account ~ 'Expenses:Dining'

-- Exclude accounts
WHERE account ~ 'Expenses:' AND account !~ 'Expenses:Tax'
```

### Payee/Narration Filtering

```sql
-- Specific merchant
WHERE payee ~ 'Amazon'

-- Narration contains text
WHERE narration ~ 'groceries'
```

### Metadata Filtering

```sql
-- By tag
WHERE tags ~ 'food'

-- By link
WHERE links ~ 'document-ref'

-- By custom metadata
WHERE META('statement') = 'reconciled'
```

---

## Common Query Patterns

### 1. Total Spending by Category

```sql
SELECT account, SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Expenses:'
GROUP BY account
ORDER BY total DESC
```

### 2. Monthly Spending Trend

```sql
SELECT MONTH(date) as month,
       SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Expenses:'
GROUP BY MONTH(date)
ORDER BY month
```

### 3. Spending at Specific Merchant

```sql
SELECT date, narration, COST(position) as amount
FROM transactions
WHERE payee ~ 'Amazon'
  AND account ~ 'Expenses:'
ORDER BY date
```

### 4. Income Statement

```sql
SELECT account, SUM(COST(position)) as amount
FROM transactions
WHERE account ~ 'Income:'
   OR account ~ 'Expenses:'
GROUP BY account
ORDER BY account
```

### 5. Net Worth

```sql
SELECT SUM(COST(balance)) as net_worth
FROM balances
WHERE account ~ 'Assets:'
   OR account ~ 'Liabilities:'
```

### 6. Portfolio Holdings (Units)

```sql
SELECT account,
       UNITS(sum(position)) as shares
FROM inventory
WHERE account ~ 'Assets:Brokerage:'
GROUP BY account
ORDER BY account
```

### 7. Portfolio Holdings (Cost Basis)

```sql
SELECT account,
       COST(sum(position)) as cost_basis
FROM inventory
WHERE account ~ 'Assets:Brokerage:'
GROUP BY account
ORDER BY account
```

### 8. Dividend Income

```sql
SELECT date, narration, COST(position) as amount
FROM transactions
WHERE account ~ 'Income:Dividends'
ORDER BY date
```

### 9. Cash Flow by Month

```sql
SELECT MONTH(date) as month,
       SUM(CASE WHEN account ~ 'Income:' THEN COST(position) ELSE 0 END) as income,
       SUM(CASE WHEN account ~ 'Expenses:' THEN COST(position) ELSE 0 END) as expenses
FROM transactions
GROUP BY MONTH(date)
ORDER BY month
```

### 10. Largest Transactions

```sql
SELECT date, payee, narration, account, COST(position) as amount
FROM transactions
WHERE COST(position) > 100
ORDER BY amount DESC
LIMIT 10
```

### 11. Tag-Based Filtering

```sql
SELECT date, narration, account, COST(position) as amount, tags
FROM transactions
WHERE tags ~ 'vacation'
  AND account ~ 'Expenses:'
```

### 12. Recurring Expenses (by Payee)

```sql
SELECT payee,
       COUNT(*) as occurrences,
       SUM(COST(position)) as total,
       AVG(COST(position)) as average
FROM transactions
WHERE account ~ 'Expenses:'
GROUP BY payee
HAVING COUNT(*) >= 3
ORDER BY total DESC
```

---

## Personal Finance Concept Mapping

| Concept | BQL Approach | Key Tables |
|---------|-------------|------------|
| **Total Expenses** | SUM(COST(position)) WHERE account ~ 'Expenses:' | transactions |
| **Total Income** | SUM(COST(position)) WHERE account ~ 'Income:' | transactions |
| **Net Worth** | SUM(COST(balance)) WHERE Assets - Liabilities | balances |
| **Savings Rate** | (Income - Expenses) / Income | transactions |
| **Monthly Budget** | GROUP BY MONTH(date) with expense sum | transactions |
| **Category Spending** | GROUP BY account with expense sum | transactions |
| **Merchant Spending** | GROUP BY payee with sum | transactions |
| **Portfolio Allocation** | COST(sum(position)) GROUP BY account | inventory |
| **Dividend Income** | WHERE account ~ 'Income:Dividends' | transactions |
| **Capital Gains** | WHERE account ~ 'Income:CapitalGains' | transactions |
| **Cash Flow** | Income vs Expenses over time | transactions |
| **Burn Rate** | Average expenses per month | transactions |
| **Subscriptions** | Recurring payee with consistent amounts | transactions |

---

## Common Mistakes to Avoid

### Mistake 1: Using SQL instead of BQL

```sql
-- WRONG (SQL syntax)
SELECT SUM(amount) FROM expenses WHERE category = 'Food'

-- CORRECT (BQL syntax)
SELECT SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Expenses:Food'
```

### Mistake 2: Forgetting COST() wrapper

```sql
-- WRONG
SELECT SUM(position) FROM transactions

-- CORRECT
SELECT SUM(COST(position)) FROM transactions
```

### Mistake 3: Using = for regex patterns

```sql
-- WRONG
WHERE account = 'Expenses:Food'

-- CORRECT (regex match for hierarchy)
WHERE account ~ 'Expenses:Food'
```

### Mistake 4: Incorrect GROUP BY with aggregation

```sql
-- WRONG (missing GROUP BY)
SELECT account, SUM(COST(position)) FROM transactions

-- CORRECT
SELECT account, SUM(COST(position)) FROM transactions GROUP BY account
```

### Mistake 5: Using COST() after GROUP BY without sum()

```sql
-- WRONG
SELECT account, COST(position) as total FROM transactions GROUP BY account

-- CORRECT
SELECT account, SUM(COST(position)) as total FROM transactions GROUP BY account
```

### Mistake 6: Confusing UNITS and COST

```sql
-- To get number of shares: use UNITS
SELECT UNITS(sum(position)) as shares FROM inventory

-- To get cost basis: use COST
SELECT COST(sum(position)) as cost_basis FROM inventory
```

### Mistake 7: Wrong account hierarchy regex

```sql
-- WRONG (matches ExpensesFood, etc.)
WHERE account ~ 'Expenses.Food'

-- CORRECT
WHERE account ~ 'Expenses:Food'
```

### Mistake 8: Date format issues

```sql
-- WRONG
WHERE date = '01/01/2024'

-- CORRECT (ISO format)
WHERE date >= '2024-01-01'
```

---

## Query Generation Process

When given a question, follow this process:

1. **Parse Intent**: What does the user want?
   - Spending total? Category breakdown? Trend over time? 
   - Income? Profit? Net worth? 
   - Investment holdings? Dividends? Gains?

2. **Map to Accounts**: Which account hierarchy?
   - Expenses → `account ~ 'Expenses:'`
   - Income → `account ~ 'Income:'`
   - Assets → `account ~ 'Assets:'`
   - Liabilities → `account ~ 'Liabilities:'`

3. **Determine Aggregation**:
   - Total → `SUM(COST(position))`
   - Count → `COUNT(*)`
   - Average → `AVG(COST(position))`
   - Shares → `UNITS(sum(position))`

4. **Apply Filters**:
   - Time period → date conditions
   - Category → account regex
   - Merchant → payee regex
   - Tags → metadata/tags

5. **Format Output**:
   - ORDER BY for sorting
   - LIMIT for top-N
   - GROUP BY for breakdowns

6. **Validate**: Does the query return the right shape?

---

## Response Format

For each question, respond with:

```yaml
intent: <what the user wants>
approach: <accounting concept mapping>
query: |
  <the BQL query>
explanation: <why this query works>
expected_columns: [col1, col2, ...]
```

Generate ONLY the BQL query with explanation. Do not execute.
"""

    def build_knowledge_base(self) -> dict:
        """Build the structured BQL knowledge base."""
        kb = {
            "keywords": self.BQL_KEYWORDS,
            "tables": self.BQL_TABLES,
            "functions": self.BQL_FUNCTIONS,
            "operators": self.BQL_OPERATORS,
        }

        # Save as YAML
        kb_path = self.kb_dir / "bql_reference.yaml"
        kb_path.write_text(yaml.dump(kb, default_flow_style=False, sort_keys=False))

        # Save as JSON for programmatic use
        json_path = self.kb_dir / "bql_reference.json"
        json_path.write_text(json.dumps(kb, indent=2))

        return kb

    def build_query_patterns(self) -> list[QueryPattern]:
        """Build the query pattern library."""
        patterns = [
            QueryPattern(
                intent="total_spending_by_category",
                question_examples=[
                    "How much did I spend on food?",
                    "What were my total expenses by category?",
                    "Break down my spending",
                ],
                query_template="""SELECT account, SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Expenses:{category}'
  AND date >= '{start_date}'
  AND date < '{end_date}'
GROUP BY account
ORDER BY total DESC""",
                required_assumptions=[
                    "Account hierarchy uses Expenses: prefix",
                    "COST() returns amounts in operating currency",
                    "Date format is YYYY-MM-DD",
                ],
                output_shape="account, total (monetary amounts)",
                category="spending",
            ),
            QueryPattern(
                intent="monthly_spending_trend",
                question_examples=[
                    "Show my monthly spending",
                    "How has my spending changed over time?",
                    "What is my average monthly spend?",
                ],
                query_template="""SELECT MONTH(date) as month, SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Expenses:'
  AND YEAR(date) = {year}
GROUP BY MONTH(date)
ORDER BY month""",
                required_assumptions=[
                    "YEAR() and MONTH() extract from date",
                    "All transactions in operating currency or converted",
                ],
                output_shape="month, total",
                category="spending",
            ),
            QueryPattern(
                intent="merchant_spending",
                question_examples=[
                    "How much did I spend at Amazon?",
                    "What did I buy from Walmart?",
                    "Show my Uber expenses",
                ],
                query_template="""SELECT date, narration, COST(position) as amount
FROM transactions
WHERE payee ~ '{merchant}'
  AND account ~ 'Expenses:'
  AND date >= '{start_date}'
  AND date < '{end_date}'
ORDER BY date""",
                required_assumptions=["Payee names match pattern", "Case-insensitive match via regex"],
                output_shape="date, narration, amount",
                category="spending",
            ),
            QueryPattern(
                intent="income_by_source",
                question_examples=[
                    "How much did I earn?",
                    "What was my salary income?",
                    "Show income breakdown",
                ],
                query_template="""SELECT account, SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Income:'
  AND date >= '{start_date}'
  AND date < '{end_date}'
GROUP BY account
ORDER BY total DESC""",
                required_assumptions=["Income accounts use Income: prefix"],
                output_shape="account, total",
                category="cashflow",
            ),
            QueryPattern(
                intent="net_worth",
                question_examples=[
                    "What is my net worth?",
                    "How much am I worth?",
                    "Assets minus liabilities",
                ],
                query_template="""SELECT SUM(COST(balance)) as net_worth
FROM balances
WHERE account ~ 'Assets:'
   OR account ~ 'Liabilities:'""",
                required_assumptions=[
                    "balances table available",
                    "Liabilities are negative in COST()",
                    "All priced in operating currency",
                ],
                output_shape="net_worth (single value)",
                category="networth",
            ),
            QueryPattern(
                intent="portfolio_holdings",
                question_examples=[
                    "What stocks do I own?",
                    "How many AAPL shares do I have?",
                    "Show my investment portfolio",
                ],
                query_template="""SELECT account,
       UNITS(sum(position)) as shares,
       COST(sum(position)) as cost_basis
FROM inventory
WHERE account ~ 'Assets:{brokerage}:'
GROUP BY account
ORDER BY account""",
                required_assumptions=[
                    "inventory table available",
                    "UNITS() for share count, COST() for basis",
                ],
                output_shape="account, shares, cost_basis",
                category="investments",
            ),
            QueryPattern(
                intent="dividend_income",
                question_examples=[
                    "How much dividend did I receive?",
                    "Show my dividend income",
                    "What dividends did AAPL pay?",
                ],
                query_template="""SELECT date, narration, COST(position) as amount
FROM transactions
WHERE account ~ 'Income:Dividends'
  AND date >= '{start_date}'
  AND date < '{end_date}'
ORDER BY date""",
                required_assumptions=["Dividend income tracked in Income:Dividends"],
                output_shape="date, narration, amount",
                category="investments",
            ),
            QueryPattern(
                intent="cash_flow",
                question_examples=[
                    "What is my cash flow?",
                    "Income vs expenses by month",
                    "Am I saving money?",
                ],
                query_template="""SELECT MONTH(date) as month,
       SUM(CASE WHEN account ~ 'Income:' THEN COST(position) ELSE 0 END) as income,
       SUM(CASE WHEN account ~ 'Expenses:' THEN COST(position) ELSE 0 END) as expenses
FROM transactions
WHERE YEAR(date) = {year}
GROUP BY MONTH(date)
ORDER BY month""",
                required_assumptions=["Income: and Expenses: prefixes", "CASE WHEN supported"],
                output_shape="month, income, expenses",
                category="cashflow",
            ),
            QueryPattern(
                intent="recurring_expenses",
                question_examples=[
                    "What are my subscriptions?",
                    "Find recurring payments",
                    "Monthly bills",
                ],
                query_template="""SELECT payee,
       COUNT(*) as occurrences,
       SUM(COST(position)) as total,
       AVG(COST(position)) as average
FROM transactions
WHERE account ~ 'Expenses:'
  AND date >= '{start_date}'
GROUP BY payee
HAVING COUNT(*) >= {min_occurrences}
ORDER BY total DESC""",
                required_assumptions=["HAVING clause supported", "Regular payments tracked"],
                output_shape="payee, occurrences, total, average",
                category="spending",
            ),
            QueryPattern(
                intent="tagged_transactions",
                question_examples=[
                    "Show my vacation expenses",
                    "What did I spend on #home-improvement?",
                    "Business trip expenses",
                ],
                query_template="""SELECT date, narration, account, COST(position) as amount
FROM transactions
WHERE tags ~ '{tag}'
  AND account ~ 'Expenses:'
ORDER BY date""",
                required_assumptions=["Tags use # prefix in ledger", "tags column contains tag strings"],
                output_shape="date, narration, account, amount",
                category="metadata",
            ),
            QueryPattern(
                intent="last_quarter",
                question_examples=[
                    "What did I spend last quarter?",
                    "Q1 expenses",
                    "Last 3 months spending",
                ],
                query_template="""SELECT account, SUM(COST(position)) as total
FROM transactions
WHERE account ~ 'Expenses:'
  AND QUARTER(date) = {quarter}
  AND YEAR(date) = {year}
GROUP BY account
ORDER BY total DESC""",
                required_assumptions=["QUARTER() function available", "Calendar quarter definition"],
                output_shape="account, total",
                category="spending",
            ),
            QueryPattern(
                intent="largest_transactions",
                question_examples=[
                    "What are my biggest expenses?",
                    "Largest transactions this year",
                    "Top 5 purchases",
                ],
                query_template="""SELECT date, payee, narration, account, COST(position) as amount
FROM transactions
WHERE account ~ 'Expenses:'
  AND date >= '{start_date}'
ORDER BY amount DESC
LIMIT {n}""",
                required_assumptions=["COST() returns positive amounts for expenses"],
                output_shape="date, payee, narration, account, amount",
                category="spending",
            ),
        ]

        # Save patterns
        for pattern in patterns:
            safe_name = pattern.intent.replace("/", "_")
            path = self.patterns_dir / f"{safe_name}.yaml"
            path.write_text(pattern.to_yaml())

        # Save all patterns index
        index_path = self.patterns_dir / "index.yaml"
        index_data = [
            {"intent": p.intent, "category": p.category, "examples": p.question_examples[:2]}
            for p in patterns
        ]
        index_path.write_text(yaml.dump(index_data, default_flow_style=False, sort_keys=False))

        return patterns

    def build_ontology(self) -> list[FinanceConcept]:
        """Build the personal finance ontology mapping."""
        concepts = [
            FinanceConcept(
                concept="Net Worth",
                formula="Assets - Liabilities",
                bql_pattern="SELECT SUM(COST(balance)) FROM balances WHERE account ~ 'Assets:' OR account ~ 'Liabilities:'",
                examples=["What is my net worth?", "How much am I worth?"],
            ),
            FinanceConcept(
                concept="Savings Rate",
                formula="(Income - Expenses) / Income × 100",
                bql_pattern="Calculate total income and total expenses, then compute percentage",
                examples=["What is my savings rate?", "How much of my income am I saving?"],
            ),
            FinanceConcept(
                concept="Total Income",
                formula="SUM of all income postings",
                bql_pattern="SELECT SUM(COST(position)) FROM transactions WHERE account ~ 'Income:'",
                examples=["How much did I earn?", "Total income this year"],
            ),
            FinanceConcept(
                concept="Total Expenses",
                formula="SUM of all expense postings",
                bql_pattern="SELECT SUM(COST(position)) FROM transactions WHERE account ~ 'Expenses:'",
                examples=["How much did I spend?", "Total expenses"],
            ),
            FinanceConcept(
                concept="Cash Flow",
                formula="Income - Expenses over time",
                bql_pattern="GROUP BY MONTH(date) with income and expense sums",
                examples=["What is my cash flow?", "Monthly income vs expenses"],
            ),
            FinanceConcept(
                concept="Burn Rate",
                formula="Average monthly expenses",
                bql_pattern="AVG of monthly expense totals",
                examples=["What is my burn rate?", "How fast am I spending?"],
            ),
            FinanceConcept(
                concept="Portfolio Allocation",
                formula="Distribution of investments by asset",
                bql_pattern="SELECT account, COST(sum(position)) FROM inventory GROUP BY account",
                examples=["How is my portfolio allocated?", "What percentage is in stocks?"],
            ),
            FinanceConcept(
                concept="Capital Gains",
                formula="Proceeds - Cost Basis of sold assets",
                bql_pattern="WHERE account ~ 'Income:CapitalGains'",
                examples=["What were my capital gains?", "Profit from selling stocks"],
            ),
            FinanceConcept(
                concept="Dividend Income",
                formula="SUM of dividend postings",
                bql_pattern="WHERE account ~ 'Income:Dividends'",
                examples=["How much dividend income?", "Dividends received"],
            ),
            FinanceConcept(
                concept="Cost Basis",
                formula="Original cost of investment positions",
                bql_pattern="COST(sum(position)) for investment accounts",
                examples=["What is my cost basis?", "How much did I pay for AAPL?"],
            ),
            FinanceConcept(
                concept="Market Value",
                formula="Current price × units held",
                bql_pattern="VALUE(position, date) — requires price directives",
                examples=["What is my portfolio worth?", "Current value of holdings"],
            ),
            FinanceConcept(
                concept="Recurring Expenses",
                formula="Payees with ≥N transactions of similar amounts",
                bql_pattern="GROUP BY payee HAVING COUNT(*) >= N",
                examples=["Subscriptions", "Monthly bills"],
            ),
            FinanceConcept(
                concept="Category Budget",
                formula="Actual spending vs budgeted amount per category",
                bql_pattern="GROUP BY account with sum, compare to budget",
                examples=["Am I over budget on food?", "Budget vs actual"],
            ),
            FinanceConcept(
                concept="Taxable Income",
                formula="Gross income - deductions",
                bql_pattern="Income - tax-deductible expenses",
                examples=["What is my taxable income?"],
            ),
        ]

        # Save concepts
        for concept in concepts:
            safe_name = concept.concept.lower().replace(" ", "_")
            path = self.ontology_dir / f"{safe_name}.yaml"
            path.write_text(concept.to_yaml())

        # Save ontology index
        index_path = self.ontology_dir / "index.yaml"
        index_data = [{"concept": c.concept, "formula": c.formula} for c in concepts]
        index_path.write_text(yaml.dump(index_data, default_flow_style=False, sort_keys=False))

        return concepts

    def build_repair_rules(self) -> dict:
        """Build error repair rules for common BQL failures."""
        repair_rules = {
            "syntax_errors": {
                "missing_cost": {
                    "pattern": "SUM(position)",
                    "fix": "SUM(COST(position))",
                    "explanation": "Always wrap position in COST() for monetary values",
                },
                "wrong_regex_operator": {
                    "pattern": "account = 'Expenses:Food'",
                    "fix": "account ~ 'Expenses:Food'",
                    "explanation": "Use ~ (regex match) for account patterns, not =",
                },
                "missing_group_by": {
                    "pattern": "SELECT account, SUM(...) ... (no GROUP BY)",
                    "fix": "Add GROUP BY account",
                    "explanation": "When mixing aggregate and non-aggregate columns, GROUP BY is required",
                },
                "cost_after_group": {
                    "pattern": "COST(position) after GROUP BY",
                    "fix": "COST(sum(position))",
                    "explanation": "After GROUP BY, wrap position in sum() first, then COST()",
                },
                "wrong_date_format": {
                    "pattern": "date = '01/01/2024'",
                    "fix": "date >= '2024-01-01'",
                    "explanation": "Use ISO date format: YYYY-MM-DD",
                },
            },
            "semantic_errors": {
                "wrong_account_prefix": {
                    "symptom": "No results for expense query",
                    "fix": "Check that account names use correct prefix (Expenses:, Income:, etc.)",
                },
                "too_specific_regex": {
                    "symptom": "Too few results",
                    "fix": "Use broader regex pattern. 'Expenses:Food' matches Expenses:Food and Expenses:Food:Restaurants",
                },
                "too_broad_regex": {
                    "symptom": "Too many results",
                    "fix": "Use more specific regex or add additional filters",
                },
                "wrong_sign": {
                    "symptom": "Negative values when expecting positive",
                    "fix": "Use ABS(COST(position)) or filter by account type",
                },
            },
            "aggregation_errors": {
                "missing_having": {
                    "pattern": "WHERE after GROUP BY",
                    "fix": "Use HAVING for post-aggregation filtering",
                },
                "wrong_level_aggregation": {
                    "symptom": "Incorrect grouping granularity",
                    "fix": "Check GROUP BY columns match expected output granularity",
                },
            },
            "inventory_errors": {
                "units_vs_cost": {
                    "symptom": "Using COST for share counts or UNITS for dollar amounts",
                    "fix": "Use UNITS() for share counts, COST() for monetary values",
                },
                "inventory_table_usage": {
                    "symptom": "Can't query inventory positions from transactions table",
                    "fix": "Use inventory table for position-level queries, transactions for flow",
                },
            },
            "pricing_errors": {
                "no_price_data": {
                    "symptom": "VALUE() returns null",
                    "fix": "Ensure price directives exist for the relevant dates and commodities",
                },
                "missing_convert": {
                    "symptom": "Multi-currency amounts not comparable",
                    "fix": "Use CONVERT(position, 'USD') for currency conversion",
                },
            },
            "multi_currency_errors": {
                "mixed_currencies": {
                    "symptom": "SUM across different currencies",
                    "fix": "Convert to base currency first using CONVERT()",
                },
                "implicit_conversion": {
                    "symptom": "Assuming automatic currency conversion",
                    "fix": "BQL does not auto-convert. Use CONVERT() explicitly",
                },
            },
            "date_errors": {
                "exclusive_end_date": {
                    "symptom": "Missing data at range boundary",
                    "fix": "Use date >= 'start' AND date < 'end' (exclusive end, inclusive start)",
                },
                "quarter_definition": {
                    "symptom": "Wrong quarter results",
                    "fix": "QUARTER() returns 1-4 for calendar quarters. Q1 = Jan-Mar",
                },
            },
            "metadata_errors": {
                "tag_format": {
                    "symptom": "Tag filter not matching",
                    "fix": "Tags are stored without # prefix in BQL. Use tags ~ 'tagname' not '#tagname'",
                },
                "link_access": {
                    "symptom": "Can't filter by links",
                    "fix": "Use links ~ 'pattern' to filter by link values",
                },
            },
        }

        # Save repair rules
        for category, rules in repair_rules.items():
            path = self.repair_dir / f"{category}.yaml"
            path.write_text(yaml.dump(rules, default_flow_style=False, sort_keys=False))

        index_path = self.repair_dir / "index.yaml"
        index_path.write_text(yaml.dump(
            {cat: list(rules.keys()) for cat, rules in repair_rules.items()},
            default_flow_style=False, sort_keys=False,
        ))

        return repair_rules

    def improve_from_failure(self, failure_report: dict) -> dict:
        """
        Improve the skill based on a failure report.

        This implements the self-improvement workflow:
        1. Categorize failure
        2. Find supporting documentation
        3. Search examples
        4. Update prompt
        5. Add regression test
        """
        improvement = {
            "failure_reference": failure_report.get("test_id", ""),
            "root_cause": self._diagnose_root_cause(failure_report),
            "documentation_found": self._find_relevant_docs(failure_report),
            "examples_found": self._find_relevant_examples(failure_report),
            "prompt_changes": self._suggest_prompt_changes(failure_report),
            "new_tests_added": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Save improvement report
        report_dir = Path(__file__).resolve().parent.parent.parent / "reports" / "failures"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_id = failure_report.get("test_id", "unknown")
        report_path = report_dir / f"improvement_{report_id}.yaml"
        report_path.write_text(yaml.dump(improvement, default_flow_style=False, sort_keys=False))

        return improvement

    def _diagnose_root_cause(self, failure_report: dict) -> str:
        """Diagnose the root cause of a failure."""
        failure_type = failure_report.get("failure_type", "unknown")
        explanation = failure_report.get("explanation", "")

        diagnoses = {
            "syntax": "The generated BQL has invalid syntax. Check BQL keywords, function names, and clause ordering.",
            "semantic": "The query uses wrong accounts, filters, or doesn't match ledger structure.",
            "aggregation": "Incorrect GROUP BY or aggregate function usage.",
            "inventory": "Position handling error — likely UNITS vs COST confusion.",
            "pricing": "Missing price data or incorrect VALUE() usage.",
            "multi_currency": "Currency conversion not handled properly.",
            "time": "Date filtering logic is incorrect.",
            "metadata": "Tag, link, or metadata filtering failed.",
            "missing": "No query was generated for this question.",
        }

        return diagnoses.get(failure_type, f"Unknown failure: {explanation}")

    def _find_relevant_docs(self, failure_report: dict) -> str:
        """Find relevant documentation sections."""
        failure_type = failure_report.get("failure_type", "")

        doc_sections = {
            "syntax": "BQL Syntax Reference, BQL Keywords, BQL Functions",
            "semantic": "Account Hierarchy, Filtering Patterns, Account Regex",
            "aggregation": "GROUP BY clause, Aggregation Functions, HAVING clause",
            "inventory": "Position Functions: COST(), UNITS(), VALUE()",
            "pricing": "Price Directives, VALUE() function, CONVERT() function",
            "multi_currency": "CONVERT() function, Multi-currency handling",
            "time": "Date Functions: YEAR(), MONTH(), QUARTER()",
            "metadata": "Tag filtering, Link filtering, ANY_METADATA()",
        }

        return doc_sections.get(failure_type, "General BQL documentation")

    def _find_relevant_examples(self, failure_report: dict) -> str:
        """Find relevant example queries."""
        patterns_dir = self.patterns_dir
        existing_patterns = list(patterns_dir.glob("*.yaml")) if patterns_dir.exists() else []
        return f"Found {len(existing_patterns)} query patterns that may be relevant"

    def _suggest_prompt_changes(self, failure_report: dict) -> str:
        """Suggest changes to the skill prompt."""
        failure_type = failure_report.get("failure_type", "")

        suggestions = {
            "syntax": "Add more BQL syntax examples, clarify function signatures",
            "semantic": "Improve account hierarchy documentation with more examples",
            "aggregation": "Add aggregation pattern examples with GROUP BY",
            "inventory": "Clarify UNITS vs COST usage with concrete examples",
            "pricing": "Document VALUE() and CONVERT() requirements",
            "multi_currency": "Add multi-currency query patterns",
            "time": "Improve date filtering documentation",
            "metadata": "Add metadata query patterns",
        }

        return suggestions.get(failure_type, "Review and improve relevant prompt section")

    def run_full_skill_build(self) -> dict:
        """Run the full skill building pipeline."""
        print("=" * 60)
        print("Agent 2 — Skill Builder")
        print("=" * 60)

        # 1. Build knowledge base
        print("\n1. Building knowledge base...")
        kb = self.build_knowledge_base()
        print(f"   Extracted {len(kb['keywords'])} keywords")
        print(f"   Extracted {len(kb['tables'])} tables")
        print(f"   Extracted {len(kb['functions'])} functions")
        print(f"   Extracted {len(kb['operators'])} operators")

        # 2. Build query patterns
        print("\n2. Building query pattern library...")
        patterns = self.build_query_patterns()
        print(f"   Created {len(patterns)} query patterns")

        # 3. Build ontology
        print("\n3. Building personal finance ontology...")
        concepts = self.build_ontology()
        print(f"   Mapped {len(concepts)} finance concepts")

        # 4. Build repair rules
        print("\n4. Building repair rules...")
        rules = self.build_repair_rules()
        rule_count = sum(len(v) for v in rules.values())
        print(f"   Created {rule_count} repair rules")

        # 5. Generate prompt
        print("\n5. Generating skill prompt...")
        prompt = self.build_skill_prompt()
        prompt_len = len(prompt)
        print(f"   Generated prompt ({prompt_len} chars)")

        summary = {
            "keywords": len(kb["keywords"]),
            "tables": len(kb["tables"]),
            "functions": len(kb["functions"]),
            "patterns": len(patterns),
            "concepts": len(concepts),
            "repair_rules": rule_count,
            "prompt_size_chars": prompt_len,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        summary_path = self.skill_dir / "build_summary.yaml"
        summary_path.write_text(yaml.dump(summary, default_flow_style=False, sort_keys=False))

        print("\n" + "=" * 60)
        print("Skill build complete!")
        print(f"Prompt: {self.skill_dir / 'prompt.md'}")
        print("=" * 60)

        return summary


if __name__ == "__main__":
    builder = SkillBuilder()
    builder.run_full_skill_build()
