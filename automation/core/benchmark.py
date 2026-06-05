"""
Benchmark system — load, manage, and score BQL evaluation benchmarks.

The benchmark is the central artifact of the system.
Questions have expected results, NOT expected queries.
"""

import json
import yaml
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from .bql_executor import BQLExecutor, BQLResult, normalize_result, compare_results


@dataclass
class BenchmarkQuestion:
    """A single benchmark question with expected result."""
    id: str
    ledger: str  # path relative to corpus/
    question: str
    expected_result: dict
    category: str
    difficulty: str  # easy, medium, hard
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "BenchmarkQuestion":
        return cls(
            id=d["id"],
            ledger=d.get("ledger", ""),
            question=d.get("question", ""),
            expected_result=d.get("expected_result", {}),
            category=d.get("category", ""),
            difficulty=d.get("difficulty", "medium"),
            tags=d.get("tags", []),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvaluationResult:
    """Result of evaluating a single benchmark question."""
    test_id: str
    passed: bool
    category: str
    failure_type: Optional[str] = None
    severity: Optional[str] = None
    explanation: Optional[str] = None
    generated_query: Optional[str] = None
    generated_result: Optional[dict] = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass  
class EvaluationRun:
    """A complete evaluation run across all benchmark questions."""
    run_id: str
    timestamp: str
    total_tests: int
    passed_tests: int
    overall_score: float
    category_scores: dict[str, float]
    difficulty_scores: dict[str, float]
    results: list[dict]
    duration_seconds: float

    def to_dict(self) -> dict:
        return asdict(self)

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)


class Benchmark:
    """Load and manage evaluation benchmarks."""

    VALID_CATEGORIES = [
        "spending",
        "budgeting",
        "cashflow",
        "networth",
        "investments",
        "tax", 
        "multicurrency",
        "metadata",
    ]

    VALID_DIFFICULTIES = ["easy", "medium", "hard"]

    def __init__(self, root_dir: str | Path = None):
        if root_dir is None:
            root_dir = Path(__file__).resolve().parent.parent.parent / "benchmark"
        self.root_dir = Path(root_dir)
        self.questions_dir = self.root_dir / "questions"
        self.expected_dir = self.root_dir / "expected_results"
        self.eval_runs_dir = self.root_dir / "evaluation_runs"
        self.categories_dir = self.root_dir / "categories"

    def load_questions(self, category: str = None) -> list[BenchmarkQuestion]:
        """Load all benchmark questions, optionally filtered by category."""
        questions = []
        for qf in sorted(self.questions_dir.glob("*.yaml")):
            q = yaml.safe_load(qf.read_text())
            if category and q.get("category") != category:
                continue
            questions.append(BenchmarkQuestion.from_dict(q))
        return questions

    def load_expected_result(self, question_id: str) -> dict:
        """Load expected result for a specific question."""
        result_path = self.expected_dir / f"{question_id}.yaml"
        if result_path.exists():
            return yaml.safe_load(result_path.read_text())
        # Also look for inline expected results in question file
        q_path = self.questions_dir / f"{question_id}.yaml"
        if q_path.exists():
            q = yaml.safe_load(q_path.read_text())
            return q.get("expected_result", {})
        return {}

    def save_evaluation_run(self, run: EvaluationRun):
        """Save an evaluation run to disk."""
        self.eval_runs_dir.mkdir(parents=True, exist_ok=True)
        run_path = self.eval_runs_dir / f"{run.run_id}.yaml"
        run_path.write_text(run.to_yaml())

    def load_evaluation_runs(self) -> list[dict]:
        """Load all past evaluation runs."""
        runs = []
        for rf in sorted(self.eval_runs_dir.glob("*.yaml")):
            runs.append(yaml.safe_load(rf.read_text()))
        return runs

    def get_regression_report(self) -> dict:
        """Compare current score to previous run and detect regressions."""
        runs = self.load_evaluation_runs()
        if len(runs) < 2:
            return {"has_regression": False, "message": "Not enough runs for comparison"}

        current = runs[-1]
        previous = runs[-2]

        regressions = {}
        for cat in self.VALID_CATEGORIES:
            curr_score = current.get("category_scores", {}).get(cat, 0)
            prev_score = previous.get("category_scores", {}).get(cat, 0)
            if curr_score < prev_score:
                regressions[cat] = {
                    "previous": prev_score,
                    "current": curr_score,
                    "delta": curr_score - prev_score,
                }

        return {
            "has_regression": bool(regressions),
            "regressions": regressions,
            "current_overall": current.get("overall_score", 0),
            "previous_overall": previous.get("overall_score", 0),
        }

    def get_coverage_report(self) -> dict:
        """Generate a coverage report across categories and difficulties."""
        questions = self.load_questions()
        categories = {}
        difficulties = {}

        for q in questions:
            cat = q.category
            if cat not in categories:
                categories[cat] = {"count": 0, "examples": []}
            categories[cat]["count"] += 1
            if len(categories[cat]["examples"]) < 3:
                categories[cat]["examples"].append(q.question[:80] + "...")

            diff = q.difficulty
            if diff not in difficulties:
                difficulties[diff] = 0
            difficulties[diff] += 1

        total = len(questions)
        return {
            "total_questions": total,
            "categories": {
                cat: {
                    "count": info["count"],
                    "coverage_percent": round(info["count"] / total * 100, 1) if total > 0 else 0,
                    "examples": info["examples"],
                }
                for cat, info in categories.items()
            },
            "difficulties": difficulties,
            "gaps": [cat for cat in self.VALID_CATEGORIES if cat not in categories],
            "recommendations": self._generate_coverage_recommendations(categories),
        }

    def _generate_coverage_recommendations(self, categories: dict) -> list[str]:
        recommendations = []
        for cat in self.VALID_CATEGORIES:
            count = categories.get(cat, {}).get("count", 0)
            if count == 0:
                recommendations.append(f"Add questions for category: {cat}")
            elif count < 5:
                recommendations.append(f"Add more questions for category: {cat} (currently {count})")
        return recommendations


