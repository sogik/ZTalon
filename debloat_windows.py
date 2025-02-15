import sys
import ctypes
import os
import tempfile
import subprocess
import requests
import winreg
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

def apply_registry_changes():
    log("Applying registry changes...")
    try:
        registry_modifications = [
            # Visual changes
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "TaskbarAl", winreg.REG_DWORD, 1), # Align taskbar to the center
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "AppsUseLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "SystemUsesLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentColorMenu", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu (1)  --.
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\Personalize", "ColorPrevalence", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu (2)   |-- These are redundant. I know
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\DWM", "AccentColorInStartAndTaskbar", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu (3)                   --'
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentPalette", winreg.REG_BINARY, b"\x00" * 32), # Makes the taskbar black
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR", "AppCaptureEnabled", winreg.REG_DWORD, 0), #Fix the  Get an app for 'ms-gamingoverlay' popup
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\PolicyManager\\default\\ApplicationManagement\\AllowGameDVR", "Value", winreg.REG_DWORD, 0), # Disable Game DVR (Reduces FPS Drops)
            (winreg.HKEY_CURRENT_USER, r"Control Panel\\Desktop", "MenuShowDelay", winreg.REG_SZ, "0"),# Reduce menu delay for snappier UI
            (winreg.HKEY_CURRENT_USER, r"Control Panel\\Desktop\\WindowMetrics", "MinAnimate", winreg.REG_DWORD, 0),# Disable minimize/maximize animations
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "ExtendedUIHoverTime", winreg.REG_DWORD, 1),# Reduce hover time for tooltips and UI elements
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "HideFileExt", winreg.REG_DWORD, 0),# Show file extensions in Explorer (useful for security and organization)
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
    except Exception as e:
        log(f"Error applying registry changes: {e}")

def replace_command_in_script(script_path, old_command, new_command):
    with open(script_path, "r") as file:
        lines = file.readlines()
    
    for i, line in enumerate(lines):
        if old_command in line:
            lines[i] = new_command + "\n"
            break
    
    with open(script_path, "w") as file:
        file.writelines(lines)

def run_registrytweak():
    log("Starting registry tweaks...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/12%20Registry.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Registry.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def install_timerresolution():
    log("Starting installation of Timer Resolution...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/10%20Timer%20Resolution.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "TimerResolution.ps1")
        log(f"Attempting to download timer script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("timer script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Timer Resolution installed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Timer Resolution installation failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during installation of Timer Resolution: {str(e)}")
        return False

def run_startmenuoptimization():
    log("Starting start menu tweaks...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/1%20Start%20Menu%20Taskbar.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Startmenu.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False
    
def run_autoruns():
    log("Starting start menu tweaks...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/21%20Autoruns.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Autoruns.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
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
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def run_backgroundapps():
    log("Starting start menu tweaks...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/3%20Setup/9%20Background%20Apps.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "BackgroundApps.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False
    
def run_copilotuninstaller():
    log("Starting copilot uninstaller...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/3%20Copilot.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "copilotuninstaller.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def run_widgetsuninstaller():
    log("Starting widget uninstaller...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/4%20Widgets.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "widgetsuninstaller.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def run_gamebaroptimization():
    log("Starting gamebar optimization...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/6%20Gamebar.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "gamebar.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def apply_powerplan():
    log("Starting power plan optimization...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/9%20Power%20Plan.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "powerplan.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def apply_signoutlockscreen():
    log("Starting signout lockscreen optimization...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/13%20Signout%20Lockscreen.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "lockscreensignout.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def run_edgeuninstaller():
    log("Starting edge uninstaller...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/14%20Edge.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "edgeuninstaller.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def apply_networkoptimization():
    log("Starting network optimization...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/8%20Advanced/1%20Network%20Adapter.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "networkoptimization.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def apply_msimode():
    log("Starting MSI mode optimization...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/5%20Graphics/9%20Msi%20Mode.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "msimode.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
        log(f"Target script path: {script_path}")
        
        response = requests.get(script_url)
        log(f"Download response status code: {response.status_code}")
        
        with open(script_path, "wb") as file:
            file.write(response.content)
        log("tweak script successfully saved to disk")
        
        # Reemplazar el comando de Read-Host con una asignación directa
        old_command = '$choice = Read-Host " "'
        new_command = '$choice = 1'
        replace_command_in_script(script_path, old_command, new_command)
        log("Command replaced in the script")
        
        powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
        log(f"Executing PowerShell command: {powershell_command}")
        
        process = subprocess.run(
            ["powershell", "-Command", powershell_command],
            capture_output=True,
            text=True
        )
        
        if process.returncode == 0:
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def run_directxinstallation():
    log("Starting DirectX installation...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/5%20Graphics/10%20Direct%20X.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "directx.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
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
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False

def run_cinstallation():
    log("Starting c++ installation...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/5%20Graphics/11%20C%2B%2B.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "c++.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
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
            log("Registry tweak completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Registry tweak failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False
                   
def finalize_installation():
    log("Clean up...")
    try:
        script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/refs/heads/main/6%20Windows/22%20Cleanup.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Cleanup.ps1")
        log(f"Attempting to download tweak script from: {script_url}")
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
            log("Clean up completed successfully")
            log(f"Process stdout: {process.stdout}")
        else:
            log(f"Clean up failed with return code: {process.returncode}")
            log(f"Process stderr: {process.stderr}")
            log(f"Process stdout: {process.stdout}")
            
    except Exception as e:
        log(f"Unexpected error during registry tweak: {str(e)}")
        return False
    
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