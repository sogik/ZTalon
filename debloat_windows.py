import sys
import ctypes
import os
import tempfile
import subprocess
import requests
import winreg
import shutil
import threading
import time
import logging

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

class InstallationWorker(threading.Thread):
    def __init__(self, exe_name, url, args=None, callback=None):
        super().__init__()
        self.exe_name = exe_name
        self.url = url
        self.args = args if args else []
        self.callback = callback

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            exe_path = os.path.join(temp_dir, self.exe_name)

            for attempt in range(3):
                try:
                    log(f"Downloading {self.exe_name} (Attempt {attempt + 1}/3)...")
                    response = requests.get(self.url, stream=True, timeout=10)
                    if response.status_code == 200:
                        with open(exe_path, "wb") as file:
                            for chunk in response.iter_content(chunk_size=8192):
                                file.write(chunk)
                        log(f"Download complete: {exe_path}")
                        break
                except Exception as e:
                    log(f"Download failed: {e}")
                    time.sleep(3)
            else:
                log(f"Failed to download {self.exe_name} after multiple attempts.")
                return

            log(f"Running {self.exe_name}...")
            process = subprocess.Popen(
                [exe_path, *self.args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            process.wait()
            if process.returncode != 0:
                log(f"Error running {self.exe_name}: {process.stderr.read()}")
            log(f"{self.exe_name} installation complete.")
            if self.callback:
                self.callback()

        except Exception as e:
            log(f"Error: {e}")
            if self.callback:
                self.callback()

def apply_registry_changes():
    log("Applying registry changes...")
    try:
        registry_modifications = [
            # Visual changes
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "TaskbarAl", winreg.REG_DWORD, 0), # Align taskbar to the left
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "AppsUseLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "SystemUsesLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentColorMenu", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu (1)  --.
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\Personalize", "ColorPrevalence", winreg.REG_DWORD, 1) # Makes accent color the color of the taskbar and start menu (2)   |-- These are redundant. I know
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\DWM", "AccentColorInStartAndTaskbar", winreg.REG_DWORD, 1) # Makes accent color the color of the taskbar and start menu (3)                   --'
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentPalette", winreg.REG_BINARY, b"\x00" * 32), # Makes the taskbar black
        ]
        for root_key, key_path, value_name, value_type, value in registry_modifications:
            try:
                with winreg.CreateKeyEx(root_key, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, value_name, 0, value_type, value)
                    log(f"Applied {value_name} to {key_path}")
            except Exception as e:
                log(f"Failed to modify {value_name} in {key_path}: {e}")
        log("Registry changes applied successfully.")
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["start", "explorer.exe"], shell=True)
        log("Explorer restarted to apply registry changes.")
        run_edge_vanisher()
        log("Edge Vanisher started successfully")
        
    except Exception as e:
        log(f"Error applying registry changes: {e}")

