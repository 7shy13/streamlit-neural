
import requests
import json

def check_specifics():
    base_url = "http://localhost:5050"
    r_scrape = requests.post(f"{base_url}/api/scrape")
    scrape_data = r_scrape.json()
    
    payload = {
        "matches": scrape_data["matches"],
        "injuries": scrape_data["injuries"]
    }
    r_analyze = requests.post(f"{base_url}/api/analyze", json=payload)
    results = r_analyze.json()['results']
    
    print("--- TARGETED DIAGNOSTICS ---")
    targets = ["PSG", "Tottenham", "Arnavutluk", "Polonya", "Mainz", "Lille", "Rijeka", "Strasbourg", "Vallecano"]
    
    for res in results:
        for t in targets:
            if t in res['home'] or t in res['away']:
                print(f"Match: {res['home']:20} vs {res['away']:20}")
                print(f"  Home Elo: {res['home_elo']} | Away Elo: {res['away_elo']}")
                break

if __name__ == "__main__":
    check_specifics()
