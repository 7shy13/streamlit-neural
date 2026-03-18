
import requests
import json

def verify_api():
    url = 'http://localhost:5050/api/scrape'
    print(f"Calling {url}...")
    try:
        r = requests.post(url, timeout=60)
        r.raise_for_status()
        data = r.json()
        print(f"Status: {data.get('status')}")
        print(f"Match Count: {data.get('match_count')}")
        print(f"Injury Teams: {data.get('injury_teams')}")
        
        # Check a sample match and its injury entry
        matches = data.get('matches', [])
        injuries = data.get('injuries', {})
        
        if matches and injuries:
            for m in matches[:3]:
                mid = m.get('match_id')
                if mid in injuries:
                    print(f"Match {mid} ({m['home']} vs {m['away']}) has injury data: {len(injuries[mid])} team lists.")
        
        with open('final_api_check.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    verify_api()
