# tests/test_data_loader.py
import pandas as pd
from src.data.extract import load_data

def test_loader_returns_df():
    df = load_data(window_days=7)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "ts" in df.columns
