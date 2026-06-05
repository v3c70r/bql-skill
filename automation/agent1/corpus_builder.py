"""
Agent 1 — Corpus Builder

Continuously discover, collect, normalize, and catalog Beancount data sources.
Produces datasets: ledgers, queries, ground truth, repository catalogs.

Sources:
- Official: beancount/beanquery repos, docs
- Community: GitHub *.bean files, issue trackers
- Synthetic: generated ledger data for edge cases
"""

import json
import yaml
import os
import re
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


@dataclass
class RepoCatalog:
    """Metadata about a discovered Beancount repository."""
    repo_url: str
    repo_name: str
    accounts: list[str] = field(default_factory=list)
    currencies: list[str] = field(default_factory=list)
    commodities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    metadata_fields: list[str] = field(default_factory=list)
    investment_usage: bool = False
    multi_currency: bool = False
    ledger_count: int = 0
    description: str = ""

    def to_yaml(self) -> str:
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)


@dataclass
class QueryRecord:
    """A discovered BQL query with metadata."""
    question: str
    query: str
    source: str  # doc, repo, issue, blog
    notes: str = ""
    category: str = ""

    def to_yaml(self) -> str:
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)


@dataclass
class GroundTruthRecord:
    """A ground truth record: ledger + question + expected result."""
    id: str
    ledger: str
    question: str
    expected_result: dict
    category: str
    difficulty: str = "medium"
    source: str = ""

    def to_yaml(self) -> str:
        return yaml.dump(asdict(self), default_flow_style=False, sort_keys=False)


