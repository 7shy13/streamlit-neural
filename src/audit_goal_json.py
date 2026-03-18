import re
import json

def debug_goal_json():
    try:
        with open('goal_debug.html', encoding='utf-8') as f:
            html = f.read()
        
        pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
        match = re.search(pattern, html, re.DOTALL)
        
        if not match:
            print("NOT FOUND")
            return
            
        data = json.loads(match.group(1))
        page_props = data.get('props', {}).get('pageProps', {})
        
        print(f"Top-level keys: {list(data.keys())}")
        print(f"PageProps keys: {list(page_props.keys())}")
        
        if 'initialState' in page_props:
            print(f"InitialState keys: {list(page_props['initialState'].keys())}")
            
        # Try to find 'fixtures' or 'matches' anywhere
        def search(obj, path=""):
            if isinstance(obj, dict):
                if 'fixtures' in obj: print(f"FOUND fixtures at: {path}")
                if 'matches' in obj: print(f"FOUND matches at: {path}")
                for k, v in obj.items():
                    search(v, f"{path}.{k}")
            elif isinstance(obj, list):
                if obj and isinstance(obj[0], dict):
                    search(obj[0], f"{path}[0]")

        search(page_props, "props.pageProps")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_goal_json()
