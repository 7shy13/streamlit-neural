import re
import json

def extract_match():
    with open('goal_debug.html', encoding='utf-8') as f:
        html = f.read()
    
    match = re.search(r'<script id=\"__NEXT_DATA__\" type=\"application/json\">(.*?)</script>', html, re.DOTALL)
    data = json.loads(match.group(1))
    
    # Path found: root.props.pageProps.content.liveScores[1].matches[0]
    m = data['props']['pageProps']['content']['liveScores'][1]['matches'][0]
    print(json.dumps(m, indent=2))

if __name__ == "__main__":
    extract_match()
