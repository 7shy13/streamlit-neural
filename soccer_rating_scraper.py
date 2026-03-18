import requests
import json
import time
import os
from bs4 import BeautifulSoup

def scrape_soccer_rating_elos():
    """
    Scrapes the top 1500+ team Elo ratings and National Teams from soccer-rating.com.
    Returns a dictionary mapping team names to their Elo ratings.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    elo_map = {}
    
    # 1. CLUB RANKINGS (Depth: Top 1500)
    for start in range(0, 1500, 100):
        url = f"https://www.soccer-rating.com/football-club-ranking/ranking.php?start={start}"
        print(f"[EloScraper] Fetching Clubs {url}...")
        _scrape_page(url, headers, elo_map)
        time.sleep(1.2)

    # 2. NATIONAL TEAM RANKINGS (Correct URL)
    national_url = "https://www.soccer-rating.com/fifa-ranking/"
    print(f"[EloScraper] Fetching National Teams {national_url}...")
    _scrape_page(national_url, headers, elo_map)

    if elo_map:
        output_path = 'soccer_rating_data.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rating_map, f, indent=2, ensure_ascii=False)
        print(f"[EloScraper] Exported {len(rating_map)} teams to {output_path}")

    return elo_map

def _scrape_page(url, headers, elo_map):
    try:
        from naming_utils import normalize_turkish
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        r.encoding = r.apparent_encoding 
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Site uses /TeamName/1234/ structure for links
        links = soup.find_all('a', href=lambda h: h and h.count('/') >= 2)
        
        for link in links:
            team_name = link.text.strip()
            if not team_name: continue
            
            parent_row = link.find_parent('tr')
            if parent_row:
                cols = parent_row.find_all('td')
                rating = None
                for cell in cols:
                    text = cell.text.strip().replace(',', '')
                    try:
                        val = float(text)
                        if 1000 < val < 3500: # Slightly lower threshold for nations
                            rating = val
                            break
                    except ValueError:
                        continue
                
                if rating:
                    clean_name = normalize_turkish(team_name)
                    elo_map[clean_name] = rating
    except Exception as e:
        print(f"[EloScraper] Error scraping {url}: {e}")
        
    return elo_map

if __name__ == "__main__":
    scrape_soccer_rating_elos()
