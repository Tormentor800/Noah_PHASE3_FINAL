import json, os
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CFG  = ROOT / "config"
ART  = ROOT / "artifacts"
CFG.mkdir(exist_ok=True, parents=True)
ART.mkdir(exist_ok=True, parents=True)

RISK_YAML    = CFG / "risk.yaml"
BROKERS_YAML = CFG / "brokers.yaml"
THRESH_YAML  = CFG / "thresholds.yaml"
EXEC_LOG     = ART / "executions_index.jsonl"

def _yaml_load(path: Path) -> dict:
    import yaml
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return yaml.safe_load(f) or {}

def _yaml_dump(path: Path, data: dict):
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

def _ensure_defaults():
    risk = _yaml_load(RISK_YAML)
    risk.setdefault("kill_switch", False)
    risk.setdefault("exposure_caps", {"total_usd": 10000, "per_league": {"NBA": 2000, "EPL": 2000, "NHL": 2000}})
    risk.setdefault("duplicate_guard_sec", 10)
    risk.setdefault("correlation_guard", {"max_same_team_open": 3})
    _yaml_dump(RISK_YAML, risk)

    brokers = _yaml_load(BROKERS_YAML)
    for b in ("pinnacle", "sbo", "isn"):
        brokers.setdefault(b, {})
        brokers[b].setdefault("pause", False)
        brokers[b].setdefault("fee_bps", 6 if b != "pinnacle" else 8)
        brokers[b].setdefault("slippage_bps_default", 40)
        brokers[b].setdefault("api", {"base_url": "https://api.asianconnect.mock", "key": "REPLACE"})
    _yaml_dump(BROKERS_YAML, brokers)

    thr = _yaml_load(THRESH_YAML)
    thr.setdefault("drift", {})
    thr["drift"].setdefault("psi_soft", 0.15)
    thr["drift"].setdefault("psi_hard", 0.25)
    thr["drift"].setdefault("ks_p_soft", 0.01)
    thr["drift"].setdefault("ks_p_hard", 0.001)
    thr.setdefault("kpi", {})
    thr["kpi"].setdefault("clv_bps_min", -75.0)
    thr["kpi"].setdefault("ev_pct_min", -1.5)
    _yaml_dump(THRESH_YAML, thr)

_ensure_defaults()

st.set_page_config(page_title="M7 Admin", layout="wide")
st.title("M7 Admin UI — thresholds, books, audit")

tab1, tab2, tab3 = st.tabs(["Risk & Thresholds", "Books / Pause", "Audit Log"])

