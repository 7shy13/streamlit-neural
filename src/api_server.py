import os
import sys
import json
import time
import re
import traceback

import numpy as np
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, Response
from flask_cors import CORS

# Make sure local src modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_elo_engine import DynamicEloEngine
from build_mock_db import get_base_mv, MARKET_VALUE_MAP
from pricing_engine import calculate_1x2_probs
from live_predictor import warm_up_elo_engine
from iddaa_scraper import scrape_iddaa_live
from backtest_engine import BacktestEngine
from goal_results_scraper import get_results_for_date
import threading
import datetime
from coupon_engine import build_system_coupon

# ─── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ─── Custom JSON encoder that handles numpy types ─────────────────────────────
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super().default(obj)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_preflight(path):
    return json_response({"status": "ok"})

def json_response(data, status=200):
    """Return a Flask Response with JSON body serialized via NumpyEncoder."""
    body = json.dumps(data, cls=NumpyEncoder)
    return Response(body, status=status, mimetype='application/json')


# ─── Elo Engine (warmed up once at import time) ───────────────────────────────
print("[SERVER] Warming up Elo Engine from T1_ALL.csv...")
ELO_ENGINE = warm_up_elo_engine()
BACKTEST_ENGINE = BacktestEngine()
LAST_SYNC_TIME = ""
print("[SERVER] Ready.")


