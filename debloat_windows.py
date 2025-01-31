import sys
import ctypes
import os
import tempfile
import subprocess
import requests
import winreg
import shutil
from PyQt5.QtCore import QThread, pyqtSignal

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

class InstallationWorker(QThread):
    progress_signal = pyqtSignal(str)
    completion_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, exe_name, url, args=None):
        super().__init__()
        self.exe_name = exe_name
        self.url = url
        self.args = args if args else []

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            exe_path = os.path.join(temp_dir, self.exe_name)
            self.progress_signal.emit(f"Downloading {self.exe_name}...")
            response = requests.get(self.url, stream=True)
            with open(exe_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            self.progress_signal.emit(f"Download complete: {exe_path}")
            self.progress_signal.emit(f"Running {self.exe_name}...")
            process = subprocess.Popen(
                [exe_path, *self.args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    self.progress_signal.emit(line.strip())
                    if "Finished" in line:
                        self.progress_signal.emit(f"{self.exe_name} complete.")
                        break
            finally:
                process.terminate()
                process.wait()
                self.progress_signal.emit(f"{self.exe_name} terminated.")
            self.completion_signal.emit(f"{self.exe_name} installation complete.")
        except Exception as e:
            self.error_signal.emit(f"Error: {e}")

def apply_registry_changes():
    print("Applying registry changes...")
    try:
        taskbar_key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, taskbar_key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "TaskbarAl", 0, winreg.REG_DWORD, 0)
            print("Taskbar alignment set.")
        except PermissionError:
            print("Error: Unable to modify Taskbar alignment.")
        except Exception as e:
            print(f"Unexpected error while modifying Taskbar alignment: {e}")

        accent_key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent"
        black_palette = bytes([0x00] * 32)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, accent_key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "AccentColorMenu", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "StartColorMenu", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "AccentPalette", 0, winreg.REG_BINARY, black_palette)
            print("Accent color settings applied.")
        except PermissionError:
            print("Error: Unable to modify Accent settings.")
        except Exception as e:
            print(f"Unexpected error while modifying Accent settings: {e}")

        themes_key_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, themes_key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(key, "ColorPrevalence", 0, winreg.REG_DWORD, 1)
            print("Light theme and accent color settings applied.")
        except PermissionError:
            print("Error: Unable to modify light theme or accent color settings.")
        except Exception as e:
            print(f"Unexpected error while modifying light theme or accent color settings: {e}")

        taskbar_pinned_path = r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Taskband"
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, taskbar_pinned_path)
            print("Taskbar icons cleared.")
        except FileNotFoundError:
            print("No Taskbar icons to clear.")
        except PermissionError:
            print("Error: Unable to clear Taskbar icons.")
        except Exception as e:
            print(f"Unexpected error while clearing Taskbar icons: {e}")

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
        run_applybackground()

    except Exception as e:
        print(f"Error applying registry changes: {e}")

def run_applybackground():
    print("Running background application setup...")
    worker = InstallationWorker(
        "applybackground.exe",
        "https://github.com/ravendevteam/talon-applybackground/releases/download/v1.0.0/applybackground.exe"
    )
    worker.progress_signal.connect(print)
    worker.completion_signal.connect(run_winconfig)
    worker.error_signal.connect(print)
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
            f"Set-ExecutionPolicy Unrestricted -Scope Process -Force; "
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
            err_output = process.stderr.read()
            print(f"Error: {err_output}")
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
        args=["--barebones"]
    )
    worker.progress_signal.connect(print)
    worker.completion_signal.connect(finalize_installation)
    worker.error_signal.connect(print)
    worker.start()

def finalize_installation():
    print("Installation complete.")

if __name__ == "__main__":
    apply_registry_changes()
