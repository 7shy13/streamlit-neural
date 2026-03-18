import re
import json

def find_path_to_string(obj, target, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            res = find_path_to_string(v, target, f"{path}.{k}")
            if res: return res
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            res = find_path_to_string(item, target, f"{path}[{i}]")
            if res: return res
    elif isinstance(obj, str):
        if target.lower() in obj.lower():
            return path
    return None

def debug():
    with open('goal_debug.html', encoding='utf-8') as f:
        html = f.read()
    
    match = re.search(r'<script id=\"__NEXT_DATA__\" type=\"application/json\">(.*?)</script>', html, re.DOTALL)
    if not match:
        print("NEXT_DATA NOT FOUND")
        return
        
    data = json.loads(match.group(1))
    path = find_path_to_string(data, "Fenerbahce")
    print(f"PATH TO FENERBAHCE: {path}")
    
    # Also find if there's a score nearby
    if path:
        # Navigate to the parent or grandparent to see the structure
        parts = path.split('.')
        # Remove [x] or .key
        current = data
        for p in parts[1:-1]: # skip root and the final key
            if '[' in p:
                key, idx = p.split('[')
                idx = int(idx[:-1])
                current = current[key][idx]
            else:
                current = current[p]
        
        print("\nStructure at parent:")
        print(json.dumps(current, indent=2))

if __name__ == "__main__":
    debug()
