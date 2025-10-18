# Sharp Composite — Weighting & Cadence

**Books:** Pinnacle (0.5), SBO (0.3), ISN (0.2)  
**Cadence:** 30s refresh (configurable in `config.yml`)  
**Fallback:** If a source is missing, remaining weights renormalize to 1.0.

## Formula
Composite fair odds:
\[
\text{Composite} = \frac{1}{\sum_i \frac{w_i}{o_i}}
\]
Implied probability = \( 1 / \text{Composite} \)

## Normalization
- Vig removed per book (fair conversion)
- Composite rounded to market-consistent precision

## Guardrail
- Any bet with < **1 percentage point** edge vs composite is rejected.

## API
`GET /composite?league=NBA&market=ML&base_odds=1.95`  
Returns: `composite_fair`, `sources[]`, `ts`.

## Files
- Code: `src/services/odds_composite.py`, `src/adapters/*.py`
- Admin UI calls API service name (`api`) inside Docker
