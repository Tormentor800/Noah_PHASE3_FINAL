# Explainability Exports (SHAP / LIME)

**Purpose:** Provide per-sample evidence for top factors influencing model output.

## Artifacts
- `artifacts/shap_snapshot.csv` — feature, shap_value (top-N)
- `artifacts/shap_snapshot.png` — horizontal bar chart of SHAP top factors
- `artifacts/lime_snapshot.png` — LIME local explanation plot
- `artifacts/snapshot_features.json` — the features used for the snapshot

## How to refresh
```powershell
py -m pip install shap lime
py -m src.serve.shap_lime_export
