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
            for line in process.stdout:
                log(line.strip())
                if self.exe_name == "cttwinutil.exe" and "Tweaks are finished" in line:
                    log("CTT WinUtil process detected completion. Terminating applyprofile.exe.")
                    subprocess.run(["taskkill", "/F", "/IM", "applyprofile.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait()
            if process.returncode != 0:
                log(f"Error running {self.exe_name}: {process.stderr.read()}")
            log(f"{self.exe_name} installation complete.")
            if self.callback:
                self.callback()

        except Exception as e:
            log(f"Error: {e}")

def apply_registry_changes():
    log("Applying registry changes...")
    try:
        registry_modifications = [
            # Visual changes
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "TaskbarAl", winreg.REG_DWORD, 0), # Align taskbar to the left
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "AppsUseLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "SystemUsesLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentColorMenu", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentPalette", winreg.REG_BINARY, b"\x00" * 32), # Makes the taskbar black
            # Below are registry changes for disabling "feature" (bloat) updates
            (winreg.HKEY_LOCAL_MACHINE, r"Software\\Policies\\Microsoft\\Windows\\WindowsUpdate", "DeferQualityUpdates", winreg.REG_DWORD, 1), # Enables the delay of security updates
            (winreg.HKEY_LOCAL_MACHINE, r"Software\\Policies\\Microsoft\\Windows\\WindowsUpdate", "DeferQualityUpdatesPeriodInDays", winreg.REG_DWORD, 4), # Sets delay of security updates for 4 days
            (winreg.HKEY_LOCAL_MACHINE, r"Software\\Policies\\Microsoft\\Windows\\WindowsUpdate", "TargetReleaseVerion", winreg.REG_DWORD, 1), # Enables the target release version policy
            (winreg.HKEY_LOCAL_MACHINE, r"Software\\Policies\\Microsoft\\Windows\\WindowsUpdate", "TargetReleaseVersionInfo", winreg.REG_SZ, "24H2"), # Sets the target release version to 24H2
            (winreg.HKEY_LOCAL_MACHINE, r"Software\\Policies\\Microsoft\\Windows\\WindowsUpdate", "ProductVersion", winreg.REG_SZ, "Windows 11") # Sets the product version to Windows 11
        ]
        for root_key, key_path, value_name, value_type, value in registry_modifications:
            try:
                with winreg.OpenKey(root_key, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, value_name, 0, value_type, value)
                log(f"Applied {value_name} to {key_path}")
            except Exception as e:
                log(f"Failed to modify {value_name} in {key_path}: {e}")
        log("Registry changes applied successfully.")
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["start", "explorer.exe"], shell=True)
        log("Explorer restarted to apply registry changes.")
        run_applybackground()
    except Exception as e:
        log(f"Error applying registry changes: {e}")

def run_applybackground():
    print("Running background application setup...")
    worker = InstallationWorker(
        "applybackground.exe",
        "https://github.com/ravendevteam/talon-applybackground/releases/download/v1.0.0/applybackground.exe",
        callback=run_winconfig
    )
    worker.start()

def run_winconfig():
    log("Running Windows configuration script...")
    try:
        script_url = "https://win11debloat.raphi.re/"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Win11Debloat.ps1")
        response = requests.get(script_url)
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("Windows configuration script downloaded.")
        powershell_command = (
            f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
            f"& '{script_path}' -Silent -RemoveApps -RemoveGamingApps -DisableTelemetry "
            f"-DisableBing -DisableSuggestions -DisableLockscreenTips -RevertContextMenu "
            f"-TaskbarAlignLeft -HideSearchTb -DisableWidgets -DisableCopilot -ExplorerToThisPC"
        )
        subprocess.run(["powershell", "-Command", powershell_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("Windows configuration applied successfully.")
        run_edge_vanisher()
    except Exception as e:
        log(f"Error running PowerShell script: {e}")

def run_edge_vanisher():
    log("Running Edge Vanisher script...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/talon-blockedge/refs/heads/main/edge_vanisher.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "edge_vanisher.ps1")
        response = requests.get(script_url)
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("Edge Vanisher script downloaded.")
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        subprocess.run(["powershell", "-Command", powershell_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("Edge Vanisher applied successfully.")
        run_oouninstall()
    except Exception as e:
        log(f"Error running Edge Vanisher script: {e}")

def run_oouninstall():
    log("Running OOUninstall script...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/oouninstaller/refs/heads/main/uninstall_oo.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "uninstall_oo.ps1")
        response = requests.get(script_url)
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("OOUninstall script downloaded.")
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        subprocess.run(["powershell", "-Command", powershell_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("OOUninstall applied successfully.")
    except Exception as e:
        log(f"Error running OOUninstall script: {e}")

def finalize_installation():
    log("Installation complete. Restarting system...")
    subprocess.run(["shutdown", "/r", "/t", "10"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    apply_registry_changes()
