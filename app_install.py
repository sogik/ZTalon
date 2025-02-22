import sys
import ctypes
import os
import tempfile
import subprocess
import requests
import shutil
import time
import logging
import json

LOG_FILE = "talon.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log(message):
    logging.info(message)
    print(message)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)

def run_appinstaller():
    log("Starting app installer...")
    try:
        script_url = "https://raw.githubusercontent.com/gameshler/Ultimate-Windows-Optimization-Guide/refs/heads/main/4%20Installers/1%20Installers.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "appinstaller.ps1")
        log(f"Attempting to download installer script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")

        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("install completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"install failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False