"""
Agent 4 — Adversarial User

Continuously discovers weaknesses in the BQL skill.
Generates difficult, ambiguous, and edge-case questions.

Focus areas:
- Ambiguity (unclear intent)
- Investments (shares vs cost vs value)
- Multi-Currency (FX complexity)
- Tax (complex rules)
- Date Logic (quarter definitions, boundaries)
- Metadata (tags, links, custom fields)
"""

import yaml
import random
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class AdversarialQuestion:
    """A challenging test question designed to expose skill weaknesses."""
    question: str
    category: str
    difficulty: str  # medium, hard, very_hard
    ambiguity_type: str  # What makes it hard
    reasoning: str  # Why this is a good adversarial test
    trap_elements: list[str] = field(default_factory=list)

    def to_yaml(self) -> str:
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)


class AdversarialUser:
    """Agent 4 main class. Generates adversarial test cases."""

    CATEGORIES = [
        "spending",
        "budgeting", 
        "cashflow",
        "networth",
        "investments",
        "tax",
        "multicurrency",
        "metadata",
    ]

    AMBIGUITY_TYPES = [
        "ambiguous_merchant",      # "food" could mean groceries OR restaurants
        "ambiguous_timeframe",     # "last quarter" — calendar or rolling?
        "ambiguous_measurement",   # "how much AAPL" — shares, cost, or value?
        "ambiguous_accounting",    # "income" — gross, net, taxable?
        "ambiguous_currency",      # "net worth" — in which currency?
        "unstated_assumptions",    # Assumes knowledge not in the query
        "edge_case_dates",         # Year boundaries, leap years
        "nested_categories",       # Sub-accounts with partial matches
        "zero_results",            # No matching data
        "implicit_conversion",     # Requires currency conversion
        "complex_grouping",        # Multi-level aggregation
        "metadata_dependency",     # Requires tag/link interpretation
    ]

    def __init__(self, project_dir: str | Path = None):
        if project_dir is None:
            project_dir = Path(__file__).resolve().parent.parent.parent
        self.project_dir = Path(project_dir)
        self.output_dir = project_dir / "reports" / "failures"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_spending_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial spending questions."""
        return [
            AdversarialQuestion(
                question="How much did I spend on food?",
                category="spending",
                difficulty="hard",
                ambiguity_type="ambiguous_merchant",
                reasoning="'Food' is ambiguous — could mean groceries, restaurants, or both. "
                         "The skill must recognize this ambiguity and decide what accounts to include. "
                         "Expenses:Food:Groceries vs Expenses:Food:Restaurants vs just Expenses:Food.",
                trap_elements=[
                    "Might only match Expenses:Food and miss Expenses:Food:Restaurants",
                    "Might match Expenses:Food:Groceries which may not exist",
                    "Should clarify what 'food' means or use broad regex",
                ],
            ),
            AdversarialQuestion(
                question="What were my Amazon purchases?",
                category="spending",
                difficulty="medium",
                ambiguity_type="ambiguous_merchant",
                reasoning="Amazon sells everything — the payee is the same but categories vary. "
                         "Should the query return all or filter by expense category?",
                trap_elements=[
                    "Without account filter, may return refunds or income",
                    "Payee matching is case-sensitive unless regex is used",
                    "Multiple merchants might have 'Amazon' in name",
                ],
            ),
            AdversarialQuestion(
                question="Show me what I spent on transportation including gas, parking, and repairs.",
                category="spending",
                difficulty="hard",
                ambiguity_type="nested_categories",
                reasoning="Requires matching multiple sub-accounts under Expenses:Transport. "
                         "Each ledger may organize these differently.",
                trap_elements=[
                    "Sub-accounts might not be standardized",
                    "Regex must match Transport and all children",
                    "Might need to combine multiple queries",
                ],
            ),
            AdversarialQuestion(
                question="What was my biggest expense?",
                category="spending",
                difficulty="easy",
                ambiguity_type="ambiguous_measurement",
                reasoning="'Biggest' could mean single largest transaction or largest category total. "
                         "Two valid interpretations with different queries.",
                trap_elements=[
                    "Could interpret as single transaction (no GROUP BY)",
                    "Could interpret as category total (GROUP BY account)",
                    "Should clarify which interpretation is used",
                ],
            ),
            AdversarialQuestion(
                question="How much did I spend at restaurants during the last month?",
                category="spending",
                difficulty="medium",
                ambiguity_type="ambiguous_timeframe",
                reasoning="'Last month' needs date calculation. Also, 'restaurants' may be "
                         "Expenses:Food:Restaurants or Expenses:Restaurants.",
                trap_elements=[
                    "Date calculation for 'last month'",
                    "Account naming inconsistency",
                    "Should handle current date calculation",
                ],
            ),
        ]

    def generate_budgeting_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial budgeting questions."""
        return [
            AdversarialQuestion(
                question="Am I over budget?",
                category="budgeting",
                difficulty="very_hard",
                ambiguity_type="unstated_assumptions",
                reasoning="No budget is defined in the ledger. The skill must recognize "
                         "that budget data doesn't exist in standard Beancount ledgers.",
                trap_elements=[
                    "Budgets are external to Beancount",
                    "Might try to extract non-existent data",
                    "Should explain that budgets are not in the ledger",
                ],
            ),
            AdversarialQuestion(
                question="Compare my spending this month to the same month last year.",
                category="budgeting",
                difficulty="hard",
                ambiguity_type="edge_case_dates",
                reasoning="Requires two date ranges with relative calculation. "
                         "Must handle year boundaries correctly.",
                trap_elements=[
                    "Date arithmetic needed",
                    "Year boundary handling",
                    "Two separate queries or one combined",
                ],
            ),
            AdversarialQuestion(
                question="What percentage of my income goes to housing?",
                category="budgeting",
                difficulty="hard",
                ambiguity_type="complex_grouping",
                reasoning="Requires computing ratio: housing expenses / total income × 100. "
                         "Might need sub-queries or multiple queries.",
                trap_elements=[
                    "Ratio calculation not native to BQL",
                    "Might need two queries",
                    "'Housing' could include rent, mortgage, utilities",
                ],
            ),
        ]

    def generate_cashflow_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial cash flow questions."""
        return [
            AdversarialQuestion(
                question="Am I cash flow positive?",
                category="cashflow",
                difficulty="medium",
                ambiguity_type="ambiguous_timeframe",
                reasoning="Cash flow positive over what period? Monthly? Yearly? All-time? "
                         "The skill must choose a reasonable default or ask for clarification.",
                trap_elements=[
                    "No timeframe specified",
                    "Must define 'positive' (income > expenses)",
                    "May need to specify date range",
                ],
            ),
            AdversarialQuestion(
                question="What is my monthly burn rate?",
                category="cashflow",
                difficulty="hard",
                ambiguity_type="complex_grouping",
                reasoning="Burn rate = average monthly expenses. Must aggregate per month, "
                         "then average across months. Two-level aggregation.",
                trap_elements=[
                    "Two-level aggregation (monthly sum, then average)",
                    "May not be possible in single BQL query",
                    "Alternative: total expenses / number of months",
                ],
            ),
            AdversarialQuestion(
                question="How much free cash flow do I have each month after all expenses?",
                category="cashflow",
                difficulty="hard",
                ambiguity_type="complex_grouping",
                reasoning="Monthly income minus monthly expenses. Requires grouping by month "
                         "and computing difference. CASE WHEN or subquery needed.",
                trap_elements=[
                    "Need income and expense in same GROUP BY month",
                    "CASE WHEN for conditional aggregation",
                    "Edge cases: months with no income or no expenses",
                ],
            ),
        ]

    def generate_networth_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial net worth questions."""
        return [
            AdversarialQuestion(
                question="What is my net worth?",
                category="networth",
                difficulty="hard",
                ambiguity_type="ambiguous_measurement",
                reasoning="Net worth can be measured in multiple ways: cost basis, market value, "
                         "or book value. The skill must clarify or choose one.",
                trap_elements=[
                    "Cost basis vs market value",
                    "May need prices for market value",
                    "Liabilities must be subtracted",
                ],
            ),
            AdversarialQuestion(
                question="How much equity do I have in my house?",
                category="networth",
                difficulty="very_hard",
                ambiguity_type="ambiguous_measurement",
                reasoning="Equity = property value - mortgage balance. Property value may not "
                         "be tracked in Beancount. Mortgage might be split into principal/interest.",
                trap_elements=[
                    "Property value may not be in ledger",
                    "Mortgage principal vs total mortgage",
                    "May need to interpret account structure",
                ],
            ),
        ]

    def generate_investment_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial investment questions."""
        return [
            AdversarialQuestion(
                question="How much AAPL do I own?",
                category="investments",
                difficulty="hard",
                ambiguity_type="ambiguous_measurement",
                reasoning="'How much' could mean: number of shares, cost basis, or market value. "
                         "This is the most common ambiguity in investment questions.",
                trap_elements=[
                    "Shares: UNITS(sum(position))",
                    "Cost basis: COST(sum(position))",
                    "Market value: VALUE(sum(position)) requires prices",
                    "Should clarify which is being returned",
                ],
            ),
            AdversarialQuestion(
                question="What is my portfolio performance?",
                category="investments",
                difficulty="very_hard",
                ambiguity_type="unstated_assumptions",
                reasoning="Performance requires comparison over time. Need initial and current values. "
                         "Requires prices at two points. Might need external data.",
                trap_elements=[
                    "Requires price history",
                    "Time period not specified",
                    "Performance metric not defined (absolute, percentage, annualized)",
                ],
            ),
            AdversarialQuestion(
                question="How much profit did I make from selling stocks?",
                category="investments",
                difficulty="medium",
                ambiguity_type="ambiguous_accounting",
                reasoning="Profit = proceeds - cost basis. This requires tracking the cost basis "
                         "of sold lots. Beancount handles this via lot matching.",
                trap_elements=[
                    "Need to find sell transactions",
                    "Cost basis is automatically computed by Beancount",
                    "CapitalGains account may track this directly",
                ],
            ),
            AdversarialQuestion(
                question="What is my allocation between stocks and bonds?",
                category="investments",
                difficulty="hard",
                ambiguity_type="nested_categories",
                reasoning="Requires classifying instruments into asset classes. "
                         "Beancount doesn't have asset class metadata by default.",
                trap_elements=[
                    "Asset classification not native to Beancount",
                    "Must map specific holdings to categories",
                    "Percentage calculation needed",
                ],
            ),
        ]

    def generate_multicurrency_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial multi-currency questions."""
        return [
            AdversarialQuestion(
                question="What is my net worth in EUR?",
                category="multicurrency",
                difficulty="hard",
                ambiguity_type="ambiguous_currency",
                reasoning="All assets must be converted to EUR. Requires CONVERT() function "
                         "and price data for all holdings.",
                trap_elements=[
                    "CONVERT() requires price data",
                    "May need to handle missing prices",
                    "Different conversion rates on different dates",
                ],
            ),
            AdversarialQuestion(
                question="How much did I spend in EUR and GBP combined last month?",
                category="multicurrency",
                difficulty="hard",
                ambiguity_type="implicit_conversion",
                reasoning="Can't sum EUR and GBP directly. Must convert to common currency first. "
                         "The conversion rate date matters.",
                trap_elements=[
                    "Cannot sum different currencies directly",
                    "Need CONVERT() or choose a base currency",
                    "Which date's exchange rate to use",
                ],
            ),
            AdversarialQuestion(
                question="What was the exchange rate I used for my EUR income?",
                category="multicurrency",
                difficulty="medium",
                ambiguity_type="ambiguous_measurement",
                reasoning="Exchange rates come from price directives. Need to query prices table "
                         "for EUR prices on relevant dates.",
                trap_elements=[
                    "Need to use prices table, not transactions",
                    "May need to find specific dates",
                    "Average vs specific rate",
                ],
            ),
        ]

    def generate_tax_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial tax questions."""
        return [
            AdversarialQuestion(
                question="What was my taxable income last year?",
                category="tax",
                difficulty="very_hard",
                ambiguity_type="unstated_assumptions",
                reasoning="Taxable income depends on jurisdiction and deductions. "
                         "Beancount doesn't track tax categories automatically.",
                trap_elements=[
                    "Tax rules are external to Beancount",
                    "Deductions not automatically tracked",
                    "May need to explain limitations",
                ],
            ),
            AdversarialQuestion(
                question="How much tax did I pay?",
                category="tax",
                difficulty="hard",
                ambiguity_type="ambiguous_accounting",
                reasoning="'Tax paid' could mean: payroll tax withheld, estimated tax payments, "
                         "sales tax in purchases, or property tax. Each is a different account.",
                trap_elements=[
                    "Multiple types of tax",
                    "May not be tracked in separate accounts",
                    "Some tax is embedded in transactions",
                ],
            ),
            AdversarialQuestion(
                question="What were my tax deductions?",
                category="tax",
                difficulty="very_hard",
                ambiguity_type="unstated_assumptions",
                reasoning="Deductions require tagging or specific account categorization. "
                         "Standard Beancount ledgers don't mark deductible expenses.",
                trap_elements=[
                    "Requires metadata or tags for deductibility",
                    "Different deduction types (charitable, medical, etc.)",
                    "May need to explain that categorization is needed",
                ],
            ),
        ]

    def generate_metadata_attacks(self) -> list[AdversarialQuestion]:
        """Generate adversarial metadata questions."""
        return [
            AdversarialQuestion(
                question="Show my vacation expenses.",
                category="metadata",
                difficulty="medium",
                ambiguity_type="metadata_dependency",
                reasoning="Requires filtering by #vacation tag. Tags must exist in the ledger. "
                         "Not all transactions will be tagged.",
                trap_elements=[
                    "Tags are optional in Beancount",
                    "Need to check if tags exist",
                    "Tag format: #vacation in ledger, 'vacation' in BQL",
                ],
            ),
            AdversarialQuestion(
                question="What expenses are linked to my tax documents?",
                category="metadata",
                difficulty="hard",
                ambiguity_type="metadata_dependency",
                reasoning="Links (^document-ref) connect transactions to documents. "
                         "Not commonly used in all ledgers.",
                trap_elements=[
                    "Links are rarely used",
                    "May not be present in ledger",
                    "Need to explain what links are",
                ],
            ),
            AdversarialQuestion(
                question="Show me all unreconciled transactions.",
                category="metadata",
                difficulty="medium",
                ambiguity_type="metadata_dependency",
                reasoning="Reconciliation status is usually tracked via statement metadata. "
                         "Requires understanding of balance assertions vs metadata.",
                trap_elements=[
                    "Reconciliation not always tracked",
                    "May need to use balance assertions instead",
                    "Metadata key may vary between ledgers",
                ],
            ),
        ]

    def generate_edge_case_attacks(self) -> list[AdversarialQuestion]:
        """Generate edge case and boundary questions."""
        return [
            AdversarialQuestion(
                question="Show my expenses from February 29, 2024.",
                category="spending",
                difficulty="medium",
                ambiguity_type="edge_case_dates",
                reasoning="February 29 only exists in leap years. Tests date handling. "
                         "2024 is a leap year, so this should work.",
                trap_elements=[
                    "Leap year date handling",
                    "May return empty if no transactions that day",
                    "Date parsing edge case",
                ],
            ),
            AdversarialQuestion(
                question="What did I spend on December 31?",
                category="spending",
                difficulty="easy",
                ambiguity_type="edge_case_dates",
                reasoning="Year boundary date. Tests inclusive/exclusive range handling.",
                trap_elements=[
                    "Year boundary",
                    "Date comparison edge case",
                ],
            ),
            AdversarialQuestion(
                question="Show my spending where the payee is empty.",
                category="spending",
                difficulty="hard",
                ambiguity_type="edge_case_dates",
                reasoning="Some transactions may have empty payee. Tests null/empty handling.",
                trap_elements=[
                    "Null/empty payee handling",
                    "IS NULL vs = '' in BQL",
                ],
            ),
            AdversarialQuestion(
                question="What were my expenses with no tags?",
                category="metadata",
                difficulty="hard",
                ambiguity_type="metadata_dependency",
                reasoning="Filtering for absence of metadata. Tests NOT logic with tags.",
                trap_elements=[
                    "Negation of metadata condition",
                    "May require tags IS NULL or similar",
                ],
            ),
            AdversarialQuestion(
                question="Show the average, median, and mode of my expenses.",
                category="spending",
                difficulty="very_hard",
                ambiguity_type="complex_grouping",
                reasoning="BQL has AVG but not MEDIAN or MODE. Tests whether the skill "
                         "recognizes unsupported operations.",
                trap_elements=[
                    "MEDIAN and MODE not available in BQL",
                    "Should explain limitations",
                    "Could suggest alternative approaches",
                ],
            ),
        ]

    def generate_all_attacks(self) -> list[AdversarialQuestion]:
        """Generate all adversarial questions."""
        all_attacks = []
        all_attacks.extend(self.generate_spending_attacks())
        all_attacks.extend(self.generate_budgeting_attacks())
        all_attacks.extend(self.generate_cashflow_attacks())
        all_attacks.extend(self.generate_networth_attacks())
        all_attacks.extend(self.generate_investment_attacks())
        all_attacks.extend(self.generate_multicurrency_attacks())
        all_attacks.extend(self.generate_tax_attacks())
        all_attacks.extend(self.generate_metadata_attacks())
        all_attacks.extend(self.generate_edge_case_attacks())

        return all_attacks

    def run_adversarial_generation(self) -> dict:
        """Generate and save all adversarial test cases."""
        print("=" * 60)
        print("Agent 4 — Adversarial User")
        print("=" * 60)

        attacks = self.generate_all_attacks()

        # Save all attacks
        attacks_path = self.output_dir / "adversarial_questions.yaml"
        attacks_data = [asdict(a) for a in attacks]
        attacks_path.write_text(
            yaml.dump(attacks_data, default_flow_style=False, sort_keys=False)
        )

        # Category breakdown
        categories = {}
        for a in attacks:
            cat = a.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(a.question)

        # Difficulty breakdown
        difficulties = {}
        for a in attacks:
            diff = a.difficulty
            if diff not in difficulties:
                difficulties[diff] = 0
            difficulties[diff] += 1

        print(f"\nGenerated {len(attacks)} adversarial questions:")
        print(f"  Categories:")
        for cat, questions in sorted(categories.items()):
            print(f"    {cat}: {len(questions)} questions")
        print(f"\n  Difficulty distribution:")
        for diff, count in sorted(difficulties.items()):
            print(f"    {diff}: {count}")

        # Save summary
        summary = {
            "total_questions": len(attacks),
            "categories": {cat: len(qs) for cat, qs in categories.items()},
            "difficulties": difficulties,
            "ambiguity_types_covered": sorted(set(a.ambiguity_type for a in attacks)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        summary_path = self.output_dir / "adversarial_summary.yaml"
        summary_path.write_text(
            yaml.dump(summary, default_flow_style=False, sort_keys=False)
        )

        print(f"\nSaved to {attacks_path}")
        print("=" * 60)

        return summary


if __name__ == "__main__":
    adversary = AdversarialUser()
    adversary.run_adversarial_generation()
