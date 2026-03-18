import sqlite3
import pandas as pd
import numpy as np
import datetime
import os
import math
import json

# MAP OF RELATIVE FINANCIAL TIERS (M Euros) - Fallback Priors
LEAGUE_FINANCIAL_PRIORS = {
    "Premier League": 450.0,
    "La Liga": 320.0,
    "Bundesliga": 280.0,
    "Serie A": 260.0,
    "Ligue 1": 220.0,
    "Trendyol Süper Lig": 35.0,
    "Championship": 120.0,
    "Eredivisie": 80.0,
    "Liga Portugal": 90.0
}

MARKET_VALUE_MAP = {
    "Galatasaray": 210.0,
    "Fenerbahce": 200.0,
    "Besiktas": 140.0,
    "Trabzonspor": 100.0,
    "Basaksehir": 55.0,
    "Buyuksehyr": 55.0,
    "Adana Demir": 45.0,
    "Konyaspor": 40.0,
}

# 1. Global Cache Loader
LIVE_MV_CACHE = {}
MV_RESOLVED_CACHE = {} # Perf Fix: Cache resolved names to avoid fuzzy matching 12,000 times

try:
    cache_path = os.path.join(os.path.dirname(__file__), 'live_market_values.json')
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            LIVE_MV_CACHE = json.load(f)
        print(f"[MarketValue] Loaded {len(LIVE_MV_CACHE)} live values from Transfermarkt cache.")
except Exception as e:
    print(f"[MarketValue] Cache load error: {e}")

def get_base_mv(team_name, league=None):
    """
    Returns the squad value in M Euros.
    Priority: 1. Live Scraped Cache, 2. Manual Map, 3. League Prior, 4. Global Min.
    """
    # Perf Fix: Instant return if already resolved
    if team_name in MV_RESOLVED_CACHE:
        return MV_RESOLVED_CACHE[team_name]

    from naming_utils import FluidMatcher, normalize_turkish
    
    val = 15.0 # default
    
    # 1. Check Live Scraped Cache (Fluid Match)
    if LIVE_MV_CACHE:
        match = FluidMatcher.match(team_name, list(LIVE_MV_CACHE.keys()), cutoff=0.75)
        if match:
            val = float(LIVE_MV_CACHE[match])
            MV_RESOLVED_CACHE[team_name] = val
            return val
            
    # 2. Check Static Manual Map
    if team_name in MARKET_VALUE_MAP:
        val = MARKET_VALUE_MAP[team_name]
        MV_RESOLVED_CACHE[team_name] = val
        return val
    
    # ... rest of the logic
    
    # 3. Check League Prior (Flexible Matching)
    if league:
        norm_l = normalize_turkish(league).lower()
        for k, v in LEAGUE_FINANCIAL_PRIORS.items():
            if normalize_turkish(k).lower() in norm_l or norm_l in normalize_turkish(k).lower():
                return v
            
    # 4. Global Minimal Fallback
    return 15.0

def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, format="%d/%m/%Y")
    except:
        return pd.to_datetime(date_str)

