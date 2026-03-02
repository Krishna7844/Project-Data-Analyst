"""
Relationship Detection Service
Automatically detects relationships between DataFrames (1:1, 1:N, N:1, M:N).
"""
import pandas as pd


def detect_relationships(dataframes: dict[str, pd.DataFrame]) -> list[dict]:
    """
    Given a dict of {table_name: DataFrame}, detect relationships based on
    matching column names and cardinality analysis.
    
    Returns a list of relationship dicts:
    {
        "table_a": str,
        "table_b": str,
        "key_column": str,
        "relationship": str,  # "One-to-One", "One-to-Many", "Many-to-One", "Many-to-Many"
        "matching_records": int,
        "table_a_unique": int,
        "table_b_unique": int
    }
    """
    relationships = []
    table_names = list(dataframes.keys())

    for i in range(len(table_names)):
        for j in range(i + 1, len(table_names)):
            name_a = table_names[i]
            name_b = table_names[j]
            df_a = dataframes[name_a]
            df_b = dataframes[name_b]

            # Find common column names
            common_cols = set(df_a.columns) & set(df_b.columns)

            for col in common_cols:
                # Get non-null values in both
                vals_a = df_a[col].dropna()
                vals_b = df_b[col].dropna()

                # Check if there's actual overlap
                overlap = set(vals_a.astype(str)) & set(vals_b.astype(str))
                if len(overlap) < 2:
                    continue  # No meaningful relationship

                # Cardinality analysis
                unique_a = vals_a.nunique()
                unique_b = vals_b.nunique()
                total_a = len(vals_a)
                total_b = len(vals_b)

                # Is the column a key (unique) in table A?
                is_key_a = unique_a == total_a  # All values unique
                # Is the column a key (unique) in table B?
                is_key_b = unique_b == total_b

                if is_key_a and is_key_b:
                    rel_type = "One-to-One"
                elif is_key_a and not is_key_b:
                    rel_type = "One-to-Many"
                elif not is_key_a and is_key_b:
                    rel_type = "Many-to-One"
                else:
                    rel_type = "Many-to-Many"

                relationships.append({
                    "table_a": name_a,
                    "table_b": name_b,
                    "key_column": col,
                    "relationship": rel_type,
                    "matching_records": len(overlap),
                    "table_a_unique": int(unique_a),
                    "table_b_unique": int(unique_b),
                    "table_a_total": int(total_a),
                    "table_b_total": int(total_b),
                })

    return relationships
