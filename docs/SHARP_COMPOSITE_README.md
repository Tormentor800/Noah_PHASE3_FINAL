# Sharp Composite (Prematch, via AsianConnect)

**Scope:** Pinnacle, SBO, ISN only (BIA excluded). Purpose is to benchmark entry vs. sharp prices and compute CLV vs sharp close.

## Sources & Access
- **Broker:** AsianConnect
- **Books:** Pinnacle, SBO, ISN
- **Markets:** 1X2, AH/Spread, Totals (OU). Prematch only.

## Normalization
- Convert book odds to **implied probabilities** (American/Decimal → prob).
- Map market sides to a consistent “home/over” orientation so the same side is compared across books.
- Remove obviously stale/erroneous points (e.g., implied p ∉ (0.01, 0.99)).

## Weighting (default)
- Pinnacle: **0.50**
- SBO: **0.30**
- ISN: **0.20**

Composite probability:
p_comp = 0.50·p_pinn + 0.30·p_sbo + 0.20·p_isn

If any feed is missing at a tick:
- **2-book fallback:** Renormalize weights (e.g., 0.625 / 0.375).
- **1-book fallback:** Use the single book (flag `sharp_books_used=1`).
- **0-book:** skip tick.

## Sampling Cadence
- Pull quotes every **30 seconds** (configurable).
- Snapshot *at entry* (pre-bet) → `sharp_entry_prob`.
- For CLV, snapshot *sharp close* close to kickoff (last available tick within cutoff window).

## Gate Rule (Hard)
- **Edge vs Sharp @ entry**: `fair_prob − sharp_entry_prob ≥ 0.01` (≥ 1 pp)
- Bets failing the gate **must not** be executed/logged.

## Outputs
- **Per bet:** `artifacts/per_bet_execution_sharp.csv`
  - `entry_ts, league, market, sharp_books_used, sharp_entry_prob, fair_prob, edge_vs_sharp_entry, exec_book, exec_odds, result`
- **Summary:** `artifacts/summary_sharp_entry_vs_clv.csv`
  - Overall + league/market breakdown: `% passing ≥1%`, `% CLV>0`, `avg CLV (pp)`, slippage & latency stats.

## Known Limitations
- Demo mode uses synthetic frames if live broker feeds are unavailable.
- Market alignment heuristics can be tuned per sport/league.
