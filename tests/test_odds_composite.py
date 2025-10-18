from __future__ import annotations
from src.services.odds_composite import OddsComposite

def test_composite_weights_and_normalization(monkeypatch):
    # mock adapters to fixed values
    def f_p(mkt, rid): return {"book":"pinnacle","price":2.00,"ts":mkt.get("ts")}
    def f_s(mkt, rid): return {"book":"sbo","price":1.90,"ts":mkt.get("ts")}
    def f_i(mkt, rid): return {"book":"isn","price":2.10,"ts":mkt.get("ts")}

    import src.adapters.pinnacle as ap
    import src.adapters.sbo as asb
    import src.adapters.isn as ai

    monkeypatch.setattr(ap, "fetch_odds", f_p)
    monkeypatch.setattr(asb, "fetch_odds", f_s)
    monkeypatch.setattr(ai, "fetch_odds", f_i)

    cfg = {
        "sharp":{
            "weights":{"pinnacle":0.5,"sbo":0.3,"isn":0.2},
            "cadence_sec": 30, "stale_after_sec": 90,
            "normalization":{"scheme":"none"}
        }
    }
    oc = OddsComposite(cfg)
    market = {"league":"NBA","market":"ML","ts":None}
    out = oc.compose(market)

    # expected: 0.5*2.00 + 0.3*1.90 + 0.2*2.10 = 1.0 + 0.57 + 0.42 = 1.99
    assert round(out["composite_fair"], 2) == 1.99
    assert len(out["sources"]) == 3
