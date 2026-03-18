"""Quick diagnostic to find what value is not JSON serializable in calculate_value_bets."""
import sys
sys.path.insert(0, 'src')

import json
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

# Replicate what the server does at import-time
from live_predictor import warm_up_elo_engine
from build_mock_db import get_base_mv, MARKET_VALUE_MAP
from pricing_engine import calculate_1x2_probs

ELO_ENGINE = warm_up_elo_engine()

def calculate_value_bets(matches, injuries):
    results = []
    for m in matches:
        home = str(m['home'])
        away = str(m['away'])
        h_mv = float(get_base_mv(home) or 25.0)
        a_mv = float(get_base_mv(away) or 25.0)
        h_miss = float(injuries.get(home, 0.0))
        a_miss = float(injuries.get(away, 0.0))
        drop_h = float(min(1.0, h_miss / max(0.1, h_mv)))
        drop_a = float(min(1.0, a_miss / max(0.1, a_mv)))
        decay_h = float(max(0.60, 1.0 - drop_h * 0.70))
        decay_a = float(max(0.60, 1.0 - drop_a * 0.70))
        lh_, la_ = ELO_ENGINE.get_base_lambdas(home, away, h_mv, a_mv)
        lh = float(lh_) * decay_h
        la  = float(la_) * decay_a
        ph_, pd_, pa_ = calculate_1x2_probs(lh, la, rho=0.15)
        ph, pd, pa = float(ph_), float(pd_), float(pa_)
        f1 = round(float(1 / ph), 2) if ph > 0.001 else 99.0
        fx = round(float(1 / pd), 2) if pd > 0.001 else 99.0
        f2 = round(float(1 / pa), 2) if pa > 0.001 else 99.0
        value_bets = []
        for name, odd, fair, prob in [
            ("MS 1", float(m['iddaa_1']), f1, ph),
            ("MS X", float(m['iddaa_X']), fx, pd),
            ("MS 2", float(m['iddaa_2']), f2, pa),
        ]:
            if odd <= 0: continue
            ev = round(float(odd * prob - 1.0), 4)
            is_val = bool(ev > 0.05)
            value_bets.append({
                "outcome": str(name),
                "iddaa_odd": float(odd),
                "fair_odd": float(fair),
                "prob": round(float(prob * 100), 1),
                "ev": float(ev),
                "is_value": is_val,
            })
        h_elo = float(round(float(ELO_ENGINE.ratings.get(home, 1500)), 0))
        a_elo = float(round(float(ELO_ENGINE.ratings.get(away, 1500)), 0))
        has_val = bool(any(v["is_value"] for v in value_bets))
        results.append({
            "home": home, "away": away,
            "league": str(m.get("league", "")),
            "source": str(m.get("source", "")),
            "home_mv": float(h_mv), "away_mv": float(a_mv),
            "home_missing_mv": float(h_miss), "away_missing_mv": float(a_miss),
            "home_decay_pct": round(float((1 - decay_h) * 100), 1),
            "away_decay_pct": round(float((1 - decay_a) * 100), 1),
            "lambda_h": round(float(lh), 3),
            "lambda_a": round(float(la), 3),
            "home_elo": h_elo, "away_elo": a_elo,
            "value_bets": value_bets, "has_value": has_val,
        })
    return results

matches = [{'home':'Galatasaray','away':'Fenerbahce','iddaa_1':2.10,'iddaa_X':3.40,'iddaa_2':2.80,'league':'SL','source':'demo'}]
injuries = {}

results = calculate_value_bets(matches, injuries)
print("Results built. Attempting json.dumps...")
try:
    s = json.dumps({"results": results}, cls=NumpyEncoder)
    print("JSON SUCCESS:", s[:200])
except Exception as e:
    print("JSON FAIL:", e)
    for i, r in enumerate(results):
        for k, v in r.items():
            try:
                json.dumps(v, cls=NumpyEncoder)
            except Exception as fe:
                print(f"  result[{i}][{k!r}] = {v!r} ({type(v)}) -> FAIL: {fe}")
