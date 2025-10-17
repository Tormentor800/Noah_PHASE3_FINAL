import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def kelly_fraction(edge, odds):
    # Kelly for decimal odds: f* = (p*(b+1)-1)/b where b=odds-1 and p=implied true prob
    # Here we approximate p via model: p = 1/(odds) * (1+edge)  -> so edge = p/ (1/odds) -1
    # Safer practical formula: f = edge / (odds - 1), clipped to [0,1]
    b = np.maximum(odds - 1.0, 1e-9)
    f = edge / b
    return np.clip(f, 0.0, 1.0)

def simulate(df, scheme="flat", unit=1.0, kelly_cap=0.02):
    bankroll = [100.0]
    stakes = []
    rets = []
    for _, r in df.iterrows():
        odds = float(r.get("decimal_odds", np.nan))
        edge = float(r.get("edge", 0.0))
        res = int(r.get("result", 0))  # 1=win,0=loss

        if scheme == "flat":
            stake = unit
        elif scheme == "kelly":
            stake = bankroll[-1] * kelly_fraction(edge, odds)
        elif scheme == "liq":
            stake = bankroll[-1] * min(kelly_fraction(edge, odds), kelly_cap)
        else:
            stake = unit

        # outcome
        pnl = stake * (odds - 1.0) if res == 1 else -stake
        bankroll.append(bankroll[-1] + pnl)
        stakes.append(stake)
        rets.append(pnl)

    out = pd.DataFrame({
        "bankroll": bankroll[1:],
        "stake": stakes,
        "pnl": rets
    })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_png", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--kelly_cap", type=float, default=0.02)
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv).dropna(subset=["decimal_odds", "result"])

    runs = {}
    for scheme in ["flat", "kelly", "liq"]:
        runs[scheme] = simulate(df, scheme=scheme, unit=1.0, kelly_cap=args.kelly_cap)

    # Plot bankroll trajectories
    plt.figure()
    for scheme, sim in runs.items():
        plt.plot(sim["bankroll"], label=scheme)
    plt.title("Bankroll Trajectory by Staking Scheme")
    plt.legend()
    plt.xlabel("Bets")
    plt.ylabel("Bankroll")
    plt.savefig(args.out_png, bbox_inches="tight")
    plt.close()

    # Summary metrics
    summary = []
    for scheme, sim in runs.items():
        roi = sim["pnl"].sum() / len(sim) if len(sim) else 0.0
        dd = (sim["bankroll"].cummax() - sim["bankroll"]).max() if len(sim) else 0.0
        vol = sim["pnl"].std() if len(sim) else 0.0
        summary.append({"scheme": scheme, "roi_per_bet": roi, "max_drawdown": dd, "volatility": vol})

    pd.DataFrame(summary).to_csv(args.out_csv, index=False)

if __name__ == "__main__":
    main()
