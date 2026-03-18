import requests
import json
from bs4 import BeautifulSoup
import re

print("Fetching Iddaa.com MBS1...")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
r = requests.get("https://www.iddaa.com/program/futbol?mbs=1", headers=headers)

soup = BeautifulSoup(r.text, 'html.parser')
script = soup.find('script', id='__NEXT_DATA__')

if not script:
    print("No __NEXT_DATA__ found.")
else:
    try:
        data = json.loads(script.string)
        print("JSON loaded successfully.")
        
        # Deep extract: usually it's in props -> pageProps -> initialStoreState or similar
        # Let's stringify and regex search for team names to see where the data hides
        dump = json.dumps(data)
        
        # Simple extraction using regex on the raw json string
        match_events = re.findall(r'\"eventName\":\"(.*?)\"', dump)
        print(f"Total events found in JSON: {len(match_events)}")
        if match_events:
            print("Sample events:", match_events[:5])
            
    except Exception as e:
        print("Error:", e)
