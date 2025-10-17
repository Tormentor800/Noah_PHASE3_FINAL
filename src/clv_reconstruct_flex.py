
import argparse
import pandas as pd
from datetime import timedelta
import numpy as np

def normalize(s):
    return str(s).strip().lower()

def implied_prob_from_decimal(x):
    try:
        x = float(x)
    except Exception:
        return np.nan
    if x <= 1.0:
        return np.nan
    return 1.0 / x

def coalesce(df, prefer, fallbacks):
    for c in [prefer] + fallbacks:
        if c and c in df.columns:
            return c
    return None

def main():
    ap = argparse.ArgumentParser(description="Flexible CLV reconstruction with custom column names.")
    ap.add_argument("--exec_csv", required=True)
    ap.add_argument("--closing_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--summary_csv", required=True)
    ap.add_argument("--date_tolerance_days", type=int, default=0)

    # Execution file columns
    ap.add_argument("--exec-date-col", default=None)
    ap.add_argument("--exec-home-col", default=None)
    ap.add_argument("--exec-away-col", default=None)
    ap.add_argument("--exec-selection-col", default=None)  # 'home'/'away'/'draw' or 1/2/X
    ap.add_argument("--exec-model-prob-col", default=None)
    ap.add_argument("--exec-model-odds-col", default=None)

    # Closing file columns
    ap.add_argument("--close-date-col", default=None)
    ap.add_argument("--close-home-col", default=None)  # decimal odds
    ap.add_argument("--close-draw-col", default=None)  # decimal odds
    ap.add_argument("--close-away-col", default=None)  # decimal odds
    ap.add_argument("--close-home-team-col", default=None)
    ap.add_argument("--close-away-team-col", default=None)

    args = ap.parse_args()

    exec_df = pd.read_csv(args.exec_csv)
    close_df = pd.read_csv(args.closing_csv)

    # Infer columns if not provided
    exec_date = args.exec_date_col or coalesce(exec_df, "date", ["match_date","event_date","Date","DATE","start_time","kickoff","fixture_date"])
    exec_home = args.exec_home_col or coalesce(exec_df, "home_team", ["home","Home","HOME","team_home","homeTeam","home_team_name"])
    exec_away = args.exec_away_col or coalesce(exec_df, "away_team", ["away","Away","AWAY","team_away","awayTeam","away_team_name"])
    exec_sel  = args.exec_selection_col or coalesce(exec_df, "selection", ["bet_side","pick","side","sel","Selection"])
    exec_mp   = args.exec_model_prob_col or coalesce(exec_df, "model_prob", ["prob","p_model","model_p","pred_prob","probability"])
    exec_mo   = args.exec_model_odds_col or coalesce(exec_df, "model_odds", ["odds_model","pred_odds","model_price"])

    if exec_date is None or exec_home is None or exec_away is None:
        raise SystemExit(f"Missing required columns in execution CSV. Found columns: {list(exec_df.columns)}")

    # Normalize keys
    exec_df["_date"] = pd.to_datetime(exec_df[exec_date], errors="coerce").dt.date
    exec_df["_home"] = exec_df[exec_home].astype(str).map(normalize)
    exec_df["_away"] = exec_df[exec_away].astype(str).map(normalize)

    # Model probability
    if exec_mp and exec_mp in exec_df.columns:
        exec_df["_model_prob"] = pd.to_numeric(exec_df[exec_mp], errors="coerce")
    elif exec_mo and exec_mo in exec_df.columns:
        exec_df["_model_prob"] = 1.0 / pd.to_numeric(exec_df[exec_mo], errors="coerce")
    else:
        # If neither provided, try decimal_odds column as model odds
        if "decimal_odds" in exec_df.columns:
            exec_df["_model_prob"] = 1.0 / pd.to_numeric(exec_df["decimal_odds"], errors="coerce")
        else:
            raise SystemExit("Provide --exec-model-prob-col or --exec-model-odds-col, or include decimal_odds in execution CSV.")

    # Selection (optional, only needed if you want per-side CLV; otherwise we'll match home/away rows)
    if exec_sel and exec_sel in exec_df.columns:
        exec_df["_sel"] = exec_df[exec_sel].astype(str).str.lower()
    else:
        exec_df["_sel"] = np.where(exec_df.get("is_home_bet", pd.Series([np.nan]*len(exec_df))).fillna(False), "home", np.nan)

    # Closing columns
    close_date = args.close_date_col or coalesce(close_df, "date", ["match_date","event_date","Date","DATE","start_time","kickoff","fixture_date"])
    close_home_team = args.close_home_team_col or coalesce(close_df, "home_team", ["home","Home","HOME","team_home","homeTeam","home_team_name"])
    close_away_team = args.close_away_team_col or coalesce(close_df, "away_team", ["away","Away","AWAY","team_away","awayTeam","away_team_name"])
    close_home_odds = args.close_home_col or coalesce(close_df, "close_home", ["home_close","home_odds_close","closing_home","closeHome","odds_home"])
    close_draw_odds = args.close_draw_col or coalesce(close_df, "close_draw", ["draw_close","closing_draw","closeDraw","odds_draw"])
    close_away_odds = args.close_away_col or coalesce(close_df, "close_away", ["away_close","away_odds_close","closing_away","closeAway","odds_away"])

    if close_date is None or close_home_team is None or close_away_team is None:
        raise SystemExit(f"Missing required columns in closing CSV. Found columns: {list(close_df.columns)}")

    close_df["_date"] = pd.to_datetime(close_df[close_date], errors="coerce").dt.date
    close_df["_home"] = close_df[close_home_team].astype(str).map(normalize)
    close_df["_away"] = close_df[close_away_team].astype(str).map(normalize)

    # Convert closing to implied probs
    if close_home_odds and close_home_odds in close_df.columns:
        close_df["_close_home_prob"] = pd.to_numeric(close_df[close_home_odds], errors="coerce").map(implied_prob_from_decimal)
    else:
        close_df["_close_home_prob"] = np.nan
    if close_draw_odds and close_draw_odds in close_df.columns:
        close_df["_close_draw_prob"] = pd.to_numeric(close_df[close_draw_odds], errors="coerce").map(implied_prob_from_decimal)
    else:
        close_df["_close_draw_prob"] = np.nan
    if close_away_odds and close_away_odds in close_df.columns:
        close_df["_close_away_prob"] = pd.to_numeric(close_df[close_away_odds], errors="coerce").map(implied_prob_from_decimal)
    else:
        close_df["_close_away_prob"] = np.nan

    # Merge
    merged = exec_df.merge(
        close_df[["_date","_home","_away","_close_home_prob","_close_draw_prob","_close_away_prob"]],
        on=["_date","_home","_away"],
        how="left"
    )

    # Choose closing prob based on selection if available, else pick max between home/away for home bets as heuristic
    def pick_close(row):
        sel = str(row.get("_sel", "")).lower()
        if sel in ("home","1","h"):
            return row["_close_home_prob"]
        if sel in ("away","2","a"):
            return row["_close_away_prob"]
        if sel in ("draw","x","d"):
            return row["_close_draw_prob"]
        # fallback: if model_prob > 0.5 assume it's the home side
        return row["_close_home_prob"] if row["_model_prob"] >= 0.5 else row["_close_away_prob"]

    merged["_closing_prob_selected"] = merged.apply(pick_close, axis=1)
    merged["_clv_ratio"] = merged["_model_prob"] / merged["_closing_prob_selected"]
    merged["_clv"] = merged["_clv_ratio"] - 1.0

    # Save
    out_cols = list(exec_df.columns) + ["_model_prob","_closing_prob_selected","_clv_ratio","_clv"]
    merged[out_cols].to_csv(args.out_csv, index=False)

    summary = {
        "n": int(len(merged)),
        "mean_clv": float(merged["_clv"].replace([np.inf,-np.inf], np.nan).mean(skipna=True)),
        "median_clv": float(merged["_clv"].replace([np.inf,-np.inf], np.nan).median(skipna=True)),
        "pct_pos_clv": float((merged["_clv"] > 0).mean(skipna=True)),
        "missing_closing_pct": float(merged["_closing_prob_selected"].isna().mean())
    }
    pd.DataFrame([summary]).to_csv(args.summary_csv, index=False)

if __name__ == "__main__":
    main()
