import os
import yaml
import requests
import streamlit as st
from datetime import datetime

CFG_PATH = "config.yml"
AUDIT_LOG = os.path.join("logs", "audit.log")
API_BASE = os.environ.get("API_BASE", "http://api:9010")

st.set_page_config(page_title="Noah Admin", page_icon="??", layout="centered")

def load_config(path: str = CFG_PATH):
    if not os.path.exists(path):
        return {"risk": {}, "books": {}}
    with open(path, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f) or {}
    y.setdefault("risk", {})
    y["risk"].setdefault("kill_switch", False)
    y["risk"].setdefault("max_corr", 0.70)
    y["risk"].setdefault("corr_min_series", 5)
    y.setdefault("books", {})
    y["books"].setdefault("pinnacle_enabled", True)
    y["books"].setdefault("sbo_enabled", True)
    y["books"].setdefault("isn_enabled", True)
    return y

def save_config(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=True, allow_unicode=True)

def log_action(msg: str):
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts}  {msg}\n")

st.title("Noah Admin UI")

tabs = st.tabs(["?? Risk Controls", "?? Books", "?? Composite", "?? Audit Log"])

# ---------- Risk Controls ----------
with tabs[0]:
    cfg = load_config()
    st.subheader("Risk Controls")

    ks = st.toggle("Kill Switch (block all new entries)", value=bool(cfg["risk"]["kill_switch"]))
    col1, col2 = st.columns(2)
    with col1:
        max_corr = st.slider("Max Correlation Threshold", 0.0, 1.0, float(cfg["risk"]["max_corr"]), 0.05)
    with col2:
        min_series = st.number_input("Correlation Min Series", min_value=1, value=int(cfg["risk"]["corr_min_series"]), step=1)

    if st.button("Save Risk Settings"):
        cfg["risk"]["kill_switch"] = bool(ks)
        cfg["risk"]["max_corr"] = float(max_corr)
        cfg["risk"]["corr_min_series"] = int(min_series)
        save_config(cfg)
        log_action(f"risk.update kill_switch={ks} max_corr={max_corr} corr_min_series={min_series}")
        st.success("Risk settings saved.")

# ---------- Books ----------
with tabs[1]:
    cfg = load_config()
    st.subheader("Per-Book Toggles")

    p_enabled = st.toggle("Enable Pinnacle", value=bool(cfg["books"]["pinnacle_enabled"]))
    s_enabled = st.toggle("Enable SBO",      value=bool(cfg["books"]["sbo_enabled"]))
    i_enabled = st.toggle("Enable ISN",      value=bool(cfg["books"]["isn_enabled"]))

    if st.button("Save Book Settings"):
        cfg["books"]["pinnacle_enabled"] = bool(p_enabled)
        cfg["books"]["sbo_enabled"] = bool(s_enabled)
        cfg["books"]["isn_enabled"] = bool(i_enabled)
        save_config(cfg)
        log_action(f"books.update pinnacle={p_enabled} sbo={s_enabled} isn={i_enabled}")
        st.success("Book settings saved.")

    st.info("Adapters should check these flags before placing orders (skip calls if disabled).")

# ---------- Composite ----------
with tabs[2]:
    st.subheader("Prematch Odds Composite")
    league = st.text_input("League", value="NBA")
    market = st.text_input("Market", value="ML")
    base_odds = st.number_input("Base odds (seed)", value=1.95, min_value=1.01, step=0.01, format="%.2f")

    col = st.columns(2)
    with col[0]:
        hit = st.button("Get Composite")
    with col[1]:
        api_base = st.text_input("API Base", value=API_BASE)

    if hit:
        try:
            url = f"{api_base}/composite"
            params = {"league": league, "market": market, "base_odds": base_odds}
            r = requests.get(url, params=params, timeout=5)
            r.raise_for_status()
            data = r.json()
            st.success("Composite fetched.")
            st.json(data)
            # Pretty sources table
            if "sources" in data:
                st.write("Sources")
                st.dataframe(data["sources"])
            log_action(f"composite.query league={league} market={market} base={base_odds}")
        except Exception as e:
            st.error(f"Failed to fetch composite: {e}")

# ---------- Audit Log ----------
with tabs[3]:
    st.subheader("Audit Log")
    if os.path.exists(AUDIT_LOG):
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            txt = f.read()
        st.text_area("Log", value=txt, height=260)
    else:
        st.write("No audit log yet.")

    new_entry = st.text_input("Add entry")
    if st.button("Append to Audit Log", disabled=(new_entry.strip() == "")):
        log_action(new_entry.strip())
        st.success("Entry appended. Refresh to see the update.")
