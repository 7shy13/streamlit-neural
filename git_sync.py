import subprocess
import os
import sys

def find_git_executable():
    """Attempts to find the git executable in common paths if not in PATH."""
    import shutil
    git_path = shutil.which("git")
    if git_path:
        return git_path
        
    # Common Windows paths
    common_paths = [
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\git.exe"),
        # Portable Git in the project
        os.path.join(os.getcwd(), "tools", "git", "bin", "git.exe")
    ]
    
    import glob
    for path_pattern in common_paths:
        matches = glob.glob(path_pattern)
        if matches:
            return matches[0]
            
    return None

def sync_to_github(commit_message="Automatic update from Antigravity"):
    git_exe = find_git_executable()
    
    if not git_exe:
        return False, "Git executable not found. Please install Git or add it to PATH."
        
    try:
        # 1. Check if it's a git repo
        if not os.path.exists(".git"):
            # Initialize if not present (Optional, but let's assume it exists for now)
            # subprocess.run([git_exe, "init"], check=True)
            return False, "Not a Git repository. Please run 'git init' manually first."

        # 2. Add
        subprocess.run([git_exe, "add", "."], check=True)
        
        # 3. Commit
        # We use a try-except here because if there's nothing to commit, it returns 1
        subprocess.run([git_exe, "commit", "-m", commit_message], capture_output=True)
        
        # 4. Push
        result = subprocess.run([git_exe, "push"], capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, "Successfully pushed to GitHub."
        else:
            return False, f"Push failed: {result.stderr}"
            
    except subprocess.CalledProcessError as e:
        return False, f"Git command failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

if __name__ == "__main__":
    success, message = sync_to_github()
    print(f"Success: {success}")
    print(f"Message: {message}")
