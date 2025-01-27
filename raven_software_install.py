import os
import subprocess
import sys
import urllib.request

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def download_toolbox(destination):
    url = "https://github.com/ravendevteam/toolbox/releases/latest/download/toolbox.exe"
    print(f"Downloading Toolbox from {url} to {destination}")
    urllib.request.urlretrieve(url, destination)

def run_toolbox(exe_path):
    print("Running Toolbox installation...")
    process = subprocess.run([exe_path, "install", "*", "--yes"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode == 0:
        print("Toolbox installation completed successfully.")
    else:
        print("Toolbox installation encountered an issue:")
        print(process.stderr.decode())
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