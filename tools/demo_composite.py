from src.services.odds_composite import OddsComposite
oc = OddsComposite()
print(oc.compose({"league":"NBA","market":"ML","base_odds":1.95,"ts":None}))
