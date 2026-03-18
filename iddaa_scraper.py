import requests
import json
import time
from bs4 import BeautifulSoup

# Internal API for Iddaa sportsbook events (MBS1 matches are in here)
API_URL = "https://sportsbookv2.iddaa.com/sportsbook/events?st=1&type=0&version=0"
# Detail pattern: https://www.iddaa.com/program/futbol/mac-detay/1/{match_id}/sakat-ve-cezali

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.iddaa.com",
    "Referer": "https://www.iddaa.com/"
}

DEMO_MATCHES = [
    {"match_id": "1", "home": "Galatasaray",  "away": "Fenerbahce",  "iddaa_1": 2.10, "iddaa_X": 3.40, "iddaa_2": 2.80, "league": "Süper Lig", "source": "demo"},
    {"match_id": "2", "home": "Besiktas",     "away": "Trabzonspor", "iddaa_1": 1.95, "iddaa_X": 3.50, "iddaa_2": 3.10, "league": "Süper Lig", "source": "demo"},
]

def scrape_detailed_injuries(match_id):
    """
    Fetches missing player data directly from the Iddaa statistics API.
    Fast, reliable, and provides comprehensive player stats.
    """
    if not match_id:
        return []

    # API endpoint identified via network interception
    url = f"https://statisticsv2.iddaa.com/statistics/missingplayerandstats/1/{match_id}"
    
    try:
        print(f"[Scraper] Fetching injury API for {match_id}...")
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        if not data.get('isSuccess'):
            return []
            
        payload = data.get('data', {})
        home_players_raw = payload.get('homeTeam', {}).get('players', [])
        away_players_raw = payload.get('awayTeam', {}).get('players', [])
        
        def transform_player(p):
            return {
                "name": p.get('name', 'Unknown'),
                "pos": p.get('position', ''),
                "played": str(p.get('numberOfMatches', 0)),
                "type": p.get('reasonDetail', p.get('reason', ''))
            }
            
        home_players = [transform_player(p) for p in home_players_raw]
        away_players = [transform_player(p) for p in away_players_raw]
        
        # Return as [home_list, away_list] to remain compatible with api_server
        return [home_players, away_players]

    except Exception as e:
        print(f"[Scraper] Injury API error for {match_id}: {e}")
        return []

def scrape_iddaa_live():
    """
    Scrapes live matches using the internal Iddaa JSON API.
    Fast, reliable, includes Match IDs.
    """
    print("[Scraper] Fetching matches from API...")
    try:
        r = requests.get(API_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        events = data.get('data', {}).get('events', [])
        matches = []
        
        for e in events:
            # STRICT FILTER: Soccer only (sid: 1) and MBS1 only (mbc: 1)
            if e.get('sid') != 1: continue
            if e.get('mbc') != 1: continue
            
            match_id = str(e.get('i', ''))
            home = e.get('hn', 'Unknown')
            away = e.get('an', 'Unknown')
            
            # Extract 1X2 odds from markets (m)
            o1, oX, o2 = 0.0, 0.0, 0.0
            markets = e.get('m', [])
            for m in markets:
                # Market Type 1 is usually MS 1X2
                if m.get('t') == 1:
                    odds = m.get('o', [])
                    for o in odds:
                        if o.get('no') == 1: o1 = float(o.get('odd', 0))
                        if o.get('no') == 2: oX = float(o.get('odd', 0))
                        if o.get('no') == 3: o2 = float(o.get('odd', 0))
                    break
            
            # Extract League/Category info
            category = e.get('cn', '') # Country (e.g., İngiltere)
            league_raw = e.get('ln', '') # League (e.g., Premier Lig)
            league = f"{category} {league_raw}".strip() or "IDDAA"
            
            if home and away and (o1 > 0 or oX > 0 or o2 > 0):
                matches.append({
                    "match_id": match_id,
                    "home": home,
                    "away": away,
                    "iddaa_1": o1,
                    "iddaa_X": oX,
                    "iddaa_2": o2,
                    "league": league,
                    "match_time": e.get('d', 0), # Unix timestamp
                    "source": "live"
                })
        
        print(f"[Scraper] API returned {len(matches)} matches.")
        return matches
    except Exception as ex:
        print(f"[Scraper] API Scrape Error: {ex}")
        return DEMO_MATCHES

if __name__ == '__main__':
    res = scrape_iddaa_live()
    for m in res[:5]:
        print(f"ID: {m['match_id']} | {m['home']} vs {m['away']} | 1:{m['iddaa_1']} X:{m['iddaa_X']} 2:{m['iddaa_2']}")


# ─── Entry point for standalone test ─────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("ANTIGRAVITY Iddaa Live Scraper Test")
    print("=" * 60)
    
    matches = scrape_iddaa_live()
    print(f"\nTotal matches: {len(matches)}")
    print(f"Source: {matches[0].get('source','?') if matches else 'N/A'}")
    print("-" * 60)
    for m in matches[:10]:
        src = m.get('source', '?')
        t   = m.get('match_time', '')
        print(f"[{src}] {t:5s} | {m['home']:<25} vs {m['away']:<25} | "
              f"1:{m['iddaa_1']:.2f}  X:{m['iddaa_X']:.2f}  2:{m['iddaa_2']:.2f}  | {m['league']}")