def build_mock_context_database():
    """
    Reads T1_ALL.csv and generates a DETERMINISTIC historical SQL database (`context_data.db`).
    """
    db_path = "context_data.db"
    
    # Remove old DB if exists
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print("Loading T1_ALL.csv to extract deterministic context mapping...")
    try:
        # Resolve path relative to this file
        csv_path = os.path.join(os.path.dirname(__file__), 'T1_ALL.csv')
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("Error: T1_ALL.csv not found.")
        return

    df['Date'] = df['Date'].apply(parse_date)
    df = df.sort_values('Date').reset_index(drop=True)

    df['Days_Since_Last_Match'] = df['Date'].diff().dt.days
    df['Season_Id'] = (df['Days_Since_Last_Match'] > 45).cumsum()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE player_impact (match_id TEXT, team_id TEXT, missing_player_id TEXT, xt_loss_90 REAL)')
    cursor.execute('CREATE TABLE fixture_fatigue (match_id TEXT, team_id TEXT, rest_days REAL, travel_km REAL)')
    cursor.execute('CREATE TABLE market_value (team_id TEXT, date TEXT, total_value_eur_m REAL)')
    cursor.execute('CREATE TABLE motivation_context (match_id TEXT, team_id TEXT, points_to_title REAL, points_to_relegation REAL, z_score REAL)')

    impact_records = []
    fatigue_records = []
    mv_records = []
    motivation_records = []
    
    last_match_dates = {}
    standings = {}

    for idx, row in df.iterrows():
        match_id = str(idx)
        match_date = row['Date']
        home_team = row['HomeTeam']
        away_team = row['AwayTeam']
        season_id = row['Season_Id']
        
        if season_id not in standings: standings[season_id] = {}
        if home_team not in standings[season_id]: standings[season_id][home_team] = {"Points": 0, "MatchesPlayed": 0}
        if away_team not in standings[season_id]: standings[season_id][away_team] = {"Points": 0, "MatchesPlayed": 0}

        if home_team in last_match_dates: home_rest = (match_date - last_match_dates[home_team]).days
        else: home_rest = 7.0
            
        if away_team in last_match_dates: away_rest = (match_date - last_match_dates[away_team]).days
        else: away_rest = 7.0
            
        last_match_dates[home_team] = match_date
        last_match_dates[away_team] = match_date
        
        home_rest = min(10.0, float(home_rest))
        away_rest = min(10.0, float(away_rest))
        
        fatigue_records.append((match_id, home_team, home_rest, 0.0))
        fatigue_records.append((match_id, away_team, away_rest, 500.0))
        
        home_mv = get_base_mv(home_team)
        away_mv = get_base_mv(away_team)
        mv_records.append((home_team, match_date.strftime("%Y-%m-%d"), home_mv))
        mv_records.append((away_team, match_date.strftime("%Y-%m-%d"), away_mv))
        
        impact_records.append((match_id, home_team, "NONE", 0.0))
        impact_records.append((match_id, away_team, "NONE", 0.0))

        pts_h = standings[season_id][home_team]["Points"]
        pts_a = standings[season_id][away_team]["Points"]
        mp_h = standings[season_id][home_team]["MatchesPlayed"]
        mp_a = standings[season_id][away_team]["MatchesPlayed"]
        
        all_pts = [v["Points"] for k, v in standings[season_id].items() if v["MatchesPlayed"] > 0]
        
        h_zscore, a_zscore = 0.0, 0.0
        h_to_title, h_to_rel = 0, 0
        a_to_title, a_to_rel = 0, 0
        
        if len(all_pts) > 0 and (mp_h > 10 and mp_a > 10):
            all_pts.sort(reverse=True)
            leader_pts = max(all_pts)
            rel_idx = min(len(all_pts) - 1, len(all_pts) - 4)
            relegation_pts = all_pts[rel_idx] if rel_idx > 0 else 0
            
            h_to_title = max(0, leader_pts - pts_h)
            a_to_title = max(0, leader_pts - pts_a)
            h_to_rel = max(0, pts_h - relegation_pts)
            a_to_rel = max(0, pts_a - relegation_pts)
            
            def calc_motiv_score(to_title, to_rel):
                score = 0.0
                if to_title <= 6: score += (6 - to_title) * 0.4
                if to_rel <= 6: score += (6 - to_rel) * 0.4
                if to_title > 15 and to_rel > 15: score -= 1.0
                return score
                
            h_zscore = calc_motiv_score(h_to_title, h_to_rel)
            a_zscore = calc_motiv_score(a_to_title, a_to_rel)
            
        motivation_records.append((match_id, home_team, h_to_title, h_to_rel, h_zscore))
        motivation_records.append((match_id, away_team, a_to_title, a_to_rel, a_zscore))
        
        fthg, ftag = row['FTHG'], row['FTAG']
        standings[season_id][home_team]["MatchesPlayed"] += 1
        standings[season_id][away_team]["MatchesPlayed"] += 1
        
        if fthg > ftag: standings[season_id][home_team]["Points"] += 3
        elif fthg == ftag:
            standings[season_id][home_team]["Points"] += 1
            standings[season_id][away_team]["Points"] += 1
        else: standings[season_id][away_team]["Points"] += 3

    cursor.executemany("INSERT INTO player_impact VALUES (?, ?, ?, ?)", impact_records)
    cursor.executemany("INSERT INTO fixture_fatigue VALUES (?, ?, ?, ?)", fatigue_records)
    cursor.executemany("INSERT INTO market_value VALUES (?, ?, ?)", mv_records)
    cursor.executemany("INSERT INTO motivation_context VALUES (?, ?, ?, ?, ?)", motivation_records)
    
    cursor.execute("CREATE INDEX idx_impact ON player_impact(match_id, team_id)")
    cursor.execute("CREATE INDEX idx_fatigue ON fixture_fatigue(match_id, team_id)")
    cursor.execute("CREATE INDEX idx_mv ON market_value(team_id, date)")
    cursor.execute("CREATE INDEX idx_motiv ON motivation_context(match_id, team_id)")
    
    conn.commit()
    conn.close()
    print(f"Database 'context_data.db' built successfully!")

if __name__ == "__main__":
    build_mock_context_database()
