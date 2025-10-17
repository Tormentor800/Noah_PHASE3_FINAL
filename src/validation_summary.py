import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def reliability_plot(probs, outcomes, out_png):
    # calibration curve expects prob of positive class and outcomes in {0,1}
    frac_pos, mean_pred = calibration_curve(outcomes, probs, n_bins=10, strategy='quantile')
    plt.figure()
    plt.plot(mean_pred, frac_pos, marker='o')
    plt.plot([0,1],[0,1],'--')
    plt.title("Reliability / Calibration")
    plt.xlabel("Predicted probability")
    plt.ylabel("Empirical frequency")
    plt.savefig(out_png, bbox_inches="tight")
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_pdf", required=True)
    ap.add_argument("--prob_col", default="model_prob")
    ap.add_argument("--result_col", default="result")
    args = ap.parse_args()

    df = pd.read_csv(args.in_csv).dropna(subset=[args.prob_col, args.result_col])
    probs = df[args.prob_col].astype(float).clip(0,1).values
    outcomes = df[args.result_col].astype(int).values

    # Reliability plot
    rel_png = "reports/reliability.png"
    reliability_plot(probs, outcomes, rel_png)

    # Simple temporal split plot if date exists
    if "date" in df.columns:
        try:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            rolling = df[args.result_col].rolling(200, min_periods=50).mean()
            plt.figure()
            plt.plot(rolling.index, rolling.values)
            plt.title("Rolling Win Rate (window=200)")
            plt.xlabel("Index (time-ordered)")
            plt.ylabel("Win rate")
            roll_png = "reports/rolling_winrate.png"
            plt.savefig(roll_png, bbox_inches="tight")
            plt.close()
        except Exception:
            roll_png = None
    else:
        roll_png = None

    # Minimal PDF
    c = canvas.Canvas(args.out_pdf, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Model Validation Summary")
    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(40, y, "Includes calibration and rolling performance snapshots.")
    y -= 20

    # Insert images
    from reportlab.platypus import Image
    try:
        c.drawImage(rel_png, 40, y-260, width=520, height=240, preserveAspectRatio=True, anchor='sw')
        y -= 270
    except Exception:
        pass
    if roll_png:
        try:
            c.drawImage(roll_png, 40, y-260, width=520, height=240, preserveAspectRatio=True, anchor='sw')
            y -= 270
        except Exception:
            pass

    c.showPage()
    c.save()

if __name__ == "__main__":
    main()
