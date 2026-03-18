import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random

def scrape_global_market_values():
    """
    Scrapes Transfermarkt for multiple countries and leagues to build a 
    comprehensive global market value database.
    """
    print("--- Transfermarkt Global Bütçe Kazıyıcı ---")
    
    # Country IDs from research
    COUNTRIES = {
        "Turkey": 174,
        "England": 189,
        "Spain": 157,
        "Germany": 40,
        "Italy": 75,
        "France": 50
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    all_market_values = {}

    for country_name, country_id in COUNTRIES.items():
        print(f"\n[Country] {country_name} (ID: {country_id}) taranıyor...")
        url = f"https://www.transfermarkt.com.tr/wettbewerbe/national/wettbewerbe/{country_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all leagues in the table
            table = soup.find('table', class_='items')
            if not table:
                continue
                
            rows = table.find('tbody').find_all('tr')
            leagues_to_scrape = []
            
            # Typically first 2-3 rows are the most relevant (1.Lig, 2.Lig, Cup)
            for row in rows[:3]:
                link_node = row.find('td', class_='hauptlink')
                if link_node:
                    a_tag = link_node.find('a')
                    if a_tag and '/wettbewerb/' in a_tag['href']:
                        # Convert to startseite link if needed
                        path = a_tag['href']
                        if 'startseite' not in path:
                            path = path.replace('/wettbewerb/', '/startseite/wettbewerb/')
                        
                        leagues_to_scrape.append({
                            "name": a_tag.text.strip(),
                            "url": f"https://www.transfermarkt.com.tr{path}"
                        })

            for league in leagues_to_scrape:
                print(f"  [League] {league['name']} taranıyor...")
                time.sleep(random.uniform(1.5, 3.0)) # Be polite to avoid IP block
                
                l_res = requests.get(league['url'], headers=headers, timeout=20)
                l_soup = BeautifulSoup(l_res.content, 'html.parser')
                
                # The team table usually has class 'items'
                l_table = l_soup.find('table', class_='items')
                if not l_table:
                    # Fallback for some page structures
                    l_table = l_soup.find('div', id='yw1').find('table') if l_soup.find('div', id='yw1') else None
                
                if not l_table:
                    print(f"    [!] Tablo bulunamadı: {league['name']}")
                    continue
                
                tbody = l_table.find('tbody')
                if not tbody: continue
                
                l_rows = tbody.find_all('tr', recursive=False)
                for l_row in l_rows:
                    cols = l_row.find_all('td', recursive=False)
                    if len(cols) >= 3:
                        # Team name is in td.hauptlink
                        name_node = l_row.find('td', class_='hauptlink')
                        if name_node:
                            team_link = name_node.find('a')
                            if team_link:
                                team_name = team_link.text.strip()
                                
                                # Value is in td.rechts (usually the last or second to last)
                                value_nodes = l_row.find_all('td', class_='rechts')
                                if value_nodes:
                                    # The total value is often the last 'rechts' cell in the row
                                    value_text = value_nodes[-1].text.strip()
                                    
                                    val_parsed = 0.0
                                    try:
                                        if 'milyar' in value_text:
                                            cl = value_text.replace('milyar', '').replace('€', '').replace(',', '.').strip()
                                            val_parsed = float(cl) * 1000.0
                                        elif 'mil.' in value_text or 'm' in value_text:
                                            cl = value_text.replace('mil.', '').replace('€', '').replace('m', '').replace(',', '.').strip()
                                            val_parsed = float(cl)
                                        elif 'bin' in value_text or 'k' in value_text:
                                            cl = value_text.replace('bin', '').replace('€', '').replace('k', '').replace(',', '.').strip()
                                            val_parsed = float(cl) / 1000.0
                                    except:
                                        pass
                                    
                                    if val_parsed > 0:
                                        all_market_values[team_name] = val_parsed
                
        except Exception as e:
            print(f"  [HATA] {country_name} taranırken sorun oluştu: {e}")

    # Save to local JSON Cache
    output_path = 'live_market_values.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_market_values, f, indent=2, ensure_ascii=False)
    print(f"[MarketValue] Successfully saved {len(all_market_values)} values to {output_path}")
    return all_market_values

if __name__ == "__main__":
    scrape_global_market_values()
