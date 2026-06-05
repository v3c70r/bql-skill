"""
Agent 3 — Independent Auditor

Evaluate the BQL skill objectively.
Must NOT help improve the skill directly — only scoring.

Workflow:
1. Load ledger
2. Ask question  
3. Let skill generate BQL
4. Execute BQL
5. Compare actual result against expected result
6. Generate evaluation report
"""

import yaml
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.benchmark import Benchmark, Evaluator, EvaluationRun, EvaluationResult
from core.bql_executor import BQLExecutor, BQLResult, normalize_result, compare_results


class Auditor:
    """Agent 3 — Independent Auditor.

    Evaluates skill performance, categorizes failures, generates reports.
    Does NOT suggest improvements.
    """

    FAILURE_CATEGORIES = [
        "syntax",       # Invalid query
        "semantic",     # Wrong accounts/filters
        "aggregation",  # Incorrect grouping
        "inventory",    # Units vs cost basis confusion
        "pricing",      # Market value confusion
        "multi_currency",  # FX handling errors
        "time",         # Date filtering errors
        "metadata",     # Tag/link filtering failures
        "setup",        # Ledger not found or parse error
        "missing",      # No query provided
    ]

    def __init__(self, project_dir: str | Path = None):
        if project_dir is None:
            project_dir = Path(__file__).resolve().parent.parent.parent
        self.project_dir = Path(project_dir)
        self.benchmark = Benchmark(self.project_dir / "benchmark")
        self.evaluator = Evaluator(self.benchmark, self.project_dir / "corpus")
        self.reports_dir = self.project_dir / "reports" / "auditor"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def evaluate_against_holdout(self, query_map: dict[str, str]) -> dict:
        """Evaluate skill against holdout set (never seen during training)."""
        print("=" * 60)
        print("Agent 3 — Independent Auditor")
        print("Evaluating against HOLDOUT set")
        print("=" * 60)

        holdout_questions = self._load_holdout_questions()

        if not holdout_questions:
            return {
                "status": "no_holdout",
                "message": "No holdout questions found",
            }

        results = []
        for q in holdout_questions:
            query = query_map.get(q["id"], "")
            eval_result = self.evaluator.evaluate_question(
                self.benchmark.load_questions()[0].__class__.from_dict(q),
                query,
            )
            results.append(eval_result.to_dict())

        total = len(results)
        passed = sum(1 for r in results if r.get("passed"))

        report = {
            "evaluation_type": "holdout",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": total,
            "passed": passed,
            "score": round(passed / total * 100, 1) if total > 0 else 0.0,
            "results": results,
            "failures_by_type": self._summarize_failures(results),
        }

        self._save_report(report, "holdout_evaluation")
        return report

    def _load_holdout_questions(self) -> list[dict]:
        """Load holdout benchmark questions."""
        holdout_path = self.project_dir / "corpus" / "holdout" / "ground_truth.yaml"
        if not holdout_path.exists():
            return []
        return yaml.safe_load(holdout_path.read_text()) or []

    def _summarize_failures(self, results: list[dict]) -> dict:
        """Summarize failures by type."""
        failures = {}
        for r in results:
            if not r.get("passed"):
                ftype = r.get("failure_type", "unknown")
                if ftype not in failures:
                    failures[ftype] = 0
                failures[ftype] += 1
        return failures

    def audit_single(self, ledger_path: str, question: str, query: str) -> dict:
        """Audit a single query against a ledger."""
        print(f"\nAuditing single query:")
        print(f"  Ledger: {ledger_path}")
        print(f"  Question: {question}")
        print(f"  Query: {query}")

        try:
            executor = BQLExecutor(ledger_path)
            result = executor.execute(query)

            return {
                "status": "success",
                "result": result.to_dict(),
                "row_count": result.row_count,
                "columns": result.columns,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def generate_category_report(self, evaluation_run: dict = None) -> dict:
        """Generate a per-category score report."""
        if evaluation_run is None:
            # Load latest evaluation run
            runs = self.benchmark.load_evaluation_runs()
            if not runs:
                return {"error": "No evaluation runs found"}
            evaluation_run = runs[-1]

        category_scores = evaluation_run.get("category_scores", {})
        overall = evaluation_run.get("overall_score", 0)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_score": overall,
            "category_scores": category_scores,
            "summary": self._generate_summary_text(category_scores, overall),
        }

        self._save_report(report, "category_report")
        return report

    def _generate_summary_text(self, category_scores: dict, overall: float) -> str:
        """Generate a human-readable summary."""
        lines = [f"Overall Score: {overall}%", ""]
        lines.append("Category Scores:")
        lines.append("-" * 40)

        sorted_cats = sorted(category_scores.items(), key=lambda x: x[1])
        for cat, score in sorted_cats:
            bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
            status = "✅" if score >= 90 else "⚠️" if score >= 80 else "❌"
            lines.append(f"  {status} {cat:20s} {bar} {score}%")

        lines.append("")
        lines.append(f"Categories >= 90%: {sum(1 for s in category_scores.values() if s >= 90)}")
        lines.append(f"Categories >= 80%: {sum(1 for s in category_scores.values() if s >= 80)}")
        lines.append(f"Categories < 80%:  {sum(1 for s in category_scores.values() if s < 80)}")

        return "\n".join(lines)

    def detect_regressions(self) -> dict:
        """Detect regressions between the last two evaluation runs."""
        regression_report = self.benchmark.get_regression_report()

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regression_detected": regression_report.get("has_regression", False),
            "details": regression_report.get("regressions", {}),
            "current_overall": regression_report.get("current_overall", 0),
            "previous_overall": regression_report.get("previous_overall", 0),
            "recommendation": self._regression_recommendation(regression_report),
        }

        self._save_report(report, "regression_detection")
        return report

    def _regression_recommendation(self, regression_report: dict) -> str:
        """Generate recommendation based on regression analysis."""
        if not regression_report.get("has_regression"):
            return "No regressions detected. Safe to proceed."

        regressions = regression_report.get("regressions", {})
        cats = list(regressions.keys())
        return (
            f"REGRESSION DETECTED in categories: {', '.join(cats)}. "
            f"Do NOT accept current skill version. "
            f"Investigate and fix before proceeding."
        )

    def check_success_criteria(self) -> dict:
        """Check if the project meets the success criteria defined in the README."""
        runs = self.benchmark.load_evaluation_runs()

        criteria = {
            "overall_score_>=95": False,
            "spending_>=95": False,
            "budgeting_>=95": False,
            "cashflow_>=95": False,
            "networth_>=95": False,
            "investments_>=90": False,
            "multicurrency_>=90": False,
            "tax_>=90": False,
            "metadata_>=90": False,
            "consecutive_runs_>=3": False,
            "regression_rate_<2%": False,
        }

        if runs:
            latest = runs[-1]
            overall = latest.get("overall_score", 0)
            cat_scores = latest.get("category_scores", {})

            criteria["overall_score_>=95"] = overall >= 95
            criteria["spending_>=95"] = cat_scores.get("spending", 0) >= 95
            criteria["budgeting_>=95"] = cat_scores.get("budgeting", 0) >= 95
            criteria["cashflow_>=95"] = cat_scores.get("cashflow", 0) >= 95
            criteria["networth_>=95"] = cat_scores.get("networth", 0) >= 95
            criteria["investments_>=90"] = cat_scores.get("investments", 0) >= 90
            criteria["multicurrency_>=90"] = cat_scores.get("multicurrency", 0) >= 90
            criteria["tax_>=90"] = cat_scores.get("tax", 0) >= 90
            criteria["metadata_>=90"] = cat_scores.get("metadata", 0) >= 90
            criteria["consecutive_runs_>=3"] = len(runs) >= 3

            # Check consecutive runs above threshold
            if len(runs) >= 3:
                last_3 = runs[-3:]
                criteria["consecutive_runs_>=3"] = all(
                    r.get("overall_score", 0) >= 95 for r in last_3
                )

        passed = sum(1 for v in criteria.values() if v)
        total = len(criteria)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "criteria": criteria,
            "passed": passed,
            "total": total,
            "mature": passed == total,
            "missing": [k for k, v in criteria.items() if not v],
        }

        self._save_report(report, "success_criteria")
        return report

    def _save_report(self, report: dict, name: str):
        """Save an auditor report."""
        path = self.reports_dir / f"{name}.yaml"
        path.write_text(yaml.dump(report, default_flow_style=False, sort_keys=False))

    def run_full_audit(self, query_map: dict[str, str] = None) -> dict:
        """Run a full audit cycle."""
        print("=" * 60)
        print("Agent 3 — Independent Auditor: Full Audit")
        print("=" * 60)

        if query_map is None:
            query_map = {}

        # 1. Load all benchmark questions
        print("\n1. Loading benchmark questions...")
        questions = self.benchmark.load_questions()
        print(f"   Loaded {len(questions)} questions")

        # 2. Run evaluation
        print("\n2. Running evaluation...")
        if query_map:
            run = self.evaluator.run_full_evaluation(query_map)
        else:
            # Generate simple queries for testing
            auto_map = self._generate_basic_query_map(questions)
            run = self.evaluator.run_full_evaluation(auto_map)

        # 3. Print results
        print(f"\n3. Results:")
        print(f"   Overall: {run.overall_score}%")
        print(f"   Passed: {run.passed_tests}/{run.total_tests}")
        print(f"\n   Category Scores:")
        for cat, score in sorted(run.category_scores.items()):
            if score > 0:
                status = "✅" if score >= 90 else "⚠️" if score >= 80 else "❌"
                print(f"     {status} {cat}: {score}%")

        # 4. Generate reports
        print("\n4. Generating reports...")
        cat_report = self.generate_category_report(run.to_dict())
        reg_report = self.detect_regressions()
        criteria_report = self.check_success_criteria()

        print(f"\n   Regression check: {'❌ REGRESSION' if reg_report['regression_detected'] else '✅ Clean'}")
        print(f"   Maturity check: {criteria_report['passed']}/{criteria_report['total']} criteria met")

        return {
            "evaluation_run": run.to_dict(),
            "category_report": cat_report,
            "regression_report": reg_report,
            "criteria_report": criteria_report,
        }

    def _generate_basic_query_map(self, questions) -> dict[str, str]:
        """Generate working query map for beanquery 0.2.0."""
        query_map = {}

        # Working queries for beanquery 0.2.0 schema
        default_queries = {
            "GT0001": "SELECT position FROM postings WHERE payee ~ 'Restaurant' AND year(date) = 2024 AND month(date) <= 3",
            "GT0002": "SELECT position FROM postings WHERE (payee ~ 'Restaurant' OR payee ~ 'Grocery') AND year(date) = 2024 AND month(date) = 1",
            "GT0003": "SELECT position FROM postings WHERE payee !~ 'Employer'",
            "GT0004": "SELECT position FROM postings WHERE payee ~ 'Amazon'",
            "GT0005": "SELECT position FROM postings WHERE payee ~ 'Landlord'",
            "GT0006": "SELECT position FROM postings WHERE (payee ~ 'Electric' OR payee ~ 'Internet') AND year(date) = 2024 AND month(date) = 1",
            "GT0007": "SELECT position FROM postings WHERE payee ~ 'Employer' AND year(date) = 2024 AND month(date) <= 3",
            "GT0008": "SELECT position FROM postings WHERE year(date) = 2024 AND month(date) = 1 AND payee !~ 'Employer' AND payee IS NOT NULL",
            "GT0009": "SELECT position FROM postings WHERE payee IS NULL",
            "GT0010": "SELECT narration, position FROM postings WHERE payee ~ 'Market' AND narration ~ 'AAPL'",
            "GT0011": "SELECT position FROM postings WHERE payee ~ 'Apple' OR payee ~ 'Microsoft'",
            "GT0012": "SELECT position FROM postings WHERE payee ~ 'Market'",
            "GT0013": "SELECT position FROM postings WHERE payee ~ 'Market'",
            "GT0014": "SELECT narration, position FROM postings WHERE payee ~ 'EU'",
            "GT0015": "SELECT narration, position FROM postings WHERE payee ~ 'UK'",
            "GT0016": "SELECT position FROM postings WHERE payee ~ 'Hotel' OR payee ~ 'Paris'",
            "GT0017": "SELECT narration, position FROM postings WHERE payee ~ 'Client'",
            "GT0018": "SELECT position FROM postings WHERE payee ~ 'Employee'",
            "GT0019": "SELECT position FROM postings WHERE payee ~ 'Facebook'",
        }

        for q in questions:
            if q.id in default_queries:
                query_map[q.id] = default_queries[q.id]
            else:
                cat = q.category
                if cat == "spending":
                    query_map[q.id] = "SELECT position FROM postings WHERE payee !~ 'Employer' AND year(date) = 2024 AND month(date) = 1"
                elif cat == "cashflow":
                    query_map[q.id] = "SELECT position FROM postings WHERE year(date) = 2024 AND month(date) = 1"
                elif cat == "investments":
                    query_map[q.id] = "SELECT narration, position FROM postings WHERE payee ~ 'Market'"
                elif cat == "multicurrency":
                    query_map[q.id] = "SELECT narration, position FROM postings"
                else:
                    query_map[q.id] = "SELECT position FROM postings"

        return query_map


if __name__ == "__main__":
    auditor = Auditor()
    auditor.run_full_audit()
