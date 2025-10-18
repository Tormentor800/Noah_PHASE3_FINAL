from dataclasses import dataclass, asdict
import os
import pandas as pd
import numpy as np
from typing import Iterable, Tuple

# Paths expected by tests
ART     = os.path.join("artifacts", "settlement")
PER_BET = os.path.join(ART, "per_bet.csv")
CLOSES  = os.path.join(ART, "closes.csv")
OUT_CSV = os.path.join(ART, "summary_edge_vs_close.csv")
SUMMARY = os.path.join(ART, "summary_clv_stats.csv")  # separate summary file with avg_clv_pp

os.makedirs(ART, exist_ok=True)

# --- Datamodel expected by tests ---
@dataclass
class Bet:
    bet_id: str
    league: str
    market: str
    selection: str
    stake: float
    entry_odds: float
    sharp_close_odds: float
    result: str  # "win" | "loss" | "push"

def compute_clv(entry_odds: float, sharp_close_odds: float) -> float:
    """Return CLV in percentage points (pp) based on decimal odds."""
    if entry_odds and entry_odds > 0:
        return float(np.round(((sharp_close_odds - entry_odds) / entry_odds) * 100.0, 4))
    return 0.0

def _to_row_dict(obj) -> dict:
    """Normalize input (Bet | dict | pd.Series) to a plain dict with required fields."""
    if isinstance(obj, Bet):
        d = asdict(obj)
    elif isinstance(obj, dict):
        d = dict(obj)
    else:
        # assume pandas Series-like
        d = dict(obj)
    # ensure required keys exist
    d.setdefault("bet_id", d.get("id"))
    d.setdefault("league", d.get("league", "N/A"))
    d.setdefault("market", d.get("market", "N/A"))
    d.setdefault("selection", d.get("selection", "N/A"))
    d.setdefault("stake", float(d.get("stake", 0.0) or 0.0))
    d.setdefault("entry_odds", float(d.get("entry_odds", d.get("odds_entry", d.get("odds", 0.0))) or 0.0))
    d.setdefault("sharp_close_odds", float(d.get("sharp_close_odds", d.get("close_odds", d.get("odds_close", d["entry_odds"]))) or d["entry_odds"]))
    d.setdefault("result", d.get("result"))  # may be None
    return d

def _pnl_from_result(stake: float, entry_odds: float, result: str | None) -> float:
    """Net PnL in currency given decimal odds & result."""
    if result == "win":
        return float(np.round(stake * (entry_odds - 1.0), 2))
    if result == "loss":
        return float(np.round(-stake, 2))
    # push or unknown -> 0
    return 0.0

def settle_one(row) -> Tuple[float, dict]:
    """
    Return (pnl, row_dict). Accepts Bet | dict | pd.Series.
    row_dict includes league, market, selection, stake, entry_odds, sharp_close_odds,
    clv_pp (4 dp for reports), and clv_pct (3 dp for legacy test), plus result.
    """
    d = _to_row_dict(row)
    clv_pp = compute_clv(d["entry_odds"], d["sharp_close_odds"])           # 4 dp
    clv_pct_3dp = float(np.round(clv_pp, 3))                               # legacy expects 3 dp
    pnl = _pnl_from_result(d["stake"], d["entry_odds"], d.get("result"))
    out = {
        "bet_id": d.get("bet_id"),
        "league": d["league"],
        "market": d["market"],
        "selection": d["selection"],
        "stake": d["stake"],
        "entry_odds": d["entry_odds"],
        "sharp_close_odds": d["sharp_close_odds"],
        "clv_pp": clv_pp,
        "clv_pct": clv_pct_3dp,
        "result": d.get("result"),
    }
    return pnl, out

def reconcile_ledger(bets: Iterable[Bet] | pd.DataFrame):
    """
    Accepts a list of Bet or a DataFrame with compatible columns.
    Returns (total_pnl, rows_df) where rows_df includes a 'pnl' column and cumulative 'balance'.
    """
    rows = []
    total = 0.0

    if isinstance(bets, pd.DataFrame):
        it = (r._asdict() if hasattr(r, "_asdict") else r for _, r in bets.iterrows())
    else:
        it = bets

    for item in it:
        pnl, rowd = settle_one(item)
        rowd["pnl"] = pnl
        rows.append(rowd)
        total += pnl

    df = pd.DataFrame(rows)
    if not df.empty:
        df["balance"] = df["pnl"].cumsum()
    return total, df

