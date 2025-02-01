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
                    print(f"Downloading {self.exe_name} (Attempt {attempt + 1}/3)...")
                    response = requests.get(self.url, stream=True, timeout=10)
                    if response.status_code == 200:
                        with open(exe_path, "wb") as file:
                            for chunk in response.iter_content(chunk_size=8192):
                                file.write(chunk)
                        print(f"Download complete: {exe_path}")
                        break
                except Exception as e:
                    print(f"Download failed: {e}")
                    time.sleep(3)
            else:
                print(f"Failed to download {self.exe_name} after multiple attempts.")
                return

            print(f"Running {self.exe_name}...")
            process = subprocess.Popen(
                [exe_path, *self.args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            for line in process.stdout:
                print(line.strip())

            process.wait()
            if process.returncode != 0:
                print(f"Error running {self.exe_name}: {process.stderr.read()}")

            print(f"{self.exe_name} installation complete.")

            if self.callback:
                self.callback()

        except Exception as e:
            print(f"Error: {e}")

def apply_registry_changes():
    print("Applying registry changes...")
    try:
        registry_modifications = [
            (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAl", winreg.REG_DWORD, 0),
            (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "AccentColorMenu", winreg.REG_DWORD, 0),
            (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "StartColorMenu", winreg.REG_DWORD, 0),
            (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Themes\Personalize", "AppsUseLightTheme", winreg.REG_DWORD, 0),
            (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Themes\Personalize", "SystemUsesLightTheme", winreg.REG_DWORD, 0),
            (r"Software\Microsoft\Windows\CurrentVersion\Explorer\Themes\Personalize", "ColorPrevalence", winreg.REG_DWORD, 1)
        ]

        for key_path, value_name, value_type, value in registry_modifications:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, value_name, 0, value_type, value)
                print(f"Applied {value_name} to {key_path}")
            except Exception as e:
                print(f"Failed to modify {value_name} in {key_path}: {e}")

        taskbar_pinned_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Taskband"
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, taskbar_pinned_path)
            print("Taskbar icons cleared.")
        except FileNotFoundError:
            print("No taskbar icons to clear.")

        start_menu_paths = [
            os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
        ]
        for start_menu_path in start_menu_paths:
            if os.path.exists(start_menu_path):
                for item in os.listdir(start_menu_path):
                    item_path = os.path.join(start_menu_path, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        print(f"Removed Start Menu item: {item}")
                    except Exception as e:
                        print(f"Error removing Start Menu item {item}: {e}")

        print("Taskbar and Start Menu cleared.")

        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["start", "explorer.exe"], shell=True)
        print("Explorer restarted to apply registry changes.")

        run_applybackground()

    except Exception as e:
        print(f"Error applying registry changes: {e}")

def run_applybackground():
    print("Running background application setup...")
    worker = InstallationWorker(
        "applybackground.exe",
        "https://github.com/ravendevteam/talon-applybackground/releases/download/v1.0.0/applybackground.exe",
        callback=run_winconfig
    )
    worker.start()

def run_winconfig():
    print("Running Windows configuration script...")
    try:
        script_url = "https://win11debloat.raphi.re/"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Win11Debloat.ps1")

        response = requests.get(script_url)
        with open(script_path, "wb") as file:
            file.write(response.content)

        print("Windows configuration script downloaded.")

        powershell_command = (
            f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
            f"& '{script_path}' -Silent -RemoveApps -RemoveGamingApps -DisableTelemetry "
            f"-DisableBing -DisableSuggestions -DisableLockscreenTips -RevertContextMenu "
            f"-TaskbarAlignLeft -HideSearchTb -DisableWidgets -DisableCopilot -ExplorerToThisPC"
        )

        process = subprocess.Popen(
            ["powershell", "-Command", powershell_command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        for line in process.stdout:
            print(line.strip())

        process.wait()
        if process.returncode != 0:
            print(f"Error: {process.stderr.read()}")
        else:
            print("Windows configuration applied successfully.")
            run_applyprofile()

    except Exception as e:
        print(f"Error running PowerShell script: {e}")

def run_applyprofile():
    print("Running profile-specific application setup...")
    worker = InstallationWorker(
        "applyprofile.exe",
        "https://github.com/ravendevteam/talon-applyprofile/releases/download/v1.0.0/applyprofile.exe",
        args=["--barebones"],
        callback=finalize_installation
    )
    worker.start()

def finalize_installation():
    print("Installation complete.")

if __name__ == "__main__":
    apply_registry_changes()
