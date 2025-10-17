import os, json
import pandas as pd

from src.settlement.settle import ART, PER_BET, CLOSES, OUT_CSV, SUMMARY
from src.flows.settle_demo import main as settle_demo_main

def test_settlement_outputs(tmp_path, monkeypatch):
    # run demo to produce closes and settlement artifacts
    settle_demo_main()

    assert os.path.exists(OUT_CSV)
    assert os.path.exists(SUMMARY)

    rep = pd.read_csv(OUT_CSV)
    summ = pd.read_csv(SUMMARY)

    # schema guards
    for col in ["league","market","selection","stake","sharp_entry_prob","sharp_close_prob","clv_pp"]:
        assert col in rep.columns

    assert "avg_clv_pp" in summ.columns
    # sanity: CLV distribution should be finite
    assert pd.api.types.is_numeric_dtype(rep["clv_pp"])