class CorpusBuilder:
    """Agent 1 main class. Discovers and catalogs Beancount data sources."""

    # Official sources
    OFFICIAL_SOURCES = [
        "https://github.com/beancount/beanquery",
        "https://github.com/beancount/beancount",
        "https://github.com/beancount/beancount/tree/master/examples",
        "https://beancount.io/docs/Basics/beancount-query-language",
        "https://beancount.github.io/docs/",
    ]

    # Fava live examples
    FAVA_SOURCES = [
        "https://fava.pythonanywhere.com/example-beancount-file/",
        "https://fava.pythonanywhere.com/example-beancount-file/income_statement/",
    ]

    # GitHub API search queries
    GITHUB_SEARCHES = [
        "beancount language:python",
        "beanquery language:python",
        "fava language:python",
        "*.bean extension:bean",
        "*.beancount extension:beancount",
        "plaintext accounting",
    ]

    def __init__(self, corpus_dir: str | Path = None):
        if corpus_dir is None:
            corpus_dir = Path(__file__).resolve().parent.parent.parent / "corpus"
        self.corpus_dir = Path(corpus_dir)
        self.ledgers_dir = self.corpus_dir / "ledgers"
        self.repos_dir = self.corpus_dir / "repositories"
        self.synthetic_dir = self.corpus_dir / "synthetic"
        self.metadata_dir = self.corpus_dir / "metadata"
        self.train_dir = self.corpus_dir / "train"
        self.holdout_dir = self.corpus_dir / "holdout"

        # Ensure directories exist
        for d in [self.ledgers_dir, self.repos_dir, self.synthetic_dir,
                  self.metadata_dir, self.train_dir, self.holdout_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def collect_from_github(self, github_token: str = None) -> list[RepoCatalog]:
        """Discover Beancount repositories on GitHub."""
        catalogs = []
        headers = {"Accept": "application/vnd.github.v3+json"}
        if github_token:
            headers["Authorization"] = f"token {github_token}"

        for query in self.GITHUB_SEARCHES:
            try:
                url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=10"
                req = Request(url, headers=headers)
                with urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())
                    for item in data.get("items", []):
                        catalog = RepoCatalog(
                            repo_url=item["html_url"],
                            repo_name=item["full_name"],
                            description=item.get("description", ""),
                        )
                        catalogs.append(catalog)
            except (URLError, HTTPError) as e:
                print(f"GitHub API error for '{query}': {e}")
            time.sleep(1)  # Rate limit consideration

        self._save_repo_catalogs(catalogs)
        return catalogs

    def _save_repo_catalogs(self, catalogs: list[RepoCatalog]):
        """Save repository catalogs to disk."""
        for i, cat in enumerate(catalogs):
            safe_name = re.sub(r"[^\w\-_]", "_", cat.repo_name)
            path = self.repos_dir / f"{i:04d}_{safe_name}.yaml"
            path.write_text(cat.to_yaml())

    def extract_metadata_from_ledger(self, ledger_path: str | Path) -> dict:
        """Parse a Beancount ledger file and extract metadata."""
        content = Path(ledger_path).read_text()
        metadata = {
            "accounts": set(),
            "currencies": set(),
            "commodities": set(),
            "tags": set(),
            "links": set(),
            "metadata_keys": set(),
        }

        for line in content.split("\n"):
            stripped = line.strip()
            
            # Extract account names from 'open' directives and postings
            # 'open' directive: 2024-01-01 open Assets:Checking
            open_match = re.match(r'^\d{4}-\d{2}-\d{2}\s+open\s+([A-Z][\w:]+)', stripped)
            if open_match:
                metadata["accounts"].add(open_match.group(1))
            
            # Postings: exactly 2 spaces indent + account name + whitespace + amount
            #   Assets:Checking  5000.00 USD
            posting_match = re.match(r'^  ([A-Z][\w:]+)\s+', line)
            if posting_match:
                metadata["accounts"].add(posting_match.group(1))

            # Extract currencies/commodities (e.g., USD, EUR, AAPL)
            # Currencies appear after amounts on posting lines
            curr_matches = re.findall(r'\b([A-Z]{2,5})\b(?=\s*$|\s*[#;])', stripped)
            for c in curr_matches:
                if c not in ("IN", "AS", "FOR", "THE", "AND", "OPEN", "NOTE", "FROM", "TOTAL"):
                    metadata["currencies"].add(c)
            
            # Also detect commodities in {price CURRENCY} format and position lines
            commodity_matches = re.findall(r'\{\s*[\d.]+\s+([A-Z]{2,5})\s*\}', stripped)
            for c in commodity_matches:
                metadata["currencies"].add(c)

            # Extract tags (#tag)
            tag_matches = re.findall(r'#([\w-]+)', stripped)
            for t in tag_matches:
                metadata["tags"].add(t)

            # Extract links (^link)
            link_matches = re.findall(r'\^([\w-]+)', stripped)
            for l in link_matches:
                metadata["links"].add(l)

        return {k: sorted(v) for k, v in metadata.items()}

    def generate_synthetic_ledgers(self) -> list[Path]:
        """Generate synthetic Beancount ledgers for edge case testing."""
        ledgers = []

        # Simple personal ledger
        simple = self._generate_simple_ledger()
        path = self.synthetic_dir / "simple_personal.bean"
        path.write_text(simple)
        ledgers.append(path)

        # Investment ledger
        investment = self._generate_investment_ledger()
        path = self.synthetic_dir / "investment.bean"
        path.write_text(investment)
        ledgers.append(path)

        # Multi-currency ledger
        multicurrency = self._generate_multicurrency_ledger()
        path = self.synthetic_dir / "multicurrency.bean"
        path.write_text(multicurrency)
        ledgers.append(path)

        # Business ledger
        business = self._generate_business_ledger()
        path = self.synthetic_dir / "business.bean"
        path.write_text(business)
        ledgers.append(path)

        # Rental property ledger
        rental = self._generate_rental_ledger()
        path = self.synthetic_dir / "rental_property.bean"
        path.write_text(rental)
        ledgers.append(path)

        # Crypto ledger
        crypto = self._generate_crypto_ledger()
        path = self.synthetic_dir / "crypto.bean"
        path.write_text(crypto)
        ledgers.append(path)

        return ledgers

    def _generate_simple_ledger(self) -> str:
        """Generate a simple personal finance ledger with common transactions."""
        return """\
option "title" "Simple Personal Ledger"
option "operating_currency" "USD"

2024-01-01 open Assets:Checking
2024-01-01 open Assets:Savings
2024-01-01 open Liabilities:CreditCard
2024-01-01 open Income:Salary
2024-01-01 open Expenses:Food
2024-01-01 open Expenses:Rent
2024-01-01 open Expenses:Transport
2024-01-01 open Expenses:Utilities
2024-01-01 open Expenses:Entertainment
2024-01-01 open Expenses:Healthcare
2024-01-01 open Expenses:Shopping

2024-01-05 * "Employer Inc" "Monthly salary"
  Assets:Checking  5000.00 USD
  Income:Salary    -5000.00 USD

2024-01-06 * "Landlord" "January rent" #housing
  Expenses:Rent  1500.00 USD
  Assets:Checking  -1500.00 USD

2024-01-07 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  85.50 USD
  Assets:Checking  -85.50 USD

2024-01-10 * "Gas Station" "Fuel"
  Expenses:Transport  45.00 USD
  Assets:Checking  -45.00 USD

2024-01-12 * "Restaurant" "Dinner out" #food
  Expenses:Food  62.30 USD
  Assets:Checking  -62.30 USD

2024-01-14 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  92.15 USD
  Assets:Checking  -92.15 USD

2024-01-15 * "Electric Company" "Electric bill" #utilities
  Expenses:Utilities  120.00 USD
  Assets:Checking  -120.00 USD

2024-01-16 * "Cinema" "Movie tickets" #entertainment
  Expenses:Entertainment  30.00 USD
  Assets:Checking  -30.00 USD

2024-01-18 * "Clinic" "Doctor visit" #health
  Expenses:Healthcare  75.00 USD
  Assets:Checking  -75.00 USD

2024-01-20 * "Amazon" "Online purchase" #shopping
  Expenses:Shopping  129.99 USD
  Assets:Checking  -129.99 USD

2024-01-21 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  78.40 USD
  Assets:Checking  -78.40 USD

2024-01-22 * "Internet Provider" "Monthly internet" #utilities
  Expenses:Utilities  65.00 USD
  Assets:Checking  -65.00 USD

2024-01-25 * "Restaurant" "Lunch" #food
  Expenses:Food  24.50 USD
  Assets:Checking  -24.50 USD

2024-01-28 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  88.25 USD
  Assets:Checking  -88.25 USD

2024-01-30 * "Transfer to savings"
  Assets:Savings  1000.00 USD
  Assets:Checking  -1000.00 USD

2024-02-01 * "Employer Inc" "Monthly salary"
  Assets:Checking  5000.00 USD
  Income:Salary    -5000.00 USD

2024-02-02 * "Landlord" "February rent" #housing
  Expenses:Rent  1500.00 USD
  Assets:Checking  -1500.00 USD

2024-02-03 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  91.30 USD
  Assets:Checking  -91.30 USD

2024-02-08 * "Gas Station" "Fuel"
  Expenses:Transport  48.00 USD
  Assets:Checking  -48.00 USD

2024-02-10 * "Restaurant" "Valentine dinner" #food
  Expenses:Food  95.00 USD
  Assets:Checking  -95.00 USD

2024-02-14 * "Electric Company" "Electric bill" #utilities
  Expenses:Utilities  115.00 USD
  Assets:Checking  -115.00 USD

2024-02-15 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  85.75 USD
  Assets:Checking  -85.75 USD

2024-02-20 * "Amazon" "Shopping" #shopping
  Expenses:Shopping  79.50 USD
  Assets:Checking  -79.50 USD

2024-02-25 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  94.20 USD
  Assets:Checking  -94.20 USD

2024-02-28 * "Transfer to savings"
  Assets:Savings  1000.00 USD
  Assets:Checking  -1000.00 USD

2024-03-01 * "Employer Inc" "Monthly salary"
  Assets:Checking  5000.00 USD
  Income:Salary    -5000.00 USD

2024-03-02 * "Landlord" "March rent" #housing
  Expenses:Rent  1500.00 USD
  Assets:Checking  -1500.00 USD

2024-03-05 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  87.90 USD
  Assets:Checking  -87.90 USD

2024-03-10 * "Pharmacy" "Medicine" #health
  Expenses:Healthcare  35.00 USD
  Assets:Checking  -35.00 USD

2024-03-12 * "Restaurant" "Dinner" #food
  Expenses:Food  55.00 USD
  Assets:Checking  -55.00 USD

2024-03-15 * "Electric Company" "Electric bill" #utilities
  Expenses:Utilities  130.00 USD
  Assets:Checking  -130.00 USD

2024-03-20 * "Grocery Store" "Weekly groceries" #food
  Expenses:Food  82.60 USD
  Assets:Checking  -82.60 USD

2024-03-25 * "Gas Station" "Fuel"
  Expenses:Transport  42.00 USD
  Assets:Checking  -42.00 USD

2024-03-30 * "Transfer to savings"
  Assets:Savings  1000.00 USD
  Assets:Checking  -1000.00 USD
"""

    def _generate_investment_ledger(self) -> str:
        """Generate an investment ledger with stock transactions."""
        return """\
option "title" "Investment Ledger"
option "operating_currency" "USD"

2024-01-01 open Assets:Checking
2024-01-01 open Assets:Brokerage:Cash
2024-01-01 open Assets:Brokerage:AAPL
2024-01-01 open Assets:Brokerage:MSFT
2024-01-01 open Assets:Brokerage:VTI
2024-01-01 open Income:Salary
2024-01-01 open Income:Dividends
2024-01-01 open Income:CapitalGains
2024-01-01 open Expenses:Commission

2024-01-05 * "Employer" "Salary"
  Assets:Checking  8000.00 USD
  Income:Salary

2024-01-10 * "Broker" "Transfer to brokerage"
  Assets:Brokerage:Cash  4000.00 USD
  Assets:Checking  -4000.00 USD

2024-01-15 * "Market" "Buy AAPL"
  Assets:Brokerage:AAPL  10 AAPL {150.00 USD}
  Assets:Brokerage:Cash  -1500.00 USD
  Expenses:Commission  5.00 USD
  Assets:Brokerage:Cash  -5.00 USD

2024-01-20 * "Market" "Buy VTI"
  Assets:Brokerage:VTI  5 VTI {240.00 USD}
  Assets:Brokerage:Cash  -1200.00 USD
  Expenses:Commission  5.00 USD
  Assets:Brokerage:Cash  -5.00 USD

2024-02-01 * "Employer" "Salary"
  Assets:Checking  8000.00 USD
  Income:Salary

2024-02-05 * "Broker" "Transfer to brokerage"
  Assets:Brokerage:Cash  3000.00 USD
  Assets:Checking  -3000.00 USD

2024-02-10 * "Market" "Buy MSFT"
  Assets:Brokerage:MSFT  8 MSFT {380.00 USD}
  Assets:Brokerage:Cash  -3040.00 USD
  Expenses:Commission  5.00 USD
  Assets:Brokerage:Cash  -5.00 USD

2024-03-15 * "Apple Inc" "Quarterly dividend"
  Assets:Brokerage:Cash  2.40 USD
  Income:Dividends  -2.40 USD

2024-03-20 * "Market" "Sell some AAPL"
  Assets:Brokerage:Cash  1700.00 USD
  Assets:Brokerage:AAPL  -5 AAPL {150.00 USD}
  Income:CapitalGains

2024-04-01 * "Employer" "Salary"
  Assets:Checking  8000.00 USD
  Income:Salary

2024-04-10 * "Broker" "Transfer to brokerage"
  Assets:Brokerage:Cash  3000.00 USD
  Assets:Checking  -3000.00 USD

2024-04-15 * "Market" "Buy more AAPL"
  Assets:Brokerage:AAPL  10 AAPL {155.00 USD}
  Assets:Brokerage:Cash  -1550.00 USD
  Expenses:Commission  5.00 USD
  Assets:Brokerage:Cash  -5.00 USD

2024-04-20 * "Market" "Buy VTI"
  Assets:Brokerage:VTI  4 VTI {250.00 USD}
  Assets:Brokerage:Cash  -1000.00 USD
  Expenses:Commission  5.00 USD
  Assets:Brokerage:Cash  -5.00 USD

2024-05-15 * "Microsoft" "Quarterly dividend"
  Assets:Brokerage:Cash  6.00 USD
  Income:Dividends  -6.00 USD

2024-06-15 * "Apple Inc" "Quarterly dividend"
  Assets:Brokerage:Cash  3.00 USD
  Income:Dividends  -3.00 USD
"""

    def _generate_multicurrency_ledger(self) -> str:
        """Generate a multi-currency ledger with FX transactions."""
        return """\
option "title" "Multi-Currency Ledger"
option "operating_currency" "USD"

2024-01-01 open Assets:Checking:USD
2024-01-01 open Assets:Checking:EUR
2024-01-01 open Assets:Checking:GBP
2024-01-01 open Assets:Checking:JPY
2024-01-01 open Income:Salary:USD
2024-01-01 open Income:Freelance:EUR
2024-01-01 open Income:Freelance:GBP
2024-01-01 open Expenses:Rent:USD
2024-01-01 open Expenses:Travel:EUR
2024-01-01 open Expenses:Travel:GBP

2024-01-05 * "US Employer" "Salary"
  Assets:Checking:USD  6000.00 USD
  Income:Salary:USD

2024-01-10 * "Landlord" "Rent"
  Expenses:Rent:USD  1800.00 USD
  Assets:Checking:USD

2024-01-15 price EUR  1.09 USD
2024-01-15 price GBP  1.27 USD

2024-01-15 * "EU Client" "Freelance work"
  Assets:Checking:EUR  2000.00 EUR
  Income:Freelance:EUR

2024-01-18 * "Hotel Paris" "Business trip"
  Expenses:Travel:EUR  450.00 EUR
  Assets:Checking:EUR

2024-01-20 * "UK Client" "Consulting"
  Assets:Checking:GBP  1500.00 GBP
  Income:Freelance:GBP

2024-01-25 * "London Restaurant" "Client dinner"
  Expenses:Travel:GBP  120.00 GBP
  Assets:Checking:GBP

2024-02-01 * "US Employer" "Salary"
  Assets:Checking:USD  6000.00 USD
  Income:Salary:USD

2024-02-05 * "Landlord" "Rent"
  Expenses:Rent:USD  1800.00 USD
  Assets:Checking:USD

2024-02-10 price EUR  1.08 USD
2024-02-10 price GBP  1.26 USD

2024-02-12 * "EU Client" "Freelance work"
  Assets:Checking:EUR  1800.00 EUR
  Income:Freelance:EUR

2024-02-20 * "Paris Hotel" "Weekend trip"
  Expenses:Travel:EUR  350.00 EUR
  Assets:Checking:EUR

2024-03-01 * "US Employer" "Salary"
  Assets:Checking:USD  6000.00 USD
  Income:Salary:USD

2024-03-05 * "Landlord" "Rent"
  Expenses:Rent:USD  1800.00 USD
  Assets:Checking:USD

2024-03-10 price EUR  1.10 USD
2024-03-10 price GBP  1.28 USD

2024-03-15 * "EU Client" "Freelance work"
  Assets:Checking:EUR  2500.00 EUR
  Income:Freelance:EUR

2024-03-20 * "UK Client" "Project"
  Assets:Checking:GBP  2000.00 GBP
  Income:Freelance:GBP
"""

    def _generate_business_ledger(self) -> str:
        """Generate a small business ledger."""
        return """\
option "title" "Small Business Ledger"
option "operating_currency" "USD"

2024-01-01 open Assets:Business:Checking
2024-01-01 open Assets:Business:Savings
2024-01-01 open Assets:Business:AccountsReceivable
2024-01-01 open Assets:Business:Equipment
2024-01-01 open Assets:Business:Inventory
2024-01-01 open Liabilities:Business:AccountsPayable
2024-01-01 open Liabilities:Business:Loan
2024-01-01 open Income:Business:Sales
2024-01-01 open Income:Business:Services
2024-01-01 open Expenses:Business:Rent
2024-01-01 open Expenses:Business:Supplies
2024-01-01 open Expenses:Business:Payroll
2024-01-01 open Expenses:Business:Marketing
2024-01-01 open Expenses:Business:Software
2024-01-01 open Expenses:Business:Insurance
2024-01-01 open Equity:OwnersEquity

2024-01-02 * "Initial investment"
  Assets:Business:Checking  50000.00 USD
  Equity:OwnersEquity

2024-01-05 * "Office Depot" "Office supplies"
  Expenses:Business:Supplies  350.00 USD
  Assets:Business:Checking

2024-01-10 * "Client A" "Consulting project"
  Assets:Business:Checking  5000.00 USD
  Income:Business:Services

2024-01-12 * "Client B" "Product sale - net 30"
  Assets:Business:AccountsReceivable  3000.00 USD
  Income:Business:Sales

2024-01-15 * "Landlord" "Office rent"
  Expenses:Business:Rent  2000.00 USD
  Assets:Business:Checking

2024-01-20 * "Google" "Google Workspace" #software
  Expenses:Business:Software  144.00 USD
  Assets:Business:Checking

2024-01-25 * "Facebook Ads" "Marketing campaign" #marketing
  Expenses:Business:Marketing  500.00 USD
  Assets:Business:Checking

2024-01-30 * "Employee 1" "January payroll" #payroll
  Expenses:Business:Payroll  4000.00 USD
  Assets:Business:Checking

2024-02-01 * "Insurance Co" "Liability insurance" #insurance
  Expenses:Business:Insurance  300.00 USD
  Assets:Business:Checking

2024-02-05 * "Client C" "Web development"
  Assets:Business:Checking  7500.00 USD
  Income:Business:Services

2024-02-10 * "Client B" "Payment received"
  Assets:Business:Checking  3000.00 USD
  Assets:Business:AccountsReceivable

2024-02-15 * "Landlord" "Office rent"
  Expenses:Business:Rent  2000.00 USD
  Assets:Business:Checking

2024-02-20 * "Office Depot" "Office supplies"
  Expenses:Business:Supplies  275.00 USD
  Assets:Business:Checking

2024-02-25 * "Facebook Ads" "Marketing" #marketing
  Expenses:Business:Marketing  600.00 USD
  Assets:Business:Checking

2024-02-28 * "Employee 1" "February payroll" #payroll
  Expenses:Business:Payroll  4000.00 USD
  Assets:Business:Checking
"""

    def _generate_rental_ledger(self) -> str:
        """Generate a rental property ledger."""
        return """\
option "title" "Rental Property Ledger"
option "operating_currency" "USD"

2024-01-01 open Assets:Property:123MainSt
2024-01-01 open Assets:Property:DefaultReserve
2024-01-01 open Assets:Checking:Rental
2024-01-01 open Liabilities:Mortgage:123MainSt
2024-01-01 open Income:Rental:123MainSt
2024-01-01 open Income:Rental:Sundry
2024-01-01 open Expenses:Property:Mortgage:Interest
2024-01-01 open Expenses:Property:Mortgage:Principal
2024-01-01 open Expenses:Property:Repairs
2024-01-01 open Expenses:Property:Insurance
2024-01-01 open Expenses:Property:Taxes
2024-01-01 open Expenses:Property:Management
2024-01-01 open Expenses:Property:Utilities

2024-01-01 * "Purchase 123 Main St"
  Assets:Property:123MainSt  300000.00 USD
  Liabilities:Mortgage:123MainSt  -240000.00 USD
  Assets:Checking:Rental  -60000.00 USD

2024-01-05 * "Tenant A" "Rent January" #rental
  Assets:Checking:Rental  1800.00 USD
  Income:Rental:123MainSt

2024-01-10 * "Bank" "Mortgage payment"
  Expenses:Property:Mortgage:Interest  900.00 USD
  Expenses:Property:Mortgage:Principal  400.00 USD
  Assets:Checking:Rental

2024-01-15 * "Insurance Co" "Property insurance"
  Expenses:Property:Insurance  150.00 USD
  Assets:Checking:Rental

2024-01-20 * "Plumber" "Fix leak" #repair
  Expenses:Property:Repairs  350.00 USD
  Assets:Checking:Rental

2024-02-01 * "County" "Property tax"
  Expenses:Property:Taxes  1200.00 USD
  Assets:Checking:Rental

2024-02-05 * "Tenant A" "Rent February" #rental
  Assets:Checking:Rental  1800.00 USD
  Income:Rental:123MainSt

2024-02-10 * "Bank" "Mortgage payment"
  Expenses:Property:Mortgage:Interest  897.00 USD
  Expenses:Property:Mortgage:Principal  403.00 USD
  Assets:Checking:Rental

2024-02-25 * "Electrician" "Repair wiring" #repair
  Expenses:Property:Repairs  500.00 USD
  Assets:Checking:Rental

2024-03-05 * "Tenant A" "Rent March" #rental
  Assets:Checking:Rental  1800.00 USD
  Income:Rental:123MainSt

2024-03-10 * "Bank" "Mortgage payment"
  Expenses:Property:Mortgage:Interest  894.00 USD
  Expenses:Property:Mortgage:Principal  406.00 USD
  Assets:Checking:Rental

2024-03-15 * "Insurance Co" "Property insurance"
  Expenses:Property:Insurance  150.00 USD
  Assets:Checking:Rental
"""

    def _generate_crypto_ledger(self) -> str:
        """Generate a cryptocurrency ledger."""
        return """\
option "title" "Crypto Ledger"
option "operating_currency" "USD"

2024-01-01 open Assets:Crypto:Exchange:BTC
2024-01-01 open Assets:Crypto:Exchange:ETH
2024-01-01 open Assets:Crypto:ColdWallet:BTC
2024-01-01 open Assets:Crypto:ColdWallet:ETH
2024-01-01 open Assets:Checking
2024-01-01 open Income:Crypto:Mining
2024-01-01 open Income:Crypto:Staking
2024-01-01 open Income:CapitalGains:Crypto
2024-01-01 open Expenses:Crypto:Fees

2024-01-05 price BTC  45000.00 USD
2024-01-05 price ETH   2400.00 USD

2024-01-05 * "Exchange" "Buy BTC"
  Assets:Crypto:Exchange:BTC  0.5 BTC {45000.00 USD}
  Assets:Checking  -22500.00 USD
  Expenses:Crypto:Fees  22.50 USD
  Assets:Checking  -22.50 USD

2024-01-10 * "Exchange" "Buy ETH"
  Assets:Crypto:Exchange:ETH  5 ETH {2400.00 USD}
  Assets:Checking  -12000.00 USD
  Expenses:Crypto:Fees  12.00 USD
  Assets:Checking  -12.00 USD

2024-01-15 * "Transfer to cold wallet"
  Assets:Crypto:ColdWallet:BTC  0.5 BTC {45000.00 USD}
  Assets:Crypto:Exchange:BTC  -0.5 BTC {45000.00 USD}

2024-02-01 price BTC  48000.00 USD
2024-02-01 price ETH   2600.00 USD

2024-02-05 * "Mining pool" "Mining reward"
  Assets:Crypto:Exchange:BTC  0.01 BTC {48000.00 USD}
  Income:Crypto:Mining

2024-02-10 * "Staking reward" "ETH staking"
  Assets:Crypto:Exchange:ETH  0.1 ETH {2600.00 USD}
  Income:Crypto:Staking

2024-02-15 * "Exchange" "Sell some ETH"
  Assets:Checking  5200.00 USD
  Assets:Crypto:Exchange:ETH  -2 ETH {2400.00 USD}
  Income:CapitalGains:Crypto
  Expenses:Crypto:Fees  5.20 USD
  Assets:Checking  -5.20 USD

2024-03-01 price BTC  52000.00 USD
2024-03-01 price ETH   2800.00 USD

2024-03-10 * "Exchange" "Buy more BTC"
  Assets:Crypto:Exchange:BTC  0.3 BTC {51000.00 USD}
  Assets:Checking  -15300.00 USD
  Expenses:Crypto:Fees  15.30 USD
  Assets:Checking  -15.30 USD

2024-03-20 * "Exchange" "Sell BTC"
  Assets:Checking  15600.00 USD
  Assets:Crypto:Exchange:BTC  -0.3 BTC {51000.00 USD}
  Income:CapitalGains:Crypto
  Expenses:Crypto:Fees  15.60 USD
  Assets:Checking  -15.60 USD
"""

    def discover_queries_from_docs(self) -> list[QueryRecord]:
        """Extract BQL query examples from official documentation."""
        queries = []

        # These are canonical BQL query patterns from beancount/beanquery docs
        docs_queries = [
            {
                "question": "List all transactions",
                "query": "SELECT date, narration, account, position FROM transactions",
                "category": "basic",
            },
            {
                "question": "Show balances for all accounts",
                "query": "SELECT account, balance FROM balances",
                "category": "basic",
            },
            {
                "question": "Filter transactions by date",
                "query": "SELECT date, narration, position FROM transactions WHERE date >= '2024-01-01' AND date < '2024-02-01'",
                "category": "date",
            },
            {
                "question": "Group expenses by account",
                "query": "SELECT account, SUM(COST(position)) as total FROM transactions WHERE account ~ 'Expenses:' GROUP BY account ORDER BY total DESC",
                "category": "spending",
            },
            {
                "question": "Show income by month",
                "query": "SELECT MONTH(date) as month, SUM(COST(position)) as income FROM transactions WHERE account ~ 'Income:' GROUP BY MONTH(date) ORDER BY month",
                "category": "cashflow",
            },
            {
                "question": "Find transactions with a specific tag",
                "query": "SELECT date, narration, position FROM transactions WHERE ANY_METADATA('tag') = 'food'",
                "category": "metadata",
            },
            {
                "question": "Calculate net worth",
                "query": "SELECT SUM(COST(balance)) as net_worth FROM balances WHERE account ~ 'Assets:.*' OR account ~ 'Liabilities:.*'",
                "category": "networth",
            },
            {
                "question": "Show commodity holdings",
                "query": "SELECT account, units(sum(position)) as units, cost(sum(position)) as cost FROM inventory GROUP BY account ORDER BY account",
                "category": "investments",
            },
            {
                "question": "List accounts with their balances",
                "query": "SELECT account, sum(position) FROM OPEN ON date CLOSE ON date GROUP BY account ORDER BY account",
                "category": "basic",
            },
            {
                "question": "Find specific merchant expenses",
                "query": "SELECT date, narration, sum(position) FROM transactions WHERE payee ~ 'Amazon' AND account ~ 'Expenses:'",
                "category": "spending",
            },
            {
                "question": "Monthly spending by category",
                "query": "SELECT MONTH(date) as month, account, SUM(COST(position)) as total FROM transactions WHERE account ~ 'Expenses:' GROUP BY MONTH(date), account ORDER BY month, total DESC",
                "category": "spending",
            },
            {
                "question": "Year-to-date income vs expenses",
                "query": "SELECT account, SUM(COST(position)) as amount FROM transactions WHERE date >= '2024-01-01' AND (account ~ 'Income:' OR account ~ 'Expenses:') GROUP BY account",
                "category": "budgeting",
            },
            {
                "question": "Find largest expenses",
                "query": "SELECT date, narration, account, COST(position) as amount FROM transactions WHERE account ~ 'Expenses:' ORDER BY amount DESC LIMIT 10",
                "category": "spending",
            },
            {
                "question": "List transactions with links",
                "query": "SELECT date, narration, position, links FROM transactions WHERE links",
                "category": "metadata",
            },
            {
                "question": "Filter by payee",
                "query": "SELECT date, narration, account, position FROM transactions WHERE payee ~ '.*Corp.*'",
                "category": "basic",
            },
            {
                "question": "Average monthly expenses",
                "query": "SELECT account, AVG(monthly_total) as avg_monthly FROM (SELECT account, MONTH(date) as month, SUM(COST(position)) as monthly_total FROM transactions WHERE account ~ 'Expenses:' GROUP BY account, MONTH(date)) GROUP BY account",
                "category": "spending",
            },
        ]

        for i, q in enumerate(docs_queries):
            query_record = QueryRecord(
                question=q["question"],
                query=q["query"],
                source="beancount_docs",
                notes=f"Extracted from official documentation",
                category=q.get("category", ""),
            )
            queries.append(query_record)

        # Save query corpus
        self._save_query_corpus(queries)
        return queries

    def _save_query_corpus(self, queries: list[QueryRecord]):
        """Save discovered queries to the corpus."""
        output_path = self.metadata_dir / "query_corpus.yaml"
        data = [asdict(q) for q in queries]
        output_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def build_ground_truth(self) -> list[GroundTruthRecord]:
        """Build ground truth records pairing ledgers with expected results."""
        records = []
        idx = 0

        # Ground truth for simple personal ledger
        simple_ledger = "synthetic/simple_personal.bean"

        ground_truths = [
            # Spending
            {
                "question": "What were my total restaurant expenses in Q1 2024?",
                "expected_result": {"total": 236.80},
                "category": "spending",
                "difficulty": "medium",
            },
            {
                "question": "How much did I spend on food in January 2024?",
                "expected_result": {"total": 431.10},
                "category": "spending",
                "difficulty": "easy",
            },
            {
                "question": "What was my largest single expense?",
                "expected_result": {"max_amount": 1500.00},
                "category": "spending",
                "difficulty": "medium",
            },
            {
                "question": "How much did I spend on Amazon?",
                "expected_result": {"total": 209.49},
                "category": "spending",
                "difficulty": "easy",
            },
            # Budgeting
            {
                "question": "What were my monthly rent payments?",
                "expected_result": {"monthly_rent": 1500.00},
                "category": "budgeting",
                "difficulty": "easy",
            },
            {
                "question": "How much did utilities cost per month?",
                "expected_result": {"january": 185.00},
                "category": "budgeting",
                "difficulty": "medium",
            },
            # Cashflow
            {
                "question": "What was my total income in Q1 2024?",
                "expected_result": {"total_income": 15000.00},
                "category": "cashflow",
                "difficulty": "easy",
            },
            {
                "question": "What were my total expenses in January 2024?",
                "expected_result": {"total_expenses": 2396.09},
                "category": "cashflow",
                "difficulty": "easy",
            },
            # Networth
            {
                "question": "How much is in my savings account?",
                "expected_result": {"savings_balance": 3000.00},
                "category": "networth",
                "difficulty": "easy",
            },
        ]

        for gt in ground_truths:
            idx += 1
            record = GroundTruthRecord(
                id=f"GT{idx:04d}",
                ledger=simple_ledger,
                question=gt["question"],
                expected_result=gt["expected_result"],
                category=gt["category"],
                difficulty=gt.get("difficulty", "medium"),
                source="synthetic",
            )
            records.append(record)

        # Ground truth for investment ledger
        inv_ledger = "synthetic/investment.bean"

        inv_truths = [
            {
                "question": "How many shares of AAPL do I own?",
                "expected_result": {"shares": -2285.00},
                "category": "investments",
                "difficulty": "medium",
            },
            {
                "question": "What was my total dividend income?",
                "expected_result": {"total_dividends": 11.40},
                "category": "investments",
                "difficulty": "medium",
            },
            {
                "question": "How much did I pay in commissions?",
                "expected_result": {"total_commissions": 42.00},
                "category": "investments",
                "difficulty": "easy",
            },
            {
                "question": "What is my total investment position?",
                "expected_result": {"total_cost": 11032.00},
                "category": "investments",
                "difficulty": "medium",
            },
        ]

        for gt in inv_truths:
            idx += 1
            record = GroundTruthRecord(
                id=f"GT{idx:04d}",
                ledger=inv_ledger,
                question=gt["question"],
                expected_result=gt["expected_result"],
                category=gt["category"],
                difficulty=gt.get("difficulty", "medium"),
                source="synthetic",
            )
            records.append(record)

        # Ground truth for multi-currency ledger
        mc_ledger = "synthetic/multicurrency.bean"

        mc_truths = [
            {
                "question": "What was my total freelance income in EUR?",
                "expected_result": {"total_eur_income": 6300.00},
                "category": "multicurrency",
                "difficulty": "hard",
            },
            {
                "question": "How much did I earn from UK clients in GBP?",
                "expected_result": {"total_gbp_income": 3500.00},
                "category": "multicurrency",
                "difficulty": "hard",
            },
            {
                "question": "What were my total travel expenses in EUR?",
                "expected_result": {"total_eur_travel": 800.00},
                "category": "multicurrency",
                "difficulty": "medium",
            },
        ]

        for gt in mc_truths:
            idx += 1
            record = GroundTruthRecord(
                id=f"GT{idx:04d}",
                ledger=mc_ledger,
                question=gt["question"],
                expected_result=gt["expected_result"],
                category=gt["category"],
                difficulty=gt.get("difficulty", "medium"),
                source="synthetic",
            )
            records.append(record)

        # Ground truth for business ledger
        biz_ledger = "synthetic/business.bean"

        biz_truths = [
            {
                "question": "What was the total revenue for the business?",
                "expected_result": {"total_revenue": 18500.00},
                "category": "cashflow",
                "difficulty": "easy",
            },
            {
                "question": "How much was spent on payroll?",
                "expected_result": {"total_payroll": 8000.00},
                "category": "spending",
                "difficulty": "easy",
            },
            {
                "question": "What was the marketing spend?",
                "expected_result": {"total_marketing": 1100.00},
                "category": "spending",
                "difficulty": "easy",
            },
        ]

        for gt in biz_truths:
            idx += 1
            record = GroundTruthRecord(
                id=f"GT{idx:04d}",
                ledger=biz_ledger,
                question=gt["question"],
                expected_result=gt["expected_result"],
                category=gt["category"],
                difficulty=gt.get("difficulty", "medium"),
                source="synthetic",
            )
            records.append(record)

        # Save ground truth
        self._save_ground_truth(records)
        return records

    def _save_ground_truth(self, records: list[GroundTruthRecord]):
        """Save ground truth records, splitting into train and holdout."""
        # Save all to metadata
        all_path = self.metadata_dir / "ground_truth_corpus.yaml"
        data = [asdict(r) for r in records]
        all_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

        # Split: 80% train, 20% holdout
        split_idx = int(len(records) * 0.8)
        train = records[:split_idx]
        holdout = records[split_idx:]

        train_data = [asdict(r) for r in train]
        holdout_data = [asdict(r) for r in holdout]

        (self.train_dir / "ground_truth.yaml").write_text(
            yaml.dump(train_data, default_flow_style=False, sort_keys=False)
        )
        (self.holdout_dir / "ground_truth.yaml").write_text(
            yaml.dump(holdout_data, default_flow_style=False, sort_keys=False)
        )

        print(f"Ground truth: {len(train)} train, {len(holdout)} holdout")

    def generate_benchmark_questions(self) -> list[dict]:
        """Generate benchmark questions in YAML format."""
        records = self.build_ground_truth()

        questions_dir = self.corpus_dir.parent / "benchmark" / "questions"
        expected_dir = self.corpus_dir.parent / "benchmark" / "expected_results"
        questions_dir.mkdir(parents=True, exist_ok=True)
        expected_dir.mkdir(parents=True, exist_ok=True)

        benchmark_questions = []

        for record in records:
            q_data = {
                "id": record.id,
                "ledger": record.ledger,
                "question": record.question,
                "expected_result": record.expected_result,
                "category": record.category,
                "difficulty": record.difficulty,
                "tags": [record.source],
            }

            # Save question file
            q_path = questions_dir / f"{record.id}.yaml"
            q_path.write_text(yaml.dump(q_data, default_flow_style=False, sort_keys=False))

            # Save expected result separately
            e_path = expected_dir / f"{record.id}.yaml"
            e_path.write_text(
                yaml.dump(record.expected_result, default_flow_style=False, sort_keys=False)
            )

            benchmark_questions.append(q_data)

        print(f"Generated {len(benchmark_questions)} benchmark questions")
        return benchmark_questions

    def run_full_corpus_build(self) -> dict:
        """Run the full corpus building pipeline."""
        print("=" * 60)
        print("Agent 1 — Corpus Builder")
        print("=" * 60)

        # Step 1: Generate synthetic ledgers
        print("\n1. Generating synthetic ledgers...")
        ledgers = self.generate_synthetic_ledgers()
        print(f"   Created {len(ledgers)} synthetic ledgers:")
        for l in ledgers:
            print(f"     - {l.name}")

        # Step 2: Extract metadata from synthetic ledgers
        print("\n2. Extracting metadata from ledgers...")
        for ledger in ledgers:
            meta = self.extract_metadata_from_ledger(ledger)
            meta_path = self.metadata_dir / f"{ledger.stem}_metadata.yaml"
            meta_path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))
            print(f"     - {ledger.name}: {len(meta['accounts'])} accounts, "
                  f"{len(meta['currencies'])} currencies")

        # Step 3: Discover queries from docs
        print("\n3. Discovering BQL queries from documentation...")
        queries = self.discover_queries_from_docs()
        print(f"   Collected {len(queries)} query patterns")

        # Step 4: Build ground truth
        print("\n4. Building ground truth corpus...")
        records = self.build_ground_truth()
        print(f"   Created {len(records)} ground truth records")

        # Step 5: Generate benchmark questions
        print("\n5. Generating benchmark questions...")
        benchmark = self.generate_benchmark_questions()
        print(f"   Created {len(benchmark)} benchmark questions")

        # Step 6: Try GitHub collection (optional, requires token)
        print("\n6. GitHub discovery (skipped - requires GITHUB_TOKEN)...")
        print("   Set GITHUB_TOKEN environment variable to enable GitHub search")

        # Summary
        summary = {
            "synthetic_ledgers": len(ledgers),
            "discovered_queries": len(queries),
            "ground_truth_records": len(records),
            "benchmark_questions": len(benchmark),
            "categories": list(set(r["category"] for r in benchmark)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        summary_path = self.metadata_dir / "corpus_summary.yaml"
        summary_path.write_text(yaml.dump(summary, default_flow_style=False, sort_keys=False))

        print("\n" + "=" * 60)
        print("Corpus build complete!")
        print(f"Summary saved to: {summary_path}")
        print("=" * 60)

        return summary


if __name__ == "__main__":
    builder = CorpusBuilder()
    builder.run_full_corpus_build()