with tab1:
    st.subheader("Risk Controls")
    risk = _yaml_load(RISK_YAML)
    thr  = _yaml_load(THRESH_YAML)
    drift = thr.get("drift", {})
    kpi   = thr.get("kpi", {})

    with st.form("risk_form"):
        ks = st.toggle("Kill switch (pause all execution)", value=bool(risk.get("kill_switch", False)))
        tot_cap = st.number_input("Total exposure cap (USD)", min_value=0, value=int(risk.get("exposure_caps", {}).get("total_usd", 10000)))

        per_league = dict(risk.get("exposure_caps", {}).get("per_league", {}))
        st.markdown("**Per-league caps (USD)**")
        edits = {}
        for lg, val in per_league.items():
            edits[lg] = st.number_input(f"  {lg}", min_value=0, value=int(val), key=f"cap_{lg}")
        add_lg = st.text_input("Add league cap (optional, e.g., MLB)")
        add_val = st.number_input("  value for new league", min_value=0, value=0, key="cap_new")

        dup_sec = st.number_input("Duplicate guard window (seconds)", min_value=0, value=int(risk.get("duplicate_guard_sec", 10)))
        corr_max = st.number_input("Correlation guard: max open positions per team", min_value=0, value=int(risk.get("correlation_guard", {}).get("max_same_team_open", 3)))

        st.subheader("Auto-disable thresholds")
        psi_soft = st.number_input("PSI soft", min_value=0.0, max_value=1.0, value=float(drift.get("psi_soft", 0.15)), step=0.01)
        psi_hard = st.number_input("PSI hard", min_value=0.0, max_value=1.0, value=float(drift.get("psi_hard", 0.25)), step=0.01)
        ks_soft  = st.number_input("KS p soft", min_value=0.0, max_value=1.0, value=float(drift.get("ks_p_soft", 0.01)), step=0.001, format="%.3f")
        ks_hard  = st.number_input("KS p hard", min_value=0.0, max_value=1.0, value=float(drift.get("ks_p_hard", 0.001)), step=0.001, format="%.3f")
        clv_min  = st.number_input("KPI: min CLV (bps)", value=float(kpi.get("clv_bps_min", -75.0)), step=1.0)
        ev_min   = st.number_input("KPI: min EV (%)", value=float(kpi.get("ev_pct_min", -1.5)), step=0.1)

        saved = st.form_submit_button("Save")
        if saved:
            risk["kill_switch"] = bool(ks)
            risk.setdefault("exposure_caps", {})
            risk["exposure_caps"]["total_usd"] = int(tot_cap)
            risk["exposure_caps"]["per_league"] = {**per_league, **edits}
            if add_lg.strip():
                risk["exposure_caps"]["per_league"][add_lg.strip().upper()] = int(add_val)
            risk["duplicate_guard_sec"] = int(dup_sec)
            risk["correlation_guard"] = {"max_same_team_open": int(corr_max)}
            _yaml_dump(RISK_YAML, risk)

            thr["drift"] = {
                "psi_soft": float(psi_soft),
                "psi_hard": float(psi_hard),
                "ks_p_soft": float(ks_soft),
                "ks_p_hard": float(ks_hard),
            }
            thr["kpi"] = {"clv_bps_min": float(clv_min), "ev_pct_min": float(ev_min)}
            _yaml_dump(THRESH_YAML, thr)
            st.success("Saved risk & thresholds ✅")

    # Convenience reset (outside form)
    if st.button("Reset thresholds to defaults"):
        _ensure_defaults()
        st.experimental_rerun()

with tab2:
    st.subheader("Per-book toggles and defaults")
    b = _yaml_load(BROKERS_YAML)
    with st.form("books_form"):
        cols = st.columns(3)
        updates = {}
        for i, book in enumerate(("pinnacle", "sbo", "isn")):
            with cols[i]:
                st.markdown(f"### {book.upper()}")
                bk = b.get(book, {})
                pause = st.toggle("Pause", value=bool(bk.get("pause", False)), key=f"{book}_pause")
                fee   = st.number_input("Fee (bps)", min_value=0, max_value=200, value=int(bk.get("fee_bps", 6 if book != "pinnacle" else 8)), key=f"{book}_fee")
                slip  = st.number_input("Default slippage (bps)", min_value=0, max_value=1000, value=int(bk.get("slippage_bps_default", 40)), key=f"{book}_slip")
                updates[book] = {"pause": bool(pause), "fee_bps": int(fee), "slippage_bps_default": int(slip), "api": bk.get("api", {})}
        saved = st.form_submit_button("Save")
        if saved:
            for k, v in updates.items():
                b[k] = {**b.get(k, {}), **v}
            _yaml_dump(BROKERS_YAML, b)
            st.success("Saved broker settings ✅")

with tab3:
    st.subheader("Recent Executions (audit)")
    n = st.slider("Rows", min_value=50, max_value=10000, value=500, step=50)
    if EXEC_LOG.exists():
        rows = []
        with open(EXEC_LOG, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
        if rows:
            df = pd.DataFrame(rows)
            cols = [c for c in ["ts","book","league","market","selection","client_order_id","entry_prob","exec_prob","stake","note","fee_bps"] if c in df.columns]
            if "ts" in df.columns:
                try:
                    df["ts"] = pd.to_datetime(df["ts"], unit="s", errors="coerce")
                except Exception:
                    pass
                df = df.sort_values("ts", ascending=False)
            st.dataframe(df[cols].head(n), use_container_width=True)
            st.download_button("Download CSV", data=df.to_csv(index=False), file_name="executions_audit.csv", mime="text/csv")
        else:
            st.info("No parsed rows yet.")
    else:
        st.info("No audit log found. Place some demo orders first (py -m src.flows.demo_place_orders).")
