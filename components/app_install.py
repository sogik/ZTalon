import sys
import ctypes
import os
import tempfile
import subprocess
import logging

from components.installer_patch import fetch_ultimate_installer, patch_installer_script

LOG_FILE = "ztalon.txt"
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
    except Exception:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)

def run_appinstaller():
    log("Starting app installer...")
    try:
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "appinstaller.ps1")
        log("Downloading official Ultimate installer script")
        log(f"Target script path: {script_path}")

        installer_content = fetch_ultimate_installer(timeout=30)
        patched_content = patch_installer_script(installer_content)
        
        with open(script_path, "w", encoding="utf-8") as file:
            file.write(patched_content)
        log("Installer script patched and saved to disk")

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
            return True
        else:
            log(f"install failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            return False
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False