def run_edge_vanisher():
    log("Starting Edge Vanisher script execution...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/talon-blockedge/refs/heads/main/edge_vanisher.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "edge_vanisher.ps1")
        log(f"Attempting to download Edge Vanisher script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("Edge Vanisher script successfully saved to disk")
        
        powershell_command = (
            f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
            f"& '{script_path}'; exit" 
        )
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Edge Vanisher execution completed successfully")
            log(f"Process output: {process.stdout}")
            run_oouninstall()
        else:
            log(f"Edge Vanisher execution failed with return code: {process.returncode}")
            log(f"Process error: {process.stderr}")
            run_oouninstall()
            
    except requests.exceptions.RequestException as e:
        log(f"Network error during Edge Vanisher script download: {str(e)}")
        run_oouninstall()
    except IOError as e:
        log(f"File I/O error while saving Edge Vanisher script: {str(e)}")
        run_oouninstall()
    except Exception as e:
        log(f"Unexpected error during Edge Vanisher execution: {str(e)}")
        run_oouninstall()

def run_oouninstall():
    log("Starting Office Online uninstallation process...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/oouninstaller/refs/heads/main/uninstall_oo.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "uninstall_oo.ps1")
        log(f"Attempting to download OO uninstall script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("OO uninstall script successfully saved to disk")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Office Online uninstallation completed successfully")
            log(f"Process stdout: {process.stdout}")
            run_profile_tweaks()
        else:
            log(f"Office Online uninstallation failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            run_profile_tweaks()
            
    except Exception as e:
        log(f"Unexpected error during OO uninstallation: {str(e)}")
        run_profile_tweaks()

def run_profile_tweaks():
    log("Starting Windows profile tweaks...")
    try:
        temp_dir = tempfile.gettempdir()
        exe_name = "applyprofile.exe"
        exe_path = os.path.join(temp_dir, exe_name)
        url = "https://github.com/ravendevteam/talon-applyprofile/releases/download/v1.1.0/applyprofile.exe"
        download_success = False
        for attempt in range(3):
            try:
                log(f"Downloading {exe_name} (Attempt {attempt + 1}/3)...")
                response = requests.get(url, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(exe_path, "wb") as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            file.write(chunk)
                    log(f"Download complete: {exe_path}")
                    download_success = True
                    break
                else:
                    log(f"Download failed with status code: {response.status_code}")
            except Exception as e:
                log(f"Download attempt {attempt + 1} failed: {e}")
                time.sleep(3)

        if not download_success:
            log("Failed to download profile tweaker")
            run_applybackground()
            return

        if not os.path.exists(exe_path):
            log(f"Profile tweaker not found at: {exe_path}")
            run_applybackground()
            return

        log(f"Running profile tweaker from: {exe_path}")
        process = subprocess.run(
            [exe_path, "--barebones"],
            capture_output=True,
            text=True
        )

        if process.returncode == 0:
            log("Profile tweaks applied successfully")
        else:
            log(f"Error applying profile tweaks: {process.stderr}")

        log("Profile tweaks complete")
        run_applybackground()

    except Exception as e:
        log(f"Error in profile tweaks: {str(e)}")
        run_applybackground()


def run_applybackground():
    log("Starting background application setup...")
    try:
        worker = InstallationWorker(
            "applybackground.exe",
            "https://github.com/ravendevteam/talon-applybackground/releases/download/v1.0.0/applybackground.exe",
            callback=run_winconfig
        )
        log(f"Created InstallationWorker for background application")
        log(f"Download URL: {worker.url}")
        log(f"Target executable: {worker.exe_name}")
        worker.start()
        log("Background application installation thread started")
    except Exception as e:
        log(f"Error initializing background application setup: {str(e)}")

def run_winconfig():
    log("Starting Windows configuration process...")
    try:
        script_url = "https://win11debloat.raphi.re/"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Win11Debloat.ps1")
        log(f"Attempting to download Windows configuration script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("Windows configuration script successfully saved to disk")
        
        powershell_command = (
            f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
            f"& '{script_path}' -Silent -RemoveApps -RemoveGamingApps -DisableTelemetry "
            f"-DisableBing -DisableSuggestions -DisableLockscreenTips -RevertContextMenu "
            f"-TaskbarAlignLeft -HideSearchTb -DisableWidgets -DisableCopilot -ExplorerToThisPC"
        )
        log(f"Executing PowerShell command with parameters:")
        log(f"Command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Windows configuration completed successfully")
            log(f"Process stdout: {process.stdout}")
            run_updatepolicychanger()
        else:
            log(f"Windows configuration failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except requests.exceptions.RequestException as e:
        log(f"Network error during Windows configuration script download: {str(e)}")
    except IOError as e:
        log(f"File I/O error while saving Windows configuration script: {str(e)}")
    except Exception as e:
        log(f"Unexpected error during Windows configuration: {str(e)}")

def run_updatepolicychanger():
    log("Starting UpdatePolicyChanger script execution...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/talon-updatepolicy/refs/heads/main/UpdatePolicyChanger.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "UpdatePolicyChanger.ps1")
        log(f"Attempting to download UpdatePolicyChanger script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("UpdatePolicyChanger script successfully saved to disk")
        
        powershell_command = (
            f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
            f"& '{script_path}'; exit" 
        )
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("UpdatePolicyChanger execution completed successfully")
            log(f"Process output: {process.stdout}")
            finalize_installation()
        else:
            log(f"UpdatePolicyChanger execution failed with return code: {process.returncode}")
            log(f"Process error: {process.stderr}")
            finalize_installation()
            
    except requests.exceptions.RequestException as e:
        log(f"Network error during UpdatePolicyChanger script download: {str(e)}")
        finalize_installation()
    except IOError as e:
        log(f"File I/O error while saving UpdatePolicyChanger script: {str(e)}")
        finalize_installation()
    except Exception as e:
        log(f"Unexpected error during UpdatePolicyChanger execution: {str(e)}")
        finalize_installation()

def finalize_installation():
    log("Installation complete. Restarting system...")
    try:
        subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
    except subprocess.CalledProcessError as e:
        log(f"Error during restart: {e}")
        try:
            os.system("shutdown /r /t 0")
        except Exception as e:
            log(f"Failed to restart system: {e}")

if __name__ == "__main__":
    apply_registry_changes()
