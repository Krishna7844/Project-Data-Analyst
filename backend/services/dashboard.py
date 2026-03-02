"""
Dashboard Data Aggregation Service
Computes KPIs, chart data, and summary statistics from uploaded datasets.
"""
import pandas as pd
import numpy as np


def compute_dashboard(dataframes: dict[str, pd.DataFrame], filters: dict = None) -> dict:
    """
    Given a dict of {table_name: DataFrame}, produce dashboard-ready JSON:
    - KPI cards (total records, sources, numeric highlights)
    - Chart data for bar, pie, line, doughnut charts
    
    If 'filters' is provided (dict of {col: value}), filter dataframes before aggregation.
    """
    result = {
        "kpis": [],
        "charts": [],
        "tables_preview": []
    }

    # --- Apply Filters ---
    # Create a copy of the dict so we don't mutate the original session data
    working_dfs = {name: df.copy() for name, df in dataframes.items()}
    
    if filters:
        for col, val in filters.items():
            for name, df in working_dfs.items():
                if col in df.columns:
                    # Filter matching rows
                    # Handle filtering based on data type if necessary, 
                    # but simple equality check works for categorical/string which is most click events
                    # Convert to string for comparison to handle type mismatches gracefully
                    mask = df[col].astype(str) == str(val)
                    working_dfs[name] = df[mask]

    # --- Global KPIs ---
    total_rows = sum(len(df) for df in working_dfs.values())
    total_cols = sum(len(df.columns) for df in working_dfs.values())

    result["kpis"].append({"label": "Total Records", "value": total_rows, "icon": "fa-database"})
    result["kpis"].append({"label": "Data Sources", "value": len(working_dfs), "icon": "fa-layer-group"})
    result["kpis"].append({"label": "Total Columns", "value": total_cols, "icon": "fa-table-columns"})

    # --- Per-table analysis ---
    for name, df in working_dfs.items():
        # Table preview (first 5 rows)
        preview_data = df.head(5).copy()
        # Convert datetime columns to string for JSON serialization
        for col in preview_data.columns:
            if pd.api.types.is_datetime64_any_dtype(preview_data[col]):
                preview_data[col] = preview_data[col].astype(str)
        
        result["tables_preview"].append({
            "name": name,
            "columns": list(df.columns),
            "rows": preview_data.values.tolist(),
            "total_rows": len(df),
        })

        # --- Generate charts from categorical columns ---
        cat_cols = [c for c in df.columns
                    if df[c].dtype.name == 'category'
                    or (str(df[c].dtype) in ('object', 'string', 'str') and df[c].nunique() <= 15)
                    or (pd.api.types.is_string_dtype(df[c]) and df[c].nunique() <= 15)]

        for col in cat_cols[:3]:  # Limit to 3 categorical charts per table
            value_counts = df[col].value_counts().head(10)
            result["charts"].append({
                "title": f"{col} Distribution ({name})",
                "type": _pick_chart_type(col),
                "labels": [str(x) for x in value_counts.index.tolist()],
                "data": value_counts.values.tolist(),
                "table": name,
            })

        # --- Generate charts from numeric columns ---
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # If there's a date column and a numeric column, make a line chart
        date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        if date_cols and num_cols:
            date_col = date_cols[0]
            num_col = num_cols[0]
            # Group by month
            temp = df[[date_col, num_col]].dropna().copy()
            temp['month'] = temp[date_col].dt.to_period('M').astype(str)
            monthly = temp.groupby('month')[num_col].sum().tail(12)
            result["charts"].append({
                "title": f"{num_col} Over Time ({name})",
                "type": "line",
                "labels": monthly.index.tolist(),
                "data": [round(float(v), 2) for v in monthly.values],
                "table": name,
            })

        # Numeric summary bar chart (top numeric cols)
        if len(num_cols) >= 2:
            means = {col: round(float(df[col].mean()), 2) for col in num_cols[:6]}
            result["charts"].append({
                "title": f"Average Values ({name})",
                "type": "bar",
                "labels": list(means.keys()),
                "data": list(means.values()),
                "table": name,
            })

    # Add a numeric KPI from the first table with numeric data
    for name, df in working_dfs.items():
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if num_cols:
            col = num_cols[0]
            result["kpis"].append({
                "label": f"Avg {col}",
                "value": round(float(df[col].mean()), 2),
                "icon": "fa-chart-simple"
            })
            break

    return result


def _pick_chart_type(col_name: str) -> str:
    """Pick a chart type based on column name heuristics."""
    name_lower = col_name.lower()
    if any(kw in name_lower for kw in ['region', 'type', 'tier', 'level', 'category']):
        return 'doughnut'
    if any(kw in name_lower for kw in ['gender', 'flag', 'channel', 'applied']):
        return 'pie'
    return 'bar'
