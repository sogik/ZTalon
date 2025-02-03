import os
import subprocess
import sys
import requests

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def download_toolbox(destination):
    url = "https://github.com/ravendevteam/toolbox/releases/latest/download/toolbox.exe"
    print(f"Downloading Toolbox from {url} to {destination}")
    try:
        response = requests.get(url, stream=True, verify=True)
        response.raise_for_status()
        
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Download completed successfully to {destination}")
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL certificate error: {ssl_err}")
        sys.exit(1)
    except requests.exceptions.RequestException as req_err:
        print(f"Error downloading Toolbox: {req_err}")
        sys.exit(1)

def run_toolbox(exe_path):
    print("Running Toolbox installation...")
    try:
        process = subprocess.run([exe_path, "install", "*", "--yes"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode == 0:
            print("Toolbox installation completed successfully.")
        else:
            print(f"Toolbox installation encountered an issue: {process.stderr.decode()}")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to run Toolbox: {e}")
        sys.exit(1)

def cleanup_toolbox(exe_path):
    print("Cleaning up...")
    os.remove(exe_path)
    print("Toolbox executable deleted.")

def main():
    script_dir = get_script_dir()
    toolbox_path = os.path.join(script_dir, "toolbox.exe")
    
    download_toolbox(toolbox_path)
    run_toolbox(toolbox_path)
    cleanup_toolbox(toolbox_path)
    print("Successfully installed Raven software packages.")
