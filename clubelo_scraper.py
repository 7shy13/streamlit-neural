import requests
import json
import os
import csv
from datetime import datetime
from io import StringIO

def fetch_clubelo_rankings():
    """
    Fetches the latest global rankings from clubelo.com API.
    Returns a dictionary mapping club names to Elo ratings.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"http://api.clubelo.com/{today}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print(f"[ClubElo] Fetching rankings from {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        # Parse CSV content
        f = StringIO(response.text)
        reader = csv.DictReader(f)
        
        elo_map = {}
        for row in reader:
            club = row.get('Club', '').strip()
            rating = row.get('Elo', '').strip()
            if club and rating:
                try:
                    elo_map[club] = float(rating)
                except ValueError:
                    continue
        
        if elo_map:
            output_path = 'clubelo_data.json'
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(elo_map, f, indent=2, ensure_ascii=False)
            print(f"[ClubElo] Successfully saved {len(elo_map)} rankings to {output_path}")
            return elo_map
            
    except Exception as e:
        print(f"[ClubElo] Error fetching rankings: {e}")
        return {}

if __name__ == "__main__":
    fetch_clubelo_rankings()
