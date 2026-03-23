import requests
import re
import json

url = "https://www.goal.com/en-gb/results/2026-03-22"
HEADERS = {"User-Agent": "Mozilla/5.0"}
print(f"Fetching {url}")
r = requests.get(url, headers=HEADERS)

pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
match = re.search(pattern, r.text, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    page_props = data.get('props', {}).get('pageProps', {})
    content = page_props.get('content', {})
    live_scores_groups = content.get('liveScores', [])
    
    leagues = set()
    for g in live_scores_groups:
        comp_name = g.get('competition', {}).get('name', '')
        if comp_name:
            leagues.add(comp_name)
    
    print(f"Total Unique Leagues Found: {len(leagues)}")
    
    # Check specific leagues
    targets = ["Süper Lig", "Premier League", "LaLiga", "Ligue 1", "Serie A", "UEFA Champions League", "UEFA Europa League"]
    for t in targets:
        # fuzzy match
        found = [l for l in leagues if t.lower() in l.lower() or "super" in l.lower()]
        if found:
            print(f"✅ Found {t} -> Matches: {found[:3]}")
        else:
            print(f"❌ Missing {t}")
else:
    print("Match not found.")
