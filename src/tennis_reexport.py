import argparse
import pandas as pd
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--gate", type=float, default=0.01)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv)

    # Expect 'edge' column (fraction, e.g. 0.012 for 1.2%)
    if "edge" not in df.columns and "model_edge" in df.columns:
        df = df.rename(columns={"model_edge": "edge"})

    gated = df[df["edge"] >= args.gate].copy()

    # Basic summaries
    def summarize(d: pd.DataFrame) -> dict:
        out = {}
        out["n"] = len(d)
        if "result" in d.columns:
            out["win_rate"] = d["result"].mean()
        if "edge" in d.columns:
            out["mean_edge"] = d["edge"].mean()
        if "decimal_odds" in d.columns:
            out["avg_odds"] = d["decimal_odds"].mean()
        return out

    summary_all = summarize(df)
    summary_gate = summarize(gated)

    df.to_csv(f"{args.out_dir}/per_bet_execution_full.csv", index=False)
    gated.to_csv(f"{args.out_dir}/per_bet_execution_1p.csv", index=False)
    pd.DataFrame([summary_all]).to_csv(f"{args.out_dir}/summary_full.csv", index=False)
    pd.DataFrame([summary_gate]).to_csv(f"{args.out_dir}/summary_gate_selected_1p.csv", index=False)

if __name__ == "__main__":
    main()