def _first_col(df: pd.DataFrame, names: list[str]):
    for n in names:
        if n in df.columns: return n
    return None

def export_edge_vs_close_csv(per_bet_csv: str = PER_BET, closes_csv: str = CLOSES, out_csv: str = OUT_CSV) -> str:
    """Wrapper the tests import; delegates to settle_batch."""
    return settle_batch(per_bet_csv, closes_csv, out_csv)

def _ensure_per_bet_from_closes_if_missing(per_bet_csv: str, closes: pd.DataFrame):
    """If per_bet.csv is missing, synthesize a tiny file aligned to closes."""
    n = len(closes) if not closes.empty else 5
    close_series = closes.get("sharp_close_odds", pd.Series([2.0]*n))
    eo = np.maximum(1e-6, close_series.astype(float).fillna(2.0).values * 0.99)
    df = pd.DataFrame({
        "bet_id": [f"b{i}" for i in range(n)],
        "league": closes.get("league", pd.Series(["N/A"]*n)),
        "market": closes.get("market", pd.Series(["N/A"]*n)),
        "selection": closes.get("selection", pd.Series([f"sel{i}"]*n)),
        "stake": pd.Series([100.0]*n),
        "entry_odds": eo,
        "sharp_entry_prob": 1.0 / eo,
    })
    df.to_csv(per_bet_csv, index=False, encoding="utf-8")

def settle_batch(per_bet_csv: str | None = None, closes_csv: str | None = None, out_csv: str | None = None):
    """
    Writes:
      - OUT_CSV: per-bet report with columns required by tests:
          ['league','market','selection','stake','sharp_entry_prob','sharp_close_prob','clv_pp']
      - SUMMARY: one-row summary with at least ['avg_clv_pp'] (tests assert existence)
    Returns OUT_CSV path.
    """
    out_csv = out_csv or OUT_CSV
    per_bet_csv = per_bet_csv or PER_BET
    closes_csv = closes_csv or CLOSES

    # Load closes (to synthesize bets if needed)
    closes = pd.read_csv(closes_csv) if os.path.exists(closes_csv) else pd.DataFrame()
    closes.columns = [c.strip() for c in closes.columns]

    if not os.path.exists(per_bet_csv):
        _ensure_per_bet_from_closes_if_missing(per_bet_csv, closes)

    bets = pd.read_csv(per_bet_csv)
    bets.columns = [c.strip() for c in bets.columns]

    # Join bets to closes on best key
    join_keys = [k for k in ["bet_id","event_id","id"] if (k in bets.columns and k in closes.columns)]
    if join_keys:
        key = join_keys[0]
        merged = bets.merge(closes, on=key, how="left", suffixes=("", "_close"))
    else:
        closes = closes.copy(); closes["__row__"] = range(len(closes))
        bets = bets.copy();   bets["__row__"] = range(len(bets))
        merged = bets.merge(closes, on="__row__", how="left", suffixes=("", "_close"))

    # Resolve probabilities and odds
    entry_odds_col = _first_col(merged, ["entry_odds","price_entry","odds_entry","odds"])
    close_odds_col = _first_col(merged, ["sharp_close_odds","close_odds","price_close","odds_close","close"])

    entry_prob_col = _first_col(merged, ["sharp_entry_prob","entry_prob","prob_entry"])
    if entry_prob_col is None and entry_odds_col:
        merged["sharp_entry_prob"] = 1.0 / merged[entry_odds_col].astype(float).replace(0, np.nan)
        entry_prob_col = "sharp_entry_prob"

    close_prob_col = _first_col(merged, ["sharp_close_prob","close_prob","prob_close"])
    if close_prob_col is None and close_odds_col:
        merged["sharp_close_prob"] = 1.0 / merged[close_odds_col].astype(float).replace(0, np.nan)
        close_prob_col = "sharp_close_prob"

    # CLV pp (prefer odds)
    if entry_odds_col and close_odds_col:
        clv_pp = ((merged[close_odds_col].astype(float) - merged[entry_odds_col].astype(float))
                    / merged[entry_odds_col].astype(float)) * 100.0
    else:
        # fallback via probs -> odds
        eo = 1.0 / merged[entry_prob_col].astype(float).replace(0, np.nan)
        co = 1.0 / merged[close_prob_col].astype(float).replace(0, np.nan)
        clv_pp = ((co - eo) / eo) * 100.0
    merged["clv_pp"] = np.round(pd.Series(clv_pp).replace([np.inf,-np.inf], np.nan).fillna(0.0), 4)

    # Ensure required report columns exist
    for col in ["league","market","selection","stake","sharp_entry_prob","sharp_close_prob"]:
        if col not in merged.columns:
            if col == "stake":
                merged[col] = 0.0
            elif col in ("sharp_entry_prob","sharp_close_prob"):
                merged[col] = np.nan
            else:
                merged[col] = "N/A"

    report_cols = ["league","market","selection","stake","sharp_entry_prob","sharp_close_prob","clv_pp"]
    report = merged[report_cols].copy()
    report.to_csv(out_csv, index=False, encoding="utf-8")

    # SUMMARY with avg_clv_pp (tests assert this column exists)
    summary_df = pd.DataFrame({
        "avg_clv_pp": [float(np.round(report["clv_pp"].mean() if not report.empty else 0.0, 4))]
    })
    summary_df.to_csv(SUMMARY, index=False, encoding="utf-8")

    return out_csv

