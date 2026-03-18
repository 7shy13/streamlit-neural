import requests
import json
import os
import time
import re
from bs4 import BeautifulSoup
from naming_utils import normalize_turkish, FluidMatcher

def scrape_team_player_ratings(team_name):
    """
    Scrapes individual player ratings from soccer-rating.com for a specific team.
    Returns a dictionary of {player_name: rating} and the total top-11 quality sum.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 1. First, find the team-specific URL from soccer_rating_data.json (which we already have)
    # We need to map team_name to the grounded name in soccer_rating_data.json
    try:
        with open('soccer_rating_data.json', 'r', encoding='utf-8') as f:
            anchors = json.load(f)
        
        matched_name = FluidMatcher.match(team_name, list(anchors.keys()))
        if not matched_name:
            print(f"[PlayerScraper] Could not find grounded anchor for {team_name}")
            return {}, 800 # Fallback 11 * 72avg
            
        # URL construction from grounded name (e.g., 'Fenerbahce' -> 'Fenerbahce')
        # soccer-rating uses URL-friendly names. Let's try to search or direct construct.
        search_url = f"https://www.soccer-rating.com/search.php?search={matched_name.replace(' ', '+')}"
        r_search = requests.get(search_url, headers=headers, timeout=15)
        soup_search = BeautifulSoup(r_search.text, 'html.parser')
        
        # Find the first link that looks like /Team-Name/123/
        team_link_node = soup_search.find('a', href=re.compile(r'^/[A-Za-z0-9-]+/\d+/$|^/[A-Za-z0-9-]+/n\d+/$'))
        if not team_link_node:
            print(f"[PlayerScraper] Could not find team link for {team_name} in search results.")
            return {}, 800
            
        team_url = f"https://www.soccer-rating.com{team_link_node['href']}"
        print(f"[PlayerScraper] Scraping players from {team_url}...")
        
        r_team = requests.get(team_url, headers=headers, timeout=15)
        soup_team = BeautifulSoup(r_team.text, 'html.parser')
        
        player_ratings = {}
        # The table of players (Expected Lineup and Squad)
        # Select all rows in tables that have player info
        rows = soup_team.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                # Soccer-rating often has Name in col 2, Rating in col 4
                name_cell = cells[1].text.strip()
                rating_cell = cells[3].text.strip()
                
                # Cleanup name: "1 Ugurcan Cakir (GK)" -> "Ugurcan Cakir"
                name_match = re.search(r'^\d*\s*(.*?)\s*\(', name_cell)
                if not name_match:
                    # Fallback if no (GK/DF) suffix
                    name_match = re.search(r'^\d*\s*(.*)', name_cell)
                
                if name_match:
                    clean_pname = normalize_turkish(name_match.group(1).strip())
                    try:
                        val = int(rating_cell)
                        if 30 < val < 100:
                            player_ratings[clean_pname] = val
                    except ValueError:
                        continue
        
        # Calculate summary metrics
        sorted_ratings = sorted(player_ratings.values(), reverse=True)
        top_11_avg = sum(sorted_ratings[:11]) / 11 if sorted_ratings else 72
        team_quality = sum(sorted_ratings[:11]) if sorted_ratings else 800
        
        print(f"[PlayerScraper] Found {len(player_ratings)} players for {team_name}. Top-11 Quality: {team_quality}")
        return player_ratings, team_quality
        
    except Exception as e:
        print(f"[PlayerScraper] Error: {e}")
        return {}, 800

def get_player_data_cache_path(team_name):
    safe_name = "".join([c if c.isalnum() else "_" for c in team_name])
    return f'src/player_data/{safe_name}.json'

def get_or_scrape_players(team_name, force=False):
    path = get_player_data_cache_path(team_name)
    if not force and os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    ratings, quality = scrape_team_player_ratings(team_name)
    data = {"ratings": ratings, "top_11_quality": quality, "timestamp": time.time()}
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data

if __name__ == "__main__":
    # Test
    print(get_or_scrape_players("Fenerbahce"))
