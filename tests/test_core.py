"""
Tests for the BQL Skill Research Project core modules.

Tests the BQL executor, benchmark system, and normalization/comparison logic.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add automation to path
automation_dir = Path(__file__).resolve().parent.parent / "automation"
sys.path.insert(0, str(automation_dir))

from core.bql_executor import (
    BQLResult,
    normalize_result,
    compare_results,
    _compute_signature,
    _normalize_val,
)


class TestBQLResult(unittest.TestCase):
    """Tests for BQLResult data class."""

    def test_empty_result(self):
        result = BQLResult(columns=[], rows=[], query="SELECT 1")
        self.assertEqual(result.row_count, 0)
        self.assertEqual(result.columns, [])
        self.assertEqual(result.rows, [])

    def test_basic_result(self):
        result = BQLResult(
            columns=["account", "total"],
            rows=[["Expenses:Food", 100.0], ["Expenses:Rent", 500.0]],
            query="SELECT account, SUM(COST(position)) FROM transactions",
        )
        self.assertEqual(result.row_count, 2)
        self.assertEqual(result.columns, ["account", "total"])

    def test_row_dicts(self):
        result = BQLResult(
            columns=["a", "b"],
            rows=[[1, 2], [3, 4]],
            query="test",
        )
        expected = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        self.assertEqual(result.row_dicts, expected)

    def test_get_column(self):
        result = BQLResult(
            columns=["name", "value"],
            rows=[["foo", 10], ["bar", 20]],
            query="test",
        )
        self.assertEqual(result.get_column("name"), ["foo", "bar"])
        self.assertEqual(result.get_column("value"), [10, 20])

        with self.assertRaises(KeyError):
            result.get_column("nonexistent")

    def test_first_value(self):
        result = BQLResult(
            columns=["total"],
            rows=[[42.5]],
            query="test",
        )
        self.assertEqual(result.first_value("total"), 42.5)

        empty = BQLResult(columns=["x"], rows=[], query="test")
        self.assertIsNone(empty.first_value("x"))

    def test_to_dict_and_json(self):
        result = BQLResult(columns=["x"], rows=[[1]], query="SELECT x")
        d = result.to_dict()
        self.assertEqual(d["columns"], ["x"])
        self.assertEqual(d["rows"], [[1]])
        self.assertEqual(d["row_count"], 1)

        j = result.to_json()
        self.assertIn('"columns"', j)
        self.assertIn('"rows"', j)

    def test_repr(self):
        result = BQLResult(columns=["a"], rows=[[1], [2]], query="test")
        r = repr(result)
        self.assertIn("BQLResult", r)
        self.assertIn("rows=2", r)


class TestNormalizeResult(unittest.TestCase):
    """Tests for result normalization."""

    def test_empty_result(self):
        result = BQLResult(columns=[], rows=[], query="test")
        norm = normalize_result(result)
        self.assertTrue(norm["empty"])
        self.assertEqual(norm["columns"], [])

    def test_normalize_sorts_rows(self):
        result = BQLResult(
            columns=["name", "val"],
            rows=[["b", 2], ["a", 1], ["c", 3]],
            query="test",
        )
        norm = normalize_result(result)
        self.assertFalse(norm["empty"])
        self.assertEqual(norm["row_count"], 3)

        # Rows should be sorted by their JSON representation
        names = [r["name"] for r in norm["rows"]]
        self.assertEqual(names, sorted(names))

    def test_normalize_handles_none(self):
        result = BQLResult(
            columns=["a", "b"],
            rows=[[None, 1], [2, None]],
            query="test",
        )
        norm = normalize_result(result)
        self.assertEqual(norm["row_count"], 2)

    def test_normalize_rounds_floats(self):
        result = BQLResult(
            columns=["value"],
            rows=[[3.14159265359]],
            query="test",
        )
        norm = normalize_result(result)
        self.assertEqual(norm["rows"][0]["value"], 3.141593)

    def test_normalize_columns_sorted(self):
        result = BQLResult(
            columns=["c", "a", "b"],
            rows=[[1, 2, 3]],
            query="test",
        )
        norm = normalize_result(result)
        self.assertEqual(norm["columns"], ["a", "b", "c"])


class TestCompareResults(unittest.TestCase):
    """Tests for result comparison."""

    def test_identical_results(self):
        result = BQLResult(
            columns=["x", "y"],
            rows=[[1, 2], [3, 4]],
            query="test",
        )
        norm = normalize_result(result)
        self.assertTrue(compare_results(norm, norm))

    def test_different_row_count(self):
        a = BQLResult(columns=["x"], rows=[[1], [2]], query="t1")
        b = BQLResult(columns=["x"], rows=[[1]], query="t2")
        self.assertFalse(compare_results(normalize_result(a), normalize_result(b)))

    def test_empty_vs_nonempty(self):
        a = BQLResult(columns=[], rows=[], query="t1")
        b = BQLResult(columns=["x"], rows=[[1]], query="t2")
        self.assertFalse(compare_results(normalize_result(a), normalize_result(b)))

    def test_both_empty(self):
        a = BQLResult(columns=[], rows=[], query="t1")
        b = BQLResult(columns=[], rows=[], query="t2")
        self.assertTrue(compare_results(normalize_result(a), normalize_result(b)))

    def test_same_values_different_order(self):
        a = BQLResult(columns=["n", "v"], rows=[["a", 1], ["b", 2]], query="t1")
        b = BQLResult(columns=["n", "v"], rows=[["b", 2], ["a", 1]], query="t2")
        self.assertTrue(compare_results(normalize_result(a), normalize_result(b)))

    def test_different_values(self):
        a = BQLResult(columns=["n", "v"], rows=[["a", 1], ["b", 2]], query="t1")
        b = BQLResult(columns=["n", "v"], rows=[["a", 1], ["b", 3]], query="t2")
        self.assertFalse(compare_results(normalize_result(a), normalize_result(b)))

    def test_float_tolerance(self):
        a = BQLResult(columns=["v"], rows=[[3.14159]], query="t1")
        b = BQLResult(columns=["v"], rows=[[3.14158]], query="t2")
        # Both round to 3.1416
        self.assertTrue(compare_results(normalize_result(a), normalize_result(b)))


class TestComputeSignature(unittest.TestCase):
    """Tests for signature computation."""

    def test_signature_frozenset(self):
        rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        sig = _compute_signature(rows)
        self.assertIsInstance(sig, frozenset)

    def test_signature_order_independent(self):
        rows1 = [{"a": 1}, {"b": 2}]
        rows2 = [{"b": 2}, {"a": 1}]
        self.assertEqual(_compute_signature(rows1), _compute_signature(rows2))

    def test_signature_normalizes_floats(self):
        rows1 = [{"v": 3.1415926}]
        rows2 = [{"v": 3.14159}]
        self.assertEqual(_compute_signature(rows1), _compute_signature(rows2))


class TestNormalizeVal(unittest.TestCase):
    """Tests for value normalization."""

    def test_float_rounding(self):
        self.assertEqual(_normalize_val(3.14159), 3.1416)
        self.assertEqual(_normalize_val(3.14159265359), 3.1416)

    def test_int_passes_through(self):
        self.assertEqual(_normalize_val(42), 42)

    def test_string_passes_through(self):
        self.assertEqual(_normalize_val("hello"), "hello")

    def test_none_passes_through(self):
        self.assertIsNone(_normalize_val(None))


class TestBenchmarkModule(unittest.TestCase):
    """Tests for the benchmark module."""

    def setUp(self):
        # Use a temporary directory for benchmark data
        self.tmpdir = tempfile.mkdtemp()
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "automation"))

    def test_benchmark_question_creation(self):
        from core.benchmark import BenchmarkQuestion
        
        q = BenchmarkQuestion(
            id="T001",
            ledger="test.bean",
            question="What is my net worth?",
            expected_result={"net_worth": 50000},
            category="networth",
            difficulty="easy",
        )
        self.assertEqual(q.id, "T001")
        self.assertEqual(q.category, "networth")

    def test_benchmark_question_from_dict(self):
        from core.benchmark import BenchmarkQuestion
        
        d = {
            "id": "T001",
            "ledger": "test.bean",
            "question": "Test question?",
            "expected_result": {"total": 100},
            "category": "spending",
            "difficulty": "medium",
            "tags": ["test"],
        }
        q = BenchmarkQuestion.from_dict(d)
        self.assertEqual(q.id, "T001")
        self.assertEqual(q.tags, ["test"])

    def test_evaluation_result(self):
        from core.benchmark import EvaluationResult
        
        r = EvaluationResult(
            test_id="T001",
            passed=True,
            category="spending",
        )
        self.assertTrue(r.passed)
        self.assertIsNone(r.failure_type)

        f = EvaluationResult(
            test_id="T002",
            passed=False,
            category="investments",
            failure_type="syntax",
            severity="high",
            explanation="Parse error",
        )
        self.assertFalse(f.passed)
        self.assertEqual(f.failure_type, "syntax")

    def test_evaluation_run(self):
        from core.benchmark import EvaluationRun
        
        run = EvaluationRun(
            run_id="test_run",
            timestamp="2024-01-01T00:00:00",
            total_tests=10,
            passed_tests=8,
            overall_score=80.0,
            category_scores={"spending": 90, "investments": 70},
            difficulty_scores={"easy": 100, "medium": 80, "hard": 60},
            results=[],
            duration_seconds=1.5,
        )
        self.assertEqual(run.overall_score, 80.0)
        self.assertEqual(run.category_scores["spending"], 90)


class TestBenchmarkCategories(unittest.TestCase):
    """Test that benchmark categories are valid."""

    def test_valid_categories(self):
        from core.benchmark import Benchmark
        
        valid = Benchmark.VALID_CATEGORIES
        self.assertIn("spending", valid)
        self.assertIn("investments", valid)
        self.assertIn("multicurrency", valid)
        self.assertIn("tax", valid)
        self.assertIn("metadata", valid)
        self.assertEqual(len(valid), 8)


class TestBQLExecutorCreation(unittest.TestCase):
    """Test BQLExecutor creation (without beanquery installed)."""

    def test_executor_requires_existing_file(self):
        from core.bql_executor import BQLExecutor
        
        with self.assertRaises(FileNotFoundError):
            BQLExecutor("/nonexistent/path.bean")


class TestIntegration(unittest.TestCase):
    """Integration tests across modules."""

    def test_full_workflow_without_beanquery(self):
        """Test that the full comparison workflow works."""
        # Simulate what Agent 3 does
        from core.bql_executor import BQLResult, normalize_result, compare_results

        # Simulated query result
        actual = BQLResult(
            columns=["account", "total"],
            rows=[
                ["Expenses:Food", 343.0],
                ["Expenses:Rent", 1500.0],
                ["Expenses:Transport", 45.0],
            ],
            query="SELECT account, SUM(COST(position)) as total FROM transactions WHERE account ~ 'Expenses:' GROUP BY account",
        )

        # Expected result from benchmark
        expected = {
            "empty": False,
            "columns": ["account", "total"],
            "row_count": 3,
            "rows": [
                {"account": "Expenses:Food", "total": 343.0},
                {"account": "Expenses:Rent", "total": 1500.0},
                {"account": "Expenses:Transport", "total": 45.0},
            ],
        }

        actual_norm = normalize_result(actual)
        self.assertTrue(compare_results(actual_norm, expected))

    def test_failure_workflow(self):
        """Test that failures are detected correctly."""
        from core.bql_executor import BQLResult, normalize_result, compare_results

        # Wrong result
        actual = BQLResult(
            columns=["account", "total"],
            rows=[["Expenses:Food", 500.0]],
            query="SELECT ...",
        )

        expected = {
            "empty": False,
            "columns": ["account", "total"],
            "row_count": 1,
            "rows": [{"account": "Expenses:Food", "total": 343.0}],
        }

        actual_norm = normalize_result(actual)
        self.assertFalse(compare_results(actual_norm, expected))


if __name__ == "__main__":
    unittest.main()