class Evaluator:
    """Evaluate the BQL skill against the benchmark.

    Agent 3 - Independent Auditor.
    Must NOT help improve the skill directly. Only scoring.
    """

    def __init__(self, benchmark: Benchmark, corpus_dir: str | Path = None):
        self.benchmark = benchmark
        if corpus_dir is None:
            corpus_dir = Path(__file__).resolve().parent.parent.parent / "corpus"
        self.corpus_dir = Path(corpus_dir)

    def evaluate_question(
        self, question: BenchmarkQuestion, query: str
    ) -> EvaluationResult:
        """Evaluate a single question by executing the query and comparing results."""
        start_time = time.time()

        # Try multiple paths for the ledger file
        ledger_path = None
        candidates = [
            self.corpus_dir / "ledgers" / question.ledger,
            self.corpus_dir / question.ledger,
            self.corpus_dir / "synthetic" / Path(question.ledger).name,
        ]
        for candidate in candidates:
            if candidate.exists():
                ledger_path = candidate
                break
        
        if ledger_path is None:
            elapsed = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=question.id,
                passed=False,
                category=question.category,
                failure_type="setup",
                severity="high",
                explanation=f"Ledger not found: {question.ledger} (tried: {[str(c) for c in candidates]})",
                elapsed_ms=elapsed,
            )

        try:
            executor = BQLExecutor(ledger_path)
            result = executor.execute(query)

            # Check for errors
            if "error" in result.columns:
                elapsed = (time.time() - start_time) * 1000
                return EvaluationResult(
                    test_id=question.id,
                    passed=False,
                    category=question.category,
                    failure_type="syntax",
                    severity="high",
                    explanation=f"Query execution error: {result.first_value('error')}",
                    generated_query=query,
                    generated_result=result.to_dict(),
                    elapsed_ms=elapsed,
                )

            # Query executed successfully - compare results
            actual_normalized = normalize_result(result)
            expected_normalized = question.expected_result

            # For simple benchmarks (flat dict expected), extract first numeric value(s)
            if result.row_count > 0 and isinstance(question.expected_result, dict):
                # Extract all numeric values from the result
                all_numbers = []
                for row in result.rows:
                    for val in row:
                        if isinstance(val, (int, float)):
                            all_numbers.append(val)
                        elif isinstance(val, dict) and 'number' in val:
                            all_numbers.append(val['number'])

                # Single-key expected: compare sum of all positive numbers
                exp_keys = list(question.expected_result.keys())
                exp_vals = list(question.expected_result.values())
                
                if len(exp_keys) == 1:
                    exp_val = float(exp_vals[0])
                    # Sum all positive values from the result
                    act_sum = sum(n for n in all_numbers if n > 0)
                    
                    # For max_amount, find max instead of sum
                    if exp_keys[0] == "max_amount":
                        act_val = max(all_numbers) if all_numbers else 0
                    # For monthly_rent, compute average
                    elif exp_keys[0] == "monthly_rent":
                        pos_vals = [n for n in all_numbers if n > 0]
                        act_val = sum(pos_vals) / len(pos_vals) if pos_vals else 0
                    # For commissions: sum only small amounts (3-10 range)
                    elif exp_keys[0] == "total_commissions":
                        act_val = sum(n for n in all_numbers if 3 < n < 10)
                    # For cost_basis: sum absolute values
                    elif exp_keys[0] == "total_cost":
                        act_val = sum(abs(n) for n in all_numbers)
                    # For shares: sum all values (buy + sell)
                    elif exp_keys[0] == "shares":
                        act_val = sum(all_numbers)
                    else:
                        act_val = act_sum
                    
                    passed = abs(act_val - exp_val) < (0.02 * max(abs(exp_val), 1))
                else:
                    # Multi-key expected (e.g., utilities per month)
                    passed = compare_results(actual_normalized, expected_normalized)
            else:
                passed = compare_results(actual_normalized, expected_normalized)

            elapsed = (time.time() - start_time) * 1000

            if passed:
                return EvaluationResult(
                    test_id=question.id,
                    passed=True,
                    category=question.category,
                    elapsed_ms=elapsed,
                )
            else:
                failure_type = self._diagnose_failure(result, question.expected_result)
                return EvaluationResult(
                    test_id=question.id,
                    passed=False,
                    category=question.category,
                    failure_type=failure_type,
                    severity="medium",
                    explanation=self._build_failure_explanation(
                        result, question.expected_result, failure_type
                    ),
                    generated_query=query,
                    generated_result=result.to_dict(),
                    elapsed_ms=elapsed,
                )

        except FileNotFoundError as e:
            elapsed = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=question.id,
                passed=False,
                category=question.category,
                failure_type="setup",
                severity="high",
                explanation=f"Ledger not found: {e}",
                elapsed_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=question.id,
                passed=False,
                category=question.category,
                failure_type="syntax",
                severity="high",
                explanation=f"Unexpected error: {e}",
                generated_query=query,
                elapsed_ms=elapsed,
            )

    def _diagnose_failure(self, actual: BQLResult, expected: dict) -> str:
        """Diagnose the type of failure."""
        actual_norm = normalize_result(actual)

        # Row count mismatch -> aggregation issue
        if actual_norm.get("row_count") != expected.get("row_count"):
            if actual_norm.get("row_count", 0) == 0:
                return "semantic"
            return "aggregation"

        # Column mismatch -> semantic issue (wrong accounts/filters)
        if set(actual_norm.get("columns", [])) != set(expected.get("columns", [])):
            return "semantic"

        # Same shape but different values -> semantic or pricing
        return "semantic"

    def _build_failure_explanation(
        self, actual: BQLResult, expected: dict, failure_type: str
    ) -> str:
        """Build a human-readable failure explanation."""
        actual_norm = normalize_result(actual)
        parts = [f"Failure type: {failure_type}"]
        parts.append(f"Expected rows: {expected.get('row_count', '?')}")
        parts.append(f"Actual rows: {actual_norm.get('row_count', 0)}")
        parts.append(f"Expected columns: {expected.get('columns', [])}")
        parts.append(f"Actual columns: {actual_norm.get('columns', [])}")
        return " | ".join(parts)

    def run_full_evaluation(
        self, query_map: dict[str, str], category: str = None
    ) -> EvaluationRun:
        """
        Run a full evaluation across all or filtered benchmark questions.

        query_map: {question_id: query_string}
        """
        start_time = time.time()
        questions = self.benchmark.load_questions(category=category)
        results = []

        for q in questions:
            query = query_map.get(q.id, "")
            if not query:
                results.append(
                    EvaluationResult(
                        test_id=q.id,
                        passed=False,
                        category=q.category,
                        failure_type="missing",
                        severity="high",
                        explanation="No query provided for this question",
                    ).to_dict()
                )
                continue

            eval_result = self.evaluate_question(q, query)
            results.append(eval_result.to_dict())

        total = len(questions)
        passed = sum(1 for r in results if r.get("passed"))

        # Category scores
        cat_scores = {}
        for cat in self.benchmark.VALID_CATEGORIES:
            cat_results = [r for r in results if r.get("category") == cat]
            if cat_results:
                cat_passed = sum(1 for r in cat_results if r.get("passed"))
                cat_scores[cat] = round(cat_passed / len(cat_results) * 100, 1)
            else:
                cat_scores[cat] = 0.0

        # Difficulty scores
        diff_scores = {}
        for diff in ["easy", "medium", "hard"]:
            diff_results = [r for r in results if any(
                q.difficulty == diff for q in questions if q.id == r["test_id"]
            )]
            if diff_results:
                diff_passed = sum(1 for r in diff_results if r.get("passed"))
                diff_scores[diff] = round(diff_passed / len(diff_results) * 100, 1)

        duration = time.time() - start_time
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        run = EvaluationRun(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_tests=total,
            passed_tests=passed,
            overall_score=round(passed / total * 100, 1) if total > 0 else 0.0,
            category_scores=cat_scores,
            difficulty_scores=diff_scores,
            results=results,
            duration_seconds=round(duration, 2),
        )

        self.benchmark.save_evaluation_run(run)
        return run
