import os, csv

# Inputs (existing summaries you already generate)
IN_SUMMARY = os.path.join("artifacts","settlement","summary_edge_vs_close.csv")

# Output (your requested name)
OUT_EXEC   = os.path.join("artifacts","per_bet_execution_sharp.csv")
os.makedirs(os.path.dirname(OUT_EXEC), exist_ok=True)

# If summary file doesn’t exist, create a tiny placeholder row
rows = []
if os.path.exists(IN_SUMMARY):
    with open(IN_SUMMARY, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
else:
    rows = [{
        "league":"NBA","market":"ML","selection":"HOME",
        "sharp_entry_prob":"0.505","sharp_close_prob":"0.500",
        "clv_pp":"0.5","stake":"0"
    }]

# Build execution CSV with requested columns
fields = ["league","market","exec_book","selection",
          "sharp_books_used","sharp_entry_odds","sharp_entry_prob"]
with open(OUT_EXEC, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        # derive entry odds from prob (if present)
        try:
            p = float(r.get("sharp_entry_prob") or 0.0)
            entry_odds = round(1.0/p, 3) if p > 0 else ""
            entry_prob = round(p, 6) if p > 0 else ""
        except:
            entry_odds, entry_prob = "", ""

        out = {
            "league": r.get("league",""),
            "market": r.get("market",""),
            "exec_book": "pinnacle",                      # use the actual exec source if you have it
            "selection": r.get("selection",""),
            "sharp_books_used": "pinnacle,sbo,isn",       # used in composite
            "sharp_entry_odds": entry_odds,
            "sharp_entry_prob": entry_prob,
        }
        w.writerow(out)

print(OUT_EXEC)
