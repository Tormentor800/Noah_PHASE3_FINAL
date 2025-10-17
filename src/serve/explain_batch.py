# src/serve/explain_batch.py
from __future__ import annotations
import os, shutil, json, random
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

from src.serve.shap_lime_export import export_shap_snapshot, export_lime_snapshot, _build_background_from_point

ART = Path("artifacts")
OUT = ART / "explain_shaplime"
OUT.mkdir(parents=True, exist_ok=True)

def _one(features: Dict[str, float], idx: int) -> None:
    # optional small jittered background per sample for variety
    bg = _build_background_from_point(features, n=128, std=0.08)

    shap_png = export_shap_snapshot(features, background=bg.to_dict(orient="records"))
    lime_png = export_lime_snapshot(features, background=bg.to_dict(orient="records"))

    # copy/rename outputs so we keep all snapshots
    # SHAP
    (OUT / f"shap_{idx:03d}.png").write_bytes(Path(shap_png).read_bytes())
    # the per-call CSV lives here:
    shap_csv = ART / "shap_snapshot.csv"
    if shap_csv.exists():
        (OUT / f"shap_{idx:03d}.csv").write_bytes(shap_csv.read_bytes())

    # LIME (if created)
    if lime_png and os.path.exists(lime_png):
        (OUT / f"lime_{idx:03d}.png").write_bytes(Path(lime_png).read_bytes())

    # keep the features used
    (OUT / f"features_{idx:03d}.json").write_text(json.dumps(features, indent=2), encoding="utf-8")

def run(n: int = 50) -> None:
    # demo: random features in [0,1]
    for i in range(n):
        features = {
            "feat_a": round(random.uniform(0.0, 1.0), 3),
            "feat_b": round(random.uniform(0.0, 1.0), 3),
        }
        _one(features, i)

    (OUT / "README.txt").write_text(
        f"Explainability batch generated at {datetime.utcnow().isoformat()}Z\n"
        f"- shap_###.png / shap_###.csv / lime_###.png\n"
        f"- features_###.json contain inputs used for each snapshot\n",
        encoding="utf-8",
    )
    print(f"Wrote SHAP/LIME batch → {OUT}")

if __name__ == "__main__":
    run()
