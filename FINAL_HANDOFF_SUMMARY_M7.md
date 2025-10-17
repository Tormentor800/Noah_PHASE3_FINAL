# Final Handoff – Milestone 7 (Phase 3)
**Project:** Noah – Phase 3 (Retraining + SHAP/LIME + Dashboards)  
**Release:** v1.0.0  
**Owner:** Igor Todorovski

---

## 1) What’s Included (at a glance)
- **Automation**
  - Daily **drift watch** (PSI/KS) → logs to `logs/drift_watch.log`
  - **Monthly retrain** (1st @ 03:15) → logs to `logs/monthly_retrain.log`
- **API (FastAPI on Uvicorn)**
  - `/health`, `/predict`, `/explain` (SHAP active)
- **Explainability**
  - Real **SHAP LinearExplainer** with background; robust fallback
- **Config-as-Code**
  - `config/thresholds.yaml` → drift + KPI gates
- **Dashboards**
  - Streamlit drift/health demo at port `8501`
- **Artifacts & Versioning**
  - `artifacts/model.joblib` (v1.0.0), easy rollback (copy/rename)
- **Ops**
  - Windows Task Scheduler via wrapper PS1 scripts
  - Logs and (optional) heartbeat files
- **Tests**
  - 3 smoke tests passing (health, predict, loader)

---

## 2) How to Run
### API
```powershell
py -m uvicorn src.serve.api:app --host 127.0.0.1 --port 9010
# Swagger: http://127.0.0.1:9010/docs
```

### Jobs (manual)
```powershell
py -m src.flows.drift_watch
py -m src.flows.monthly_retrain
```

### Dashboard
```powershell
py -m streamlit run dashboards\m7_drift_perf_app.py --server.port 8501
```

---

## 3) Scheduled Tasks (Windows)
Scripts in project root:
- `run_drift_watch.ps1`
- `run_monthly_retrain.ps1`

Registered tasks:
- **M7_DriftWatch** → Daily 09:05
- **M7_MonthlyRetrain** → Monthly (1st) 03:15

Check:
```powershell
schtasks /Query /TN "M7_DriftWatch" /V /FO LIST
schtasks /Query /TN "M7_MonthlyRetrain" /V /FO LIST
```

Logs:
```
logs/drift_watch.log
logs/monthly_retrain.log
# optional heartbeats if enabled:
logs/drift_watch.lastok.txt
logs/monthly_retrain.lastok.txt
```

---

## 4) Validation Evidence
- `/health` → `{ "ok": true }`
- `/predict` → returns `{version, prob, fair_price, edge_bp}`
- `/explain` (with SHAP) → **non-zero base** and fractional `top_features`
- `pytest` → **3 passed**, no warnings (after UTC fix)

---

## 5) Configuration
`config/thresholds.yaml`
```yaml
drift:
  psi_warn: 0.10
  psi_fail: 0.25
  ks_p_fail: 0.01
kpis:
  clv_14d_bps_min: 0
  clv_7d_bps_min: -75
  ev_7d_pct_min: -1.5
```
Adjust as real data dictates.

---

## 6) Directory Structure (key paths)
```
src/
  common/     # model I/O, metrics, flags
  data/       # extract.py (UTC-normalized loader)
  flows/      # drift_watch, monthly_retrain
  serve/      # FastAPI API + SHAP explain
dashboards/   # streamlit app(s)
artifacts/    # model.joblib (v1.0.0)
config/       # thresholds.yaml
logs/         # job logs (+ optional heartbeats)
tests/        # 3 smoke tests
README_M7.md
```

---

## 7) One-Command Release (local zip)
Use the provided `make_release.ps1` (see below) to produce a release zip named like:
```
M7_Phase3_v1.0.0_YYYYMMDD-HHMM.zip
```

---

## 8) Next (optional)
- Slack alerts on drift/retrain results
- Hook real data (Postgres/S3) into loader & dashboard
- Simple registry: save metrics JSON next to each model + safe promotion rules
- CI smoketests (GitHub Actions)

---

## 9) Contact
Questions or changes? Ping Igor.