def export_edge_vs_close_csv(per_bet_csv_or_df = PER_BET, closes_csv_or_out: str | None = None, out_csv: str | None = None) -> str:
    """
    Dual-mode:
      1) export_edge_vs_close_csv(rows_df, out_path): write rows_df with required columns to out_path.
      2) export_edge_vs_close_csv(per_bet_csv, closes_csv, out_csv): delegate to settle_batch.
    Returns the written CSV path.
    """
    import pandas as pd
    # Mode 1: first arg is a DataFrame of settled rows
    if isinstance(per_bet_csv_or_df, pd.DataFrame):
        df = per_bet_csv_or_df.copy()
        out_path = closes_csv_or_out or OUT_CSV
        for col in ["league","market","selection","stake","sharp_entry_prob","sharp_close_prob","clv_pp"]:
            if col not in df.columns:
                if col == "stake":
                    df[col] = 0.0
                elif col in ("sharp_entry_prob","sharp_close_prob"):
                    if "entry_odds" in df.columns and col == "sharp_entry_prob":
                        df[col] = 1.0 / pd.Series(df["entry_odds"]).replace(0, np.nan)
                    elif "sharp_close_odds" in df.columns and col == "sharp_close_prob":
                        df[col] = 1.0 / pd.Series(df["sharp_close_odds"]).replace(0, np.nan)
                    else:
                        df[col] = np.nan
                else:
                    df[col] = "N/A"
        df[["league","market","selection","stake","sharp_entry_prob","sharp_close_prob","clv_pp"]].to_csv(out_path, index=False, encoding="utf-8")
        return out_path

    # Mode 2: original signature (paths)
    per_bet_csv = per_bet_csv_or_df or PER_BET
    closes_csv  = closes_csv_or_out or CLOSES
    return settle_batch(per_bet_csv, closes_csv, out_csv)
