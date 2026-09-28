from datetime import datetime
import io
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

from app.services.profiler import DataProfilerService, to_json_serializable


# =========================================================================
# Unit Tests: to_json_serializable
# =========================================================================

def test_to_json_serializable_types():
    """Verify numpy and pandas types are converted to clean JSON types."""
    assert to_json_serializable(np.int64(42)) == 42
    assert to_json_serializable(np.float64(3.14)) == 3.14
    assert to_json_serializable(np.nan) is None
    assert to_json_serializable(float("nan")) is None
    assert to_json_serializable(float("inf")) is None
    assert to_json_serializable(np.bool_(True)) is True
    ts = pd.Timestamp("2026-01-15 10:30:00")
    assert to_json_serializable(ts) == ts.isoformat()
    assert to_json_serializable("hello") == "hello"
    assert to_json_serializable(None) is None


# =========================================================================
# Unit Tests: infer_column_data_type
# =========================================================================

def test_infer_column_data_type_integers():
    """Verify integer types detected accurately."""
    s1 = pd.Series([1, 2, 3, 4, 5])
    assert DataProfilerService.infer_column_data_type(s1) == "integer"

    s2 = pd.Series(["10", "20", "30", "40"])
    assert DataProfilerService.infer_column_data_type(s2) == "integer"


def test_infer_column_data_type_floats():
    """Verify float types detected accurately."""
    s1 = pd.Series([1.5, 2.7, 3.14, 4.0])
    assert DataProfilerService.infer_column_data_type(s1) == "float"

    s2 = pd.Series(["1.5", "2.7", "3.14"])
    assert DataProfilerService.infer_column_data_type(s2) == "float"


def test_infer_column_data_type_booleans():
    """Verify boolean types detected accurately."""
    s1 = pd.Series([True, False, True])
    assert DataProfilerService.infer_column_data_type(s1) == "boolean"

    s2 = pd.Series(["true", "false", "true", "false"])
    assert DataProfilerService.infer_column_data_type(s2) == "boolean"

    s3 = pd.Series(["yes", "no", "yes"])
    assert DataProfilerService.infer_column_data_type(s3) == "boolean"


def test_infer_column_data_type_datetime():
    """Verify datetime types detected accurately."""
    s1 = pd.Series(pd.date_range("2026-01-01", periods=5))
    assert DataProfilerService.infer_column_data_type(s1) == "datetime"

    s2 = pd.Series(["2026-01-01", "2026-01-02", "2026-01-03"])
    assert DataProfilerService.infer_column_data_type(s2) == "datetime"


def test_infer_column_data_type_categorical_and_strings():
    """Verify categorical and general string detection."""
    # Low cardinality repeated non-numeric
    s_cat = pd.Series(["North", "South", "North", "South", "North", "South"] * 10)
    assert DataProfilerService.infer_column_data_type(s_cat) == "categorical"

    # High cardinality unique strings
    s_str = pd.Series([f"Unique_Text_Entry_{i}" for i in range(50)])
    assert DataProfilerService.infer_column_data_type(s_str) == "string"


def test_infer_column_data_type_empty():
    """Verify empty column returns 'empty'."""
    s = pd.Series([None, np.nan, None])
    assert DataProfilerService.infer_column_data_type(s) == "empty"


# =========================================================================
# Unit Tests: detect_invalid_values_in_series
# =========================================================================

def test_detect_invalid_values():
    """Verify placeholder and infinity invalid value detection."""
    s = pd.Series(["valid", "N/A", "null", "-", "ok", "None"])
    invalid_count = DataProfilerService.detect_invalid_values_in_series(s, "string")
    assert invalid_count == 4

    s_num = pd.Series([10.5, float("inf"), 20.0, float("-inf")])
    invalid_count_num = DataProfilerService.detect_invalid_values_in_series(s_num, "float")
    assert invalid_count_num == 2


# =========================================================================
# Unit Tests: profile_column
# =========================================================================

