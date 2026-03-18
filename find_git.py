import os

def find_git():
    possible_paths = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\git.exe"),
        os.path.expandvars(r"%ProgramData%\Git\bin\git.exe"),
    ]
    
    # Search for GitHub Desktop
    local_app_data = os.environ.get('LOCALAPPDATA', '')
    if local_app_data:
        gh_desktop_root = os.path.join(local_app_data, 'GitHubDesktop')
        if os.path.exists(gh_desktop_root):
            for root, dirs, files in os.walk(gh_desktop_root):
                if 'git.exe' in files:
                    possible_paths.append(os.path.join(root, 'git.exe'))
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    # Hard search in AppData
    app_data = os.environ.get('APPDATA', '')
    if app_data:
        for root, dirs, files in os.walk(os.path.dirname(app_data)): # Search Local as well
            if 'git.exe' in files and 'bin' in root.lower():
                return os.path.join(root, 'git.exe')
                
    return None

if __name__ == "__main__":
    git_path = find_git()
    if git_path:
        print(f"FOUND_GIT: {git_path}")
    else:
        print("GIT_NOT_FOUND")
