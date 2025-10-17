from __future__ import annotations
import os, yaml
from datetime import timedelta
from pathlib import Path
import pandas as pd

from src.data.extract import load_data
from src.train.drift import drift_scan_batch

# tiny helper to read thresholds.yaml
def _load_thresholds():
    p = Path("config/thresholds.yaml")
    if not p.exists():
        return {"drift":{"psi_warn":0.10,"psi_fail":0.25,"ks_p_fail":0.01}}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _breaches(df: pd.DataFrame, psi_fail: float, ks_p_fail: float):
    hard = df[(df["psi"] >= psi_fail) | (df["ks_p"] <= ks_p_fail)]
    soft = df[(df["psi"] >= psi_fail*0.4) | (df["ks_p"] <= ks_p_fail*2)]
    return hard, soft

def drift_watch():
    cfg = _load_thresholds()
    psi_fail = float(cfg["drift"]["psi_fail"])
    ks_p_fail = float(cfg["drift"]["ks_p_fail"])

    df = load_data(window_days=30)
    if len(df) < 100 or "ts" not in df.columns:
        out = {"status":"insufficient_data"}
        print(out); return out

    cutoff = df["ts"].max() - timedelta(days=3)
    ref = df[df["ts"] <= cutoff]
    new = df[df["ts"] > cutoff]
    numeric_cols = [c for c in df.columns if df[c].dtype.kind in "fc"]
    report = drift_scan_batch(ref, new, numeric_cols)

    hard, soft = _breaches(report, psi_fail, ks_p_fail)
    out = {
        "report": report.to_dict(orient="records"),
        "hard_breaches": hard.to_dict(orient="records"),
        "soft_breaches": soft.to_dict(orient="records"),
    }
    print(out)

    # === On-demand retrain if any hard breach ===
    if len(hard) > 0:
        try:
            from src.flows.monthly_retrain import monthly_retrain
            re = monthly_retrain()  # promote if gates pass
            out["retrain"] = re
            print({"retrain_triggered": True, "result": re})
        except Exception as e:
            print({"retrain_triggered": False, "error": str(e)})

    # === (Optional) Slack alert hook ===
    webhook = os.getenv("SLACK_WEBHOOK", "")
    if webhook and (len(hard) > 0):
        # keep it simple: no dependency, just a curl-like note
        print({"alert":"post to slack", "webhook": "****redacted****", "hard": out["hard_breaches"]})

    return out

if __name__ == "__main__":
    drift_watch()
