"""
BQL Executor — runs BQL queries against Beancount ledgers via the beanquery library.

Handles the beanquery 0.2.x type system: Amount, Position, frozenset, etc.
"""

import subprocess
import json
import csv
import io
import sys
from pathlib import Path
from typing import Any, Optional

HAS_BEANQUERY = False
try:
    import beanquery
    from beancount.core.amount import Amount
    from beancount.core.position import Position
    HAS_BEANQUERY = True
except ImportError:
    Amount = None
    Position = None


def _serialize_value(v: Any) -> Any:
    """Convert beanquery-specific types to JSON-serializable Python primitives."""
    if v is None:
        return None
    if isinstance(v, (int, float, str)):
        return v
    if isinstance(v, bool):
        return v
    if HAS_BEANQUERY:
        if isinstance(v, Amount):
            # Return a dict preserving both number and currency
            return {"number": float(v.number), "currency": str(v.currency)}
        if isinstance(v, Position):
            amt = v.units
            return {"number": float(amt.number), "currency": str(amt.currency)}
    if isinstance(v, (frozenset, set)):
        return sorted(str(x) for x in v)
    if hasattr(v, 'isoformat'):  # date/datetime
        return v.isoformat()
    return str(v)


def _serialize_row(row: tuple) -> list:
    """Serialize an entire row tuple to primitives."""
    return [_serialize_value(v) for v in row]


class BQLResult:
    """Represents the result of a BQL query execution."""

    def __init__(self, columns: list[str], rows: list[list[Any]], query: str):
        self.columns = columns
        self.rows = rows
        self.query = query
        self._row_dicts = None

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def row_dicts(self) -> list[dict[str, Any]]:
        if self._row_dicts is None:
            self._row_dicts = [
                dict(zip(self.columns, row)) for row in self.rows
            ]
        return self._row_dicts

    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "query": self.query,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def get_column(self, name: str) -> list[Any]:
        if name not in self.columns:
            raise KeyError(f"Column '{name}' not found. Available: {self.columns}")
        idx = self.columns.index(name)
        return [row[idx] for row in self.rows]

    def first_value(self, column: str) -> Any:
        if self.row_count == 0:
            return None
        return self.get_column(column)[0]

    def __repr__(self) -> str:
        return f"BQLResult(columns={self.columns}, rows={self.row_count})"


class BQLExecutor:
    """Execute BQL (BeanQuery) queries against Beancount ledger files."""

    def __init__(self, ledger_path: str | Path):
        self.ledger_path = Path(ledger_path).resolve()
        if not self.ledger_path.exists():
            raise FileNotFoundError(f"Ledger file not found: {self.ledger_path}")

    def execute(self, query: str) -> BQLResult:
        """Execute a BQL query using beanquery if available, otherwise bean-query CLI."""
        if HAS_BEANQUERY:
            return self._execute_via_beanquery(query)
        else:
            return self._execute_via_cli(query)

    def _execute_via_beanquery(self, query: str) -> BQLResult:
        """Execute using the beanquery Python library with proper type conversion."""
        try:
            conn = beanquery.connect(f"beancount:{self.ledger_path}")
            cursor = conn.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchall()
            rows = [_serialize_row(row) for row in raw_rows]
            return BQLResult(columns=columns, rows=rows, query=query)
        except Exception as e:
            return BQLResult(
                columns=["error"],
                rows=[[str(e)]],
                query=query,
            )

    def _execute_via_cli(self, query: str) -> BQLResult:
        """Execute using the bean-query CLI tool as a fallback."""
        try:
            result = subprocess.run(
                ["bean-query", "-f", "csv", str(self.ledger_path), query],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return BQLResult(
                    columns=["error"],
                    rows=[[result.stderr.strip()]],
                    query=query,
                )

            reader = csv.reader(io.StringIO(result.stdout))
            rows_list = list(reader)
            if not rows_list:
                return BQLResult(columns=[], rows=[], query=query)

            columns = rows_list[0]
            rows = rows_list[1:]
            return BQLResult(columns=columns, rows=rows, query=query)
        except FileNotFoundError:
            return BQLResult(
                columns=["error"],
                rows=[["BQL executor not available. Install beanquery: pip install beanquery"]],
                query=query,
            )
        except Exception as e:
            return BQLResult(
                columns=["error"],
                rows=[[f"Query execution failed: {e}"]],
                query=query,
            )

    def execute_file(self, query_file: str | Path) -> BQLResult:
        """Execute a query from a file."""
        query = Path(query_file).read_text().strip()
        return self.execute(query)


def normalize_result(result: BQLResult) -> dict:
    """
    Normalize a BQLResult into a hashable, comparable dict for evaluation.
    Sorts rows and converts to standard types.
    """
    if result.row_count == 0:
        return {"empty": True, "columns": result.columns}

    rows = result.row_dicts[:]
    rows.sort(key=lambda r: json.dumps(r, default=str))

    normalized = []
    for row in rows:
        norm_row = {}
        for k, v in row.items():
            if isinstance(v, (int, float)):
                norm_row[k] = round(float(v), 6)
            elif v is not None:
                norm_row[k] = str(v)
            else:
                norm_row[k] = None
        normalized.append(norm_row)

    return {
        "empty": False,
        "columns": sorted(result.columns),
        "row_count": result.row_count,
        "rows": normalized,
    }


def compare_results(actual: dict, expected: dict, tolerance: float = 1e-4) -> bool:
    """
    Compare normalized results with tolerance for numeric values.
    """
    if actual.get("empty") != expected.get("empty"):
        return False

    if actual.get("empty") and expected.get("empty"):
        return True

    if actual.get("row_count") != expected.get("row_count"):
        return False

    actual_rows = actual.get("rows", [])
    expected_rows = expected.get("rows", [])

    actual_sig = _compute_signature(actual_rows)
    expected_sig = _compute_signature(expected_rows)

    return actual_sig == expected_sig


def _compute_signature(rows: list[dict]) -> frozenset:
    """Compute a frozenset signature for a list of row dicts."""
    sig_items = []
    for row in rows:
        items = tuple(sorted((k, _normalize_val(v)) for k, v in row.items()))
        sig_items.append(items)
    return frozenset(sig_items)


def _normalize_val(v: Any) -> Any:
    if isinstance(v, float):
        return round(v, 4)
    return v