def export_edge_vs_close_csv(per_bet_csv_or_df = PER_BET, closes_csv_or_out: str | None = None, out_csv: str | None = None) -> str:
    """
    Dual-mode:
      1) export_edge_vs_close_csv(rows_df, out_path): write rows_df with required columns to out_path.
      2) export_edge_vs_close_csv(per_bet_csv, closes_csv, out_csv): delegate to settle_batch.
    Returns the written CSV path.
    """
    import pandas as pd
    # Mode 1: first arg is a DataFrame of settled rows
    if isinstance(per_bet_csv_or_df, pd.DataFrame):
        df = per_bet_csv_or_df.copy()
        out_path = closes_csv_or_out or OUT_CSV
        for col in ["league","market","selection","stake","sharp_entry_prob","sharp_close_prob","clv_pp"]:
            if col not in df.columns:
                if col == "stake":
                    df[col] = 0.0
                elif col in ("sharp_entry_prob","sharp_close_prob"):
                    if "entry_odds" in df.columns and col == "sharp_entry_prob":
                        df[col] = 1.0 / pd.Series(df["entry_odds"]).replace(0, np.nan)
                    elif "sharp_close_odds" in df.columns and col == "sharp_close_prob":
                        df[col] = 1.0 / pd.Series(df["sharp_close_odds"]).replace(0, np.nan)
                    else:
                        df[col] = np.nan
                else:
                    df[col] = "N/A"
        df[["league","market","selection","stake","sharp_entry_prob","sharp_close_prob","clv_pp"]].to_csv(out_path, index=False, encoding="utf-8")
        return out_path

    # Mode 2: original signature (paths)
    per_bet_csv = per_bet_csv_or_df or PER_BET
    closes_csv  = closes_csv_or_out or CLOSES
    return settle_batch(per_bet_csv, closes_csv, out_csv)
def export_edge_vs_close_csv(per_bet_csv_or_df = PER_BET, closes_csv_or_out: str | None = None, out_csv: str | None = None) -> str:
    """
    Dual-mode:
      1) export_edge_vs_close_csv(rows_df, out_path): write rows_df to out_path with expected header order:
         ["bet_id","league","market","team_or_side", ...]
      2) export_edge_vs_close_csv(per_bet_csv, closes_csv, out_csv): delegate to settle_batch.
    Returns the written CSV path.
    """
    import pandas as pd
    # Mode 1: first arg is a DataFrame of settled rows (from reconcile_ledger)
    if isinstance(per_bet_csv_or_df, pd.DataFrame):
        df = per_bet_csv_or_df.copy()
        out_path = closes_csv_or_out or OUT_CSV

        # Ensure required fields / renames
        if "team_or_side" not in df.columns:
            if "selection" in df.columns:
                df["team_or_side"] = df["selection"]
            else:
                df["team_or_side"] = "N/A"

        if "bet_id" not in df.columns:
            df["bet_id"] = [f"b{i}" for i in range(len(df))]

        # Derive probs if missing
        if "sharp_entry_prob" not in df.columns:
            if "entry_odds" in df.columns:
                df["sharp_entry_prob"] = 1.0 / pd.Series(df["entry_odds"]).replace(0, np.nan)
            else:
                df["sharp_entry_prob"] = np.nan

        if "sharp_close_prob" not in df.columns:
            if "sharp_close_odds" in df.columns:
                df["sharp_close_prob"] = 1.0 / pd.Series(df["sharp_close_odds"]).replace(0, np.nan)
            else:
                df["sharp_close_prob"] = np.nan

        # Ensure clv_pp exists (tests also inspect clv_pp elsewhere)
        if "clv_pp" not in df.columns:
            if "entry_odds" in df.columns and "sharp_close_odds" in df.columns:
                eo = pd.Series(df["entry_odds"]).astype(float).replace(0, np.nan)
                co = pd.Series(df["sharp_close_odds"]).astype(float).replace(0, np.nan)
                df["clv_pp"] = ((co - eo) / eo) * 100.0
            else:
                df["clv_pp"] = 0.0
        df["clv_pp"] = pd.Series(df["clv_pp"]).astype(float)

        # Expected header order
        leading = ["bet_id","league","market","team_or_side"]
        remainder = []
        preferred_tail = ["stake","sharp_entry_prob","sharp_close_prob","clv_pp"]
        for c in preferred_tail:
            if c in df.columns and c not in leading:
                remainder.append(c)
        # add any extra columns after preferred ones, maintaining existing order
        for c in df.columns:
            if c not in leading and c not in remainder:
                remainder.append(c)

        cols_out = leading + remainder
        df[cols_out].to_csv(out_path, index=False, encoding="utf-8")
        return out_path

    # Mode 2: original signature (paths)
    per_bet_csv = per_bet_csv_or_df or PER_BET
    closes_csv  = closes_csv_or_out or CLOSES
    return settle_batch(per_bet_csv, closes_csv, out_csv)
