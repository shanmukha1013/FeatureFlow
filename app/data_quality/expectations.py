from typing import List, Dict, Any
from app.data_quality.models import DataContractModel


def generate_base_expectations(contract: DataContractModel) -> List[Dict[str, Any]]:
    """
    Translates a FeatureFlow Data Contract into Great Expectations (GX) Expectation Configs.
    Returns a list of dicts that can be passed to ExpectationSuite config.
    """
    expectations = []

    schema_def = contract.schema_definition
    primary_keys = contract.primary_keys or []

    # 1. Expect Table Columns to Match Set (Schema bounds)
    expected_columns = list(schema_def.keys())
    expectations.append({
        "expectation_type": "expect_table_columns_to_match_set",
        "kwargs": {"column_set": expected_columns, "exact_match": contract.business_rules.get("reject_extra_columns", False)},
        "meta": {"severity": "CRITICAL", "notes": "Schema Contract Boundary"}
    })

    # 2. Expect Primary Keys to be Unique and Not Null
    for pk in primary_keys:
        if pk in expected_columns:
            expectations.append({
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": pk},
                "meta": {"severity": "CRITICAL", "notes": "Primary Key Integrity"}
            })
            expectations.append({
                "expectation_type": "expect_column_values_to_be_unique",
                "kwargs": {"column": pk},
                "meta": {"severity": "CRITICAL", "notes": "Primary Key Integrity"}
            })

    # 3. Expect Data Types and Null limits
    max_null_pct = contract.business_rules.get("max_null_percentage_default", 0.05)

    for col, dtype in schema_def.items():
        # Type enforcement
        if "int" in dtype or "float" in dtype:
            gx_type_list = ["int", "int32", "int64", "float", "float32", "float64"]
            expectations.append({
                "expectation_type": "expect_column_values_to_be_in_type_list",
                "kwargs": {"column": col, "type_list": gx_type_list},
                "meta": {"severity": "ERROR", "notes": "Numeric Type Contract"}
            })
        elif "object" in dtype or "string" in dtype:
            expectations.append({
                "expectation_type": "expect_column_values_to_be_in_type_list",
                "kwargs": {"column": col, "type_list": ["object", "str", "string"]},
                "meta": {"severity": "ERROR", "notes": "String Type Contract"}
            })

        # Null limit (CRITICAL if 100% missing, WARNING if > threshold)
        if col not in primary_keys:
            expectations.append({
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": col, "mostly": 1.0 - max_null_pct},
                "meta": {"severity": "WARNING", "notes": "Null Threshold Boundary"}
            })

    return expectations