def test_profile_column_numeric():
    """Verify column metrics calculation for numeric series."""
    s = pd.Series([10, 20, 30, 40, np.nan])
    col_prof, inv_cnt = DataProfilerService.profile_column("sales", s, total_rows=5)

    assert col_prof.column_name == "sales"
    assert col_prof.detected_data_type in ("integer", "float")
    assert col_prof.null_count == 1
    assert col_prof.null_percentage == 20.0
    assert col_prof.unique_count == 4
    assert col_prof.minimum == 10
    assert col_prof.maximum == 40
    assert col_prof.mean == 25.0
    assert col_prof.median == 25.0
    assert len(col_prof.sample_values) == 4


# =========================================================================
# Unit Tests: calculate_quality_score
# =========================================================================

def test_calculate_quality_score_clean_data():
    """Clean data with 0 missing, 0 duplicates, 0 invalid should score near 100."""
    score, comp, uniq, val = DataProfilerService.calculate_quality_score(
        row_count=100,
        column_count=5,
        total_missing=0,
        duplicate_rows=0,
        invalid_values=0,
        completely_empty_cols=[],
    )
    assert score == 100.0
    assert comp == 100.0
    assert uniq == 100.0
    assert val == 100.0


def test_calculate_quality_score_imperfect_data():
    """Verify quality score reduces predictably with data defects."""
    score, comp, uniq, val = DataProfilerService.calculate_quality_score(
        row_count=100,
        column_count=5,
        total_missing=50,   # 10% missing cells
        duplicate_rows=10,  # 10% duplicate rows
        invalid_values=5,
        completely_empty_cols=["col5"],
    )
    assert 0.0 <= score <= 100.0
    assert comp == 90.0
    assert uniq == 90.0
    assert score < 100.0


def test_calculate_quality_score_empty_data():
    """Verify 0-row dataset returns 0.0 score."""
    score, comp, uniq, val = DataProfilerService.calculate_quality_score(
        row_count=0,
        column_count=0,
        total_missing=0,
        duplicate_rows=0,
        invalid_values=0,
        completely_empty_cols=[],
    )
    assert score == 0.0


# =========================================================================
# Unit Tests: profile_dataframe
# =========================================================================

def test_profile_dataframe_comprehensive():
    """Verify full dataframe profiling with anomalies, empty columns, and duplicates."""
    df = pd.DataFrame({
        "id": [1, 2, 3, 3],
        "name": ["Alice", "Bob", "Charlie", "Charlie"],
        "score": [95.5, np.nan, 80.0, 80.0],
        "empty_col": [np.nan, np.nan, np.nan, np.nan],
        "high_null": ["X", np.nan, np.nan, np.nan],
    })

    result = DataProfilerService.profile_dataframe(df)

    assert result.row_count == 4
    assert result.column_count == 5
    assert result.duplicate_rows == 1  # row 3 is duplicate of row 2
    assert result.total_missing_values == 8  # 1 in score + 4 in empty_col + 3 in high_null
    assert "empty_col" in result.completely_empty_columns
    assert "high_null" in result.high_null_columns
    assert 0.0 <= result.overall_data_quality_score <= 100.0
    assert len(result.columns) == 5

    # Check serialization
    res_dict = result.to_dict()
    assert "summary" in res_dict
    assert "columns" in res_dict
    assert "warnings" in res_dict
    assert "quality_metrics" in res_dict


# =========================================================================
# Unit Tests: load_dataframe and error handling
# =========================================================================

def test_load_dataframe_csv(tmp_path):
    """Verify loading valid CSV."""
    csv_path = tmp_path / "valid.csv"
    csv_path.write_text("a,b\n1,2\n3,4", encoding="utf-8")

    df = DataProfilerService.load_dataframe(csv_path, "csv")
    assert len(df) == 2
    assert list(df.columns) == ["a", "b"]


def test_load_dataframe_nonexistent():
    """Verify error on nonexistent file."""
    with pytest.raises(HTTPException) as exc:
        DataProfilerService.load_dataframe("non_existent_file.csv", "csv")
    assert exc.value.status_code == 400


def test_load_dataframe_empty_file(tmp_path):
    """Verify error on 0-byte file."""
    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("", encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        DataProfilerService.load_dataframe(empty_path, "csv")
    assert exc.value.status_code == 400