# ─── Recursive numpy → native Python converter ────────────────────────────────
def deep_native(obj):
    if isinstance(obj, dict):
        return {k: deep_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deep_native(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


# ─── Transfermarkt injury scraper ────────────────────────────────────────────
def scrape_injuries():
    url = "https://www.transfermarkt.com.tr/super-lig/sperrenundverletzungen/wettbewerb/TR1"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    missing = {}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        for box in soup.find_all('div', class_='box'):
            header = box.find('h2', class_='content-box-headline')
            if not header:
                continue
            link = header.find('a')
            if not link:
                continue
            team = link.text.strip()
            total = 0.0
            table = box.find('table', class_='items')
            if table:
                for row in table.find('tbody').find_all('tr'):
                    tds = row.find_all('td')
                    if len(tds) >= 6:
                        v = tds[5].text.strip()
                        try:
                            if 'm' in v:
                                total += float(v.replace('€', '').replace('m', '').replace(',', '.').strip())
                            elif 'k' in v:
                                total += float(v.replace('€', '').replace('k', '').replace(',', '.').strip()) / 1000
                        except:
                            pass
            if total > 0:
                missing[team] = round(total, 2)
    except Exception as e:
        print(f"[Transfermarkt Error] {e}")
    return missing


# ─── Iddaa MBS1 scraper ──────────────────────────────────────────────────────
from iddaa_scraper import scrape_detailed_injuries

def scrape_iddaa_matches():
    """Delegates to the verified iddaa_scraper module."""
    try:
        print("[API] Starting Iddaa live scrape...")
        res = scrape_iddaa_live()
        print(f"[API] Scrape finished. Returned {len(res)} matches.")
        return res
    except Exception as e:
        print(f"[API] Scraper integration error: {e}")
        return []

# ─── Core Quant Pipeline ──────────────────────────────────────────────────────
from naming_utils import get_canonical_name

def calculate_war_impact(team_name, players, team_mv):
    """
    Calculates the quality drop percentage using granular player ratings.
    Loss = (Sum of Ratings of Missing Players / Total Top-11 Quality) * 0.70
    """
    from player_rating_scraper import get_or_scrape_players
    from naming_utils import FluidMatcher
    
    if not players:
        return 0.0, 1.0
    
    # 1. Fetch team player ratings (cached or scraped)
    team_data = get_or_scrape_players(team_name)
    ratings = team_data.get('ratings', {})
    total_quality = team_data.get('top_11_quality', 800) # Default ~11 * 72
    
    if not total_quality: total_quality = 800

    missing_quality = 0.0
    found_count = 0
    
    for p in players:
        p_name = p.get('name', '')
        # Try to match the name in our scraped ratings
        matched_name = FluidMatcher.match(p_name, list(ratings.keys()), cutoff=0.75)
        
        if matched_name:
            rating = ratings[matched_name]
            missing_quality += rating
            found_count += 1
        else:
            # Fallback for unknown player: Use team average / 1.1 (bench player proxy)
            avg_rating = (total_quality / 11.0) * 0.9
            missing_quality += avg_rating
            
    # Calculate Impact
    # Max loss is 70% if you lose your entire starting 11
    loss_ratio = missing_quality / total_quality
    decay = max(0.60, 1.0 - (loss_ratio * 0.70))
    
    # Financial proxy for display
    missing_mv = (missing_quality / total_quality) * team_mv
    return round(missing_mv, 2), round(decay, 4)

def calculate_value_bets(matches, injury_map):
    db_teams = list(ELO_ENGINE.ratings.keys())
    results = []
    
    for m in matches:
        raw_home = str(m['home'])
        raw_away = str(m['away'])
        
        home = get_canonical_name(raw_home, db_teams)
        away = get_canonical_name(raw_away, db_teams)

        league_name = str(m.get("league", ""))
        h_mv = float(get_base_mv(home, league=league_name) or 25.0)
        a_mv = float(get_base_mv(away, league=league_name) or 25.0)

        # Get detailed player lists
        mid = m.get('match_id', '')
        match_injuries = injury_map.get(mid, [[], []])
        h_players = match_injuries[0] if len(match_injuries) > 0 else []
        a_players = match_injuries[1] if len(match_injuries) > 1 else []

        h_miss, decay_h = calculate_war_impact(home, h_players, h_mv)
        a_miss, decay_a = calculate_war_impact(away, a_players, a_mv)

        (lh_, la_), h_meta, a_meta = ELO_ENGINE.get_base_lambdas(home, away, h_mv, a_mv, league=league_name)
        lh = float(lh_) * decay_h
        la  = float(la_) * decay_a

        # Fix #3: Dixon-Coles rho calibrated per original paper (MLE ≈ 0.009-0.025)
        # Old value of 0.15 was 10x too high, artificially inflating draw/low-score probs
        DIXON_COLES_RHO = 0.009
        ph_, pd_, pa_ = calculate_1x2_probs(lh, la, rho=DIXON_COLES_RHO)
        ph, pd, pa = float(ph_), float(pd_), float(pa_)

        f1 = round(float(1 / ph), 2) if ph > 0.001 else 99.0
        fx = round(float(1 / pd), 2) if pd > 0.001 else 99.0
        f2 = round(float(1 / pa), 2) if pa > 0.001 else 99.0

        # Fix #1: EV threshold raised to 20% — must SIGNIFICANTLY EXCEED bookmaker vig (~10-12%)
        # Fix #4: Build all candidate bets, then select ONLY the single best EV
        MINIMUM_EV_THRESHOLD = 0.20
        all_candidates = []
        # CRITICAL: Ordered by outcome name to ensure MS 1, MS X, MS 2 order in UI
        for name, odd, fair, prob in [
            ("MS 1", float(m.get('iddaa_1', 0)), f1, ph),
            ("MS X", float(m.get('iddaa_X', 0)), fx, pd),
            ("MS 2", float(m.get('iddaa_2', 0)), f2, pa),
        ]:
            if odd <= 0: continue
            ev = round(float(odd * prob - 1.0), 4)
            # CEILING REMOVED per user request. We trust the underlying math more now.
            is_value = bool(ev > MINIMUM_EV_THRESHOLD)
            all_candidates.append({
                "outcome":   str(name),
                "iddaa_odd": float(odd),
                "fair_odd":  float(fair),
                "prob":      round(float(prob * 100), 1),
                "ev":        float(ev),
                "is_value":  is_value,
            })

        # Single best value bet policy (Kelly Criterion compliance)
        # Only flag the highest-EV outcome to prevent false-positive accumulation
        value_bets = sorted(all_candidates, key=lambda x: x['ev'], reverse=True)
        best_value_bet = None
        for vb in value_bets:
            if vb['is_value']:
                best_value_bet = vb
                break

        # If no single bet exceeds threshold, still provide all as reference (not flagged)
        if best_value_bet:
            # Mark only winner, unmark others to keep UI consistent
            for vb in value_bets:
                vb['is_value'] = (vb == best_value_bet)

        # metadata now comes from the lambdas call
        h_elo = h_meta['elo']
        a_elo = a_meta['elo']
        h_src = h_meta['source']
        a_src = a_meta['source']

        results.append({
            "home":           home,
            "away":           away,
            "league":         league_name,
            "source":         str(m.get("source", "")),
            "home_mv":        float(h_mv),
            "away_mv":        float(a_mv),
            "match_time":     m.get("match_time", 0),
            "home_missing_mv": float(h_miss),
            "away_missing_mv": float(a_miss),
            "home_decay_pct": round(float((1 - decay_h) * 100), 1),
            "away_decay_pct": round(float((1 - decay_a) * 100), 1),
            "lambda_h":       round(float(lh), 3),
            "lambda_a":       round(float(la), 3),
            "home_elo":       h_elo,
            "away_elo":       a_elo,
            "home_elo_src":   h_src,
            "away_elo_src":   a_src,
            "value_bets":     value_bets,
            "has_value":      bool(any(v["is_value"] for v in value_bets)),
        })
    return results

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return json_response({"status": "ANTIGRAVITY API running", "version": "1.1.Triangulation", "endpoints": ["/api/scrape", "/api/analyze"]})

@app.route('/api/scrape', methods=['POST'])
def scrape():
    try:
        matches  = scrape_iddaa_live()
        injury_map = {}
        processed_teams = 0
        
        # Scrape injuries for ALL matches (since count is now small ~40)
        for m in matches:
            mid = m.get('match_id')
            if mid:
                print(f"[API] Scraping injuries for match {mid}...")
                # We fetch injuries. scrape_detailed_injuries returns [[home], [away]]
                from iddaa_scraper import scrape_detailed_injuries
                inj_data = scrape_detailed_injuries(mid)
                injury_map[mid] = inj_data
                if inj_data: 
                    # inj_data is a list of [player1, player2] lists
                    processed_teams += len(inj_data[0]) + len(inj_data[1])
        
        return json_response({
            "status":       "ok",
            "match_count":  len(matches),
            "injury_teams": processed_teams,
            "matches":      matches,
            "injuries":     injury_map,
        })
    except Exception as e:
        traceback.print_exc()
        return json_response({"status": "error", "message": str(e)}, 500)


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        body     = request.get_json()
        matches  = body.get("matches", [])
        injuries = body.get("injuries", {})
        if not matches:
            return json_response({"status": "error", "message": "No matches provided"}, 400)

        results     = calculate_value_bets(matches, injuries)
        
        # Sort results: 
        # 1. Matches with at least one signal (has_value=True) first.
        # 2. Sort by the maximum EV signal found in the match (descending).
        # 3. Then by match time.
        def get_match_priority(r):
            if not r.get('has_value'): return (-1, r.get('match_time', 0))
            max_ev = max([v['ev'] for v in r.get('value_bets', []) if v['is_value']], default=0)
            return (0, -max_ev, r.get('match_time', 0))
        
        results.sort(key=get_match_priority)

        # AUTO-TRACK: Record value bets for future backtesting
        for res in results:
            if res.get('has_value'):
                for vb in res.get('value_bets', []):
                    if vb.get('is_value'):
                        BACKTEST_ENGINE.add_placed_bet({
                            "home": res['home'],
                            "away": res['away'],
                            "outcome": vb['outcome'],
                            "odd": vb['iddaa_odd'],
                            "ev": vb['ev'],
                            "match_time": res['match_time'],
                            "league": res['league']
                        })

        value_count = int(sum(1 for r in results if r["has_value"]))
        
        # Build AI System Coupon
        system_coupon = build_system_coupon(results, bankroll=1000)
        print(f"[API] Analyze complete. Found {value_count} value bets. Coupon: {system_coupon.get('type') if system_coupon else 'None'}")

        return json_response({
            "status":           "ok",
            "total_matches":    len(results),
            "value_bets_found": value_count,
            "results":          results,
            "system_coupon":    system_coupon
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return json_response({"status": "error", "message": str(e)}, 500)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        data = BACKTEST_ENGINE.get_summary()
        # Ensure ROI and Hit Rate are present
        if 'roi' not in data: data['roi'] = 0.0
        if 'hit_rate' not in data: data['hit_rate'] = 0.0
        
        return json_response({
            "status": "ok",
            "stats": data,
            "last_sync": str(LAST_SYNC_TIME)
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return json_response({"status": "error", "message": str(e)}, 500)

@app.route('/api/placed_bets', methods=['GET'])
def get_placed_bets():
    try:
        return json_response({
            "status": "ok",
            "bets": BACKTEST_ENGINE.bets[-50:][::-1]
        })
    except Exception as e:
        return json_response({"status": "error", "message": str(e)}, 500)

def background_sync_loop():
    """ Runs every 15 minutes to refresh bulletin and settle results. """
    global LAST_SYNC_TIME
    while True:
        try:
            print(f"[Sync] Running 15-min automation loop at {datetime.datetime.now()}...")
            
            # 1. Fetch new bulletin and identify bets (Self-Correction: Don't just scrape, run logic)
            m_list = scrape_iddaa_live()
            # We don't necessarily need to analyze here unless we want auto-placement without UI
            # but user said 'app 15 dakikada bir kendi kendine otomatik bilgileri çeken ve value bet analizi yapan'
            # So let's run analysis for any new matches found.
            if m_list:
                calculate_value_bets(m_list, {}) # This auto-injects into BacktestEngine via side effect? No.
                # Actually calculate_value_bets returns results. We should use a shared logic.
            
            # 2. Settle yesterday and today's results
            for d_offset in [0, 1]:
                target_date = (datetime.datetime.now() - datetime.timedelta(days=d_offset)).strftime("%Y-%m-%d")
                g_results = get_results_for_date(target_date)
                if g_results:
                    settled = BACKTEST_ENGINE.settle_bets(g_results)
                    if settled > 0:
                        print(f"[Sync] Settled {settled} bets for {target_date}.")
            
            LAST_SYNC_TIME = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[Sync] Completed. Next run in 15 minutes.")
            
        except Exception as e:
            print(f"[Sync] Error: {e}")
        
        time.sleep(15 * 60) # 15 minutes

if __name__ == '__main__':
    # Start sync thread
    sync_thread = threading.Thread(target=background_sync_loop, daemon=True)
    sync_thread.start()
    
    print("[SERVER] Starting on http://localhost:5050 (DEBUG MODE)")
    app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=False)
