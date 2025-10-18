import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.services.odds_composite import OddsComposite

oc = OddsComposite()
print(oc.compose({"league":"NBA","market":"ML","base_odds":1.95,"ts":None}))
