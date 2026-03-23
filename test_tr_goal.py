import requests
import re
import json

url = "https://www.goal.com/tr/fikstur-ve-sonuclar/2026-03-22"
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
    print(f"Found {len(live_scores_groups)} groups.")
    for g in live_scores_groups[:5]:
        print(g.get('competition', {}).get('name', ''))
else:
    print("Match not found.")
