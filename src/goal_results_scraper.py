import requests
from bs4 import BeautifulSoup
import datetime
import json
import re
import traceback

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

def get_results_for_date(date_str=None):
    """
    date_str: YYYY-MM-DD
    Returns a list of settled matches: {home, away, score_h, score_a, status}
    """
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    url = f"https://www.goal.com/en-gb/results/{date_str}"
    print(f"[ResultsScraper] Fetching {url}...")
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        
        pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
        match = re.search(pattern, r.text, re.DOTALL)
        if not match: return []
            
        data = json.loads(match.group(1))
        page_props = data.get('props', {}).get('pageProps', {})
        content = page_props.get('content', {})
        live_scores_groups = content.get('liveScores', [])
        
        matches = []
        for group in live_scores_groups:
            # Matches are organized within competition groups
            match_list = group.get('matches', [])
            for f in match_list:
                try:
                    # Based on audit: status "RESULT" means finished
                    status = f.get('status', '')
                    if status == "RESULT":
                        home = f.get('teamA', {}).get('name')
                        away = f.get('teamB', {}).get('name')
                        score_h = f.get('score', {}).get('teamA')
                        score_a = f.get('score', {}).get('teamB')
                        
                        if home and away and score_h is not None:
                            matches.append({
                                "home": str(home),
                                "away": str(away),
                                "score_h": int(score_h),
                                "score_a": int(score_a),
                                "status": "FT",
                                "date": date_str
                            })
                except: continue
                
        print(f"[ResultsScraper] Found {len(matches)} results.")
        return matches

    except Exception as e:
        print(f"[ResultsScraper] Error: {e}")
        return []

if __name__ == "__main__":
    # Test for yesterday
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    results = get_results_for_date(yesterday)
    for m in results[:10]:
        print(f"{m['home']} {m['score_h']}-{m['score_a']} {m['away']}")
