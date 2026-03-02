"""
Data Preprocessing Service
Cleans CSV data: removes duplicates, handles nulls, corrects data types.
"""
import pandas as pd
import numpy as np
from io import StringIO


def clean_dataframe(df: pd.DataFrame, filename: str) -> tuple[pd.DataFrame, dict]:
    """
    Clean a DataFrame by:
    1. Removing duplicate rows
    2. Handling missing values
    3. Correcting data types (dates, numerics, categories)

    Returns (cleaned_df, report_dict)
    """
    report = {
        "filename": filename,
        "original_rows": len(df),
        "original_cols": len(df.columns),
        "columns": list(df.columns),
        "changes": []
    }

    # --- 1. Remove duplicates ---
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        df = df.drop_duplicates().reset_index(drop=True)
        report["changes"].append(f"Removed {dup_count} duplicate rows")

    # --- 2. Handle missing values ---
    null_counts = df.isnull().sum()
    for col in df.columns:
        null_n = int(null_counts[col])
        if null_n == 0:
            continue

        # If more than 60% null, drop the column
        if null_n / len(df) > 0.6:
            df = df.drop(columns=[col])
            report["changes"].append(f"Dropped column '{col}' ({null_n} nulls, >{60}% missing)")
            continue

        # Numeric columns: fill with median
        if pd.api.types.is_numeric_dtype(df[col]):
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            report["changes"].append(f"Filled {null_n} nulls in '{col}' with median ({median_val:.2f})")
        else:
            # Categorical/string: fill with mode
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])
                report["changes"].append(f"Filled {null_n} nulls in '{col}' with mode ('{mode_val[0]}')")
            else:
                df[col] = df[col].fillna("Unknown")
                report["changes"].append(f"Filled {null_n} nulls in '{col}' with 'Unknown'")

    # --- 3. Correct data types ---
    for col in df.columns:
        # Try to parse as datetime
        if pd.api.types.is_string_dtype(df[col]):
            sample = df[col].dropna().head(20)
            date_parseable = 0
            for val in sample:
                try:
                    pd.to_datetime(str(val))
                    date_parseable += 1
                except (ValueError, TypeError):
                    pass
            if len(sample) > 0 and date_parseable / len(sample) > 0.8:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    report["changes"].append(f"Converted '{col}' to datetime")
                except Exception:
                    pass

        # Try to convert object to numeric
        if pd.api.types.is_string_dtype(df[col]):
            try:
                converted = pd.to_numeric(df[col], errors='coerce')
                non_null_ratio = converted.notna().sum() / len(converted) if len(converted) > 0 else 0
                if non_null_ratio > 0.8:
                    df[col] = converted
                    report["changes"].append(f"Converted '{col}' to numeric")
            except Exception:
                pass

        # Low-cardinality strings -> category
        if pd.api.types.is_string_dtype(df[col]) and not hasattr(df[col], 'cat'):
            nunique = df[col].nunique()
            if nunique < 20 and len(df) > 50:
                df[col] = df[col].astype('category')
                report["changes"].append(f"Converted '{col}' to category ({nunique} unique values)")

    if not report["changes"]:
        report["changes"].append("No cleaning needed — data is already clean!")

    report["cleaned_rows"] = len(df)
    report["cleaned_cols"] = len(df.columns)

    # Build column info
    col_info = []
    for col in df.columns:
        col_info.append({
            "name": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "unique": int(df[col].nunique()),
        })
    report["column_info"] = col_info

    return df, report


def dataframe_to_summary(df: pd.DataFrame, name: str) -> dict:
    """Create a compact summary of a DataFrame for AI analysis."""
    summary = {
        "table_name": name,
        "rows": len(df),
        "columns": len(df.columns),
        "column_details": []
    }
    for col in df.columns:
        detail = {
            "name": col,
            "dtype": str(df[col].dtype),
            "unique_count": int(df[col].nunique()),
        }
        if pd.api.types.is_numeric_dtype(df[col]):
            detail["min"] = float(df[col].min()) if not df[col].empty else None
            detail["max"] = float(df[col].max()) if not df[col].empty else None
            detail["mean"] = float(df[col].mean()) if not df[col].empty else None
        elif hasattr(df[col], 'cat') or df[col].dtype == object:
            top_values = df[col].value_counts().head(5).to_dict()
            detail["top_values"] = {str(k): int(v) for k, v in top_values.items()}
        summary["column_details"].append(detail)
    return summary
