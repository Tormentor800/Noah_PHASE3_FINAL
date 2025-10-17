import argparse
import pandas as pd
from datetime import timedelta
from utils.clv_eval import compute_clv

def normalize_teams(s: str) -> str:
    return str(s).strip().lower()

def merge_exec_with_closing(exec_df: pd.DataFrame, closing_df: pd.DataFrame, date_tolerance_days: int = 0) -> pd.DataFrame:
    # Normalize keys
    for df in (exec_df, closing_df):
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date
        for col in ["home_team", "away_team"]:
            if col in df.columns:
                df[col] = df[col].apply(normalize_teams)

    # Try merge by event_id first
    if "event_id" in exec_df.columns and "event_id" in closing_df.columns:
        merged = exec_df.merge(closing_df, on="event_id", how="left", suffixes=("", "_close"))
        return merged

    # Fallback: merge by (date, home, away) exact
    merged = exec_df.merge(closing_df, on=["date", "home_team", "away_team"], how="left", suffixes=("", "_close"))
    if merged[["close_home","close_away"]].isna().all(axis=None) and date_tolerance_days > 0:
        # Tolerant merge: try +/- days
        tol = timedelta(days=date_tolerance_days)
        exec_df["date_dt"] = pd.to_datetime(exec_df["date"])
        closing_df["date_dt"] = pd.to_datetime(closing_df["date"])
        cand = []
        for k, r in exec_df.iterrows():
            d0 = r["date_dt"]
            lo, hi = d0 - tol, d0 + tol
            subset = closing_df[(closing_df["home_team"] == r["home_team"]) &
                                (closing_df["away_team"] == r["away_team"]) &
                                (closing_df["date_dt"] >= lo) & (closing_df["date_dt"] <= hi)]
            if subset.empty:
                cand.append(r.to_frame().T.assign(close_home=pd.NA, close_draw=pd.NA, close_away=pd.NA))
            else:
                best = subset.iloc[0]
                row = r.to_dict()
                row.update({
                    "close_home": best.get("close_home"),
                    "close_draw": best.get("close_draw"),
                    "close_away": best.get("close_away"),
                })
                cand.append(pd.DataFrame([row]))
        merged = pd.concat(cand, ignore_index=True)
        merged.drop(columns=["date_dt"], errors="ignore", inplace=True)
    return merged

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exec_csv", required=True)
    ap.add_argument("--closing_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--summary_csv", required=True)
    ap.add_argument("--date_tolerance_days", type=int, default=0)
    args = ap.parse_args()

    exec_df = pd.read_csv(args.exec_csv)
    closing_df = pd.read_csv(args.closing_csv)

    merged = merge_exec_with_closing(exec_df, closing_df, args.date_tolerance_days)
    out = compute_clv(merged)

    # Save full dataset
    out.to_csv(args.out_csv, index=False)

    # Summary
    summary = {
        "n": len(out),
        "mean_clv": out["clv"].mean(skipna=True),
        "median_clv": out["clv"].median(skipna=True),
        "pct_pos_clv": (out["clv"] > 0).mean(skipna=True),
    }
    pd.DataFrame([summary]).to_csv(args.summary_csv, index=False)

if __name__ == "__main__":
    main()
