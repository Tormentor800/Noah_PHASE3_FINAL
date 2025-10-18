import os, json, math, random
import numpy as np
import pandas as pd

# Dependencies: sklearn, shap, lime, matplotlib
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import shap
from lime import lime_tabular
import matplotlib.pyplot as plt

OUT_DIR = os.path.join("artifacts", "explain_shaplime")
os.makedirs(OUT_DIR, exist_ok=True)

def synthetic_bets(n=50, seed=42):
    rng = np.random.default_rng(seed)
    # 8 toy features roughly mimicking bet attributes
    X, y = make_classification(n_samples=n, n_features=8, n_informative=5, n_redundant=1,
                               n_clusters_per_class=1, class_sep=1.0, random_state=seed)
    cols = [f"feat_{i}" for i in range(X.shape[1])]
    df = pd.DataFrame(X, columns=cols)
    df["target"] = y
    return df, cols

def train_model(df, feature_cols):
    X = df[feature_cols].values
    y = df["target"].values
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=200))
    ])
    pipe.fit(X, y)
    return pipe

def compute_shap(pipe, X, feature_names):
    # Use KernelExplainer if pipeline; sample a background for speed
    bg_idx = np.random.choice(len(X), size=min(20, len(X)), replace=False)
    background = X[bg_idx]
    f = lambda data: pipe.predict_proba(data)[:,1]
    explainer = shap.KernelExplainer(f, background)
    # Explain up to 50 rows
    nsamp = min(50, len(X))
    shap_vals = explainer.shap_values(X[:nsamp], nsamples=100)
    # shap_values shape: (nsamp, n_features)
    shap_matrix = np.array(shap_vals)
    return shap_matrix, nsamp

def compute_lime(pipe, X, feature_names, nsamp):
    explainer = lime_tabular.LimeTabularExplainer(
        X, feature_names=feature_names, class_names=["no","yes"], discretize_continuous=True, verbose=False
    )
    weights = []
    for i in range(nsamp):
        exp = explainer.explain_instance(X[i], pipe.predict_proba, num_features=min(5, len(feature_names)))
        # exp.as_list(): list of (feature_clause, weight)
        w = dict(exp.as_list())
        weights.append(w)
    return weights

def topk_from_vector(vec, names, k=5):
    idx = np.argsort(np.abs(vec))[::-1][:k]
    return [(names[i], float(vec[i])) for i in idx]

def main():
    df, feats = synthetic_bets(50)
    pipe = train_model(df, feats)
    X = df[feats].values

    shap_matrix, nsamp = compute_shap(pipe, X, feats)
    lime_weights = compute_lime(pipe, X, feats, nsamp)

    # Build per-row top factors (SHAP primary; include LIME for reference)
    rows = []
    agg_abs = np.zeros(len(feats), dtype=float)
    for i in range(nsamp):
        tv = shap_matrix[i]  # vector
        top = topk_from_vector(tv, feats, k=min(5, len(feats)))
        # accumulate abs for aggregate importance
        agg_abs += np.abs(tv)
        row = {
            "row_id": i,
            "top_factors_shap": json.dumps(top, ensure_ascii=False),
            "lime_top": json.dumps(sorted(lime_weights[i].items(), key=lambda t: abs(t[1]), reverse=True)[:5], ensure_ascii=False)
        }
        rows.append(row)

    out_csv = os.path.join(OUT_DIR, "top_factors.csv")
    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8")

    # Aggregate plot
    imp = pd.Series(agg_abs, index=feats) / nsamp
    imp = imp.sort_values(ascending=False)

    plt.figure(figsize=(8, 5))
    imp.head(10).plot(kind="barh")
    plt.gca().invert_yaxis()
    plt.title("Top Features (avg |SHAP| over 50 samples)")
    plt.tight_layout()
    out_png = os.path.join(OUT_DIR, "top_factors.png")
    plt.savefig(out_png, dpi=150)
    plt.close()

    print(f"Wrote {out_csv}")
    print(f"Wrote {out_png}")

if __name__ == "__main__":
    main()
