
import requests
import json

def final_verification():
    base_url = "http://localhost:5050"
    
    print("[Verif] 1. Scraping live data...")
    r_scrape = requests.post(f"{base_url}/api/scrape")
    r_scrape.raise_for_status()
    scrape_data = r_scrape.json()
    
    print(f"[Verif] Scraped {scrape_data['match_count']} matches.")
    
    print("[Verif] 2. Analyzing data...")
    payload = {
        "matches": scrape_data["matches"],
        "injuries": scrape_data["injuries"]
    }
    r_analyze = requests.post(f"{base_url}/api/analyze", json=payload)
    r_analyze.raise_for_status()
    analyze_data = r_analyze.json()
    
    print(f"[Verif] Analysis complete. Value bets found: {analyze_data['value_bets_found']} / {analyze_data['total_matches']}\n")
    
    results = analyze_data['results']
    # Check Liverpool vs Galatasaray specifically
    for res in results:
        if "Liverpool" in res['home'] and "Galatasaray" in res['away']:
            print("--- CASE STUDY: Liverpool vs Galatasaray ---")
            print(f"Home Elo: {res['home_elo']}")
            print(f"Away Elo: {res['away_elo']}")
            print(f"Probabilities: 1: {res['value_bets'][0]['prob']}% X: {res['value_bets'][1]['prob']}% 2: {res['value_bets'][2]['prob']}%")
            print(f"Fair Odds: 1: {res['value_bets'][0]['fair_odd']} X: {res['value_bets'][1]['fair_odd']} 2: {res['value_bets'][2]['fair_odd']}")
            print(f"Is Value Found? {res['has_value']}")
            break

if __name__ == "__main__":
    final_verification()
