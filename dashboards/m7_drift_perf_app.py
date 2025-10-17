import os
import pandas as pd
import streamlit as st

# ... existing code ...

st.subheader("Sharp Entry — League/Market Breakdown")
path_groups = os.path.join("artifacts", "summary_sharp_entry_vs_clv_by_group.csv")
if os.path.exists(path_groups) and os.path.getsize(path_groups) > 0:
    gdf = pd.read_csv(path_groups)
    # show as percentages for readability
    gdf["pct_passing_gate"] = (gdf["pct_passing_gate"] * 100).round(1)
    gdf["pct_clv_gt_0"] = (gdf["pct_clv_gt_0"] * 100).round(1)
    gdf["avg_clv_pp"] = gdf["avg_clv_pp"].round(3)
    st.dataframe(gdf.sort_values(["league", "market"]).reset_index(drop=True), width="stretch")
else:
    st.info("No grouped summary yet – run: `py -m src.flows.sharp_eval_demo`.")
