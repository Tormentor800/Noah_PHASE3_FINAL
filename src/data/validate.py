def run_ge_checks(df):
    # Minimal sanity checks (placeholder for Great Expectations)
    if df is None or len(df) == 0:
        raise ValueError("Empty dataset")
    if "ts" not in df.columns:
        raise ValueError("Missing ts column")
    return True
