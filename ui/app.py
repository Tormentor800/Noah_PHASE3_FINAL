import os
import io
import yaml
import streamlit as st
from datetime import datetime
from typing import Dict, Any

CFG_PATH = "config.yml"
AUDIT_LOG = os.path.join("logs", "audit.log")

st.set_page_config(page_title="Noah Admin", page_icon="🛠", layout="centered")

def load_config(path: str = CFG_PATH) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"risk": {}, "books": {}}
    with open(path, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f) or {}
    # sane defaults
    y.setdefault("risk", {})
    y["risk"].setdefault("kill_switch", False)
    y["risk"].setdefault("max_corr", 0.70)
    y["risk"].setdefault("corr_min_series", 5)
    y.setdefault("books", {})
    y["books"].setdefault("pinnacle_enabled", True)
    y["books"].setdefault("sbo_enabled", True)
    y["books"].setdefault("isn_enabled", True)
    return y

def save_config(cfg: Dict[str, Any], path: str = CFG_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=True, allow_unicode=True)

def log_action(msg: str) -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts}  {msg}\n")

st.title("Noah Admin UI")

tabs = st.tabs(["⚠️ Risk Controls", "📚 Books", "🧾 Audit Log"])

# ---------------- Risk Controls ----------------
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

# ---------------- Books ----------------
with tabs[1]:
    cfg = load_config()  # reload to reflect any tab1 changes immediately
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

    st.info("Adapters should check these flags before placing orders (e.g., skip API call if disabled).")

# ---------------- Audit Log ----------------
with tabs[2]:
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
