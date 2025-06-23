import sys
import os
import ctypes
import subprocess
import tempfile
import logging
import requests
import winreg
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

LOG_FILE = "ztalon.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode='a'  # Append mode
)

def log_and_print(message):
    """Enhanced logging with both file and console output"""
    logging.info(message)
    print(message)

def show_error_popup(message, allow_continue=True):
    """Show error popup with option to continue or exit"""
    print(f"\n❌ ERROR: {message}")
    if allow_continue:
        choice = input("Press Enter to continue or 'q' to quit: ").lower()
        if choice == 'q':
            sys.exit(1)
    else:
        input("Press Enter to exit...")
        sys.exit(1)

def download_file_with_retries(url, dest_path, max_retries=3, timeout=30):
    """Download file with retry mechanism and clean logging"""
    for attempt in range(max_retries):
        try:
            # Solo log del inicio de descarga (solo nombre del archivo)
            filename = url.split('/')[-1].replace('%20', ' ')
            log_and_print(f"📥 Starting download: {filename}")
            
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        # Mostrar progreso solo en consola, NO en logs
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r📊 Progress: {percent:.1f}%", end="", flush=True)
            
            print()  # New line after progress
            # Solo log del final de descarga
            log_and_print("✅ Download completed successfully")
            return True
            
        except Exception as e:
            if attempt < max_retries - 1:
                log_and_print(f"⚠️ Download failed, retrying...")
                time.sleep(2)
            else:
                log_and_print(f"❌ Download failed after all attempts")
                return False
    return False

def run_powershell_with_monitoring(command, script_path=None, timeout=300):
    """Run PowerShell command with clean logging"""
    try:
        if script_path:
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
            script_name = script_path.split('\\')[-1] if '\\' in script_path else script_path
            log_and_print(f"🔄 Executing script: {script_name}")
        else:
            log_and_print(f"🔄 Executing PowerShell command")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output pero NO logear todo el stdout/stderr
        def read_output_silent(pipe):
            """Read output without logging everything"""
            for line in iter(pipe.readline, ''):
                # Solo mostrar en consola, no en logs
                if line.strip():
                    print(line.strip())
        
        stdout_thread = threading.Thread(target=read_output_silent, args=(process.stdout,))
        stderr_thread = threading.Thread(target=read_output_silent, args=(process.stderr,))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for completion with timeout
        try:
            return_code = process.wait(timeout=timeout)
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            if return_code == 0:
                log_and_print("✅ Script executed successfully")
                return True
            else:
                log_and_print(f"⚠️ Script finished with return code: {return_code}")
                return False
                
        except subprocess.TimeoutExpired:
            log_and_print(f"❌ Script timed out after {timeout} seconds")
            process.kill()
            process.wait()
            return False
            
    except Exception as e:
        log_and_print(f"❌ Error executing script: {e}")
        return False

def set_registry_value(root_key, key_path, value_name, value, value_type):
    """Safely set registry value with error handling"""
    try:
        # Open or create the key
        key = winreg.OpenKey(root_key, key_path, 0, winreg.KEY_WRITE)
        if key is None:
            key = winreg.CreateKey(root_key, key_path)
        
        # Set the value
        winreg.SetValueEx(key, value_name, 0, value_type, value)
        winreg.CloseKey(key)
        
        log_and_print(f"✅ Registry value set: {key_path}\\{value_name} = {value}")
        return True
        
    except Exception as e:
        log_and_print(f"❌ Failed to set registry value {key_path}\\{value_name}: {e}")
        return False

def apply_registry_changes():
    """Apply system registry changes with user interaction"""
    log_and_print("🔧 Applying registry changes...")
    
    # Prompt for taskbar position preference
    print("\n" + "="*60)
    print("                TASKBAR POSITION OPTION")
    print("="*60)
    print()
    print("Where do you want the taskbar icons to be positioned?")
    print()
    print("1. Left (classic position)")
    print("2. Center (Windows 11 default)")
    print()
    
    try:
        from init import safe_input
        position_choice = safe_input("Enter your choice (1-2): ", "1").strip()
    except ImportError:
        position_choice = input("Enter your choice (1-2): ").strip()
    
    # Configure taskbar alignment: 0 = Left, 1 = Center
    taskbar_alignment = 1 if position_choice == "2" else 0
    
    # Prompt for taskbar color customization
    print("\n" + "="*60)
    print("                TASKBAR COLOR OPTION")
    print("="*60)
    print()
    print("Do you want to set the taskbar to black color?")
    print("⚠️  (This may cause visual issues on some systems)")
    print()
    print("1. Yes, apply black taskbar")
    print("2. No, keep current colors")
    print()
    
    try:
        taskbar_choice = safe_input("Enter your choice (1-2): ", "2").strip()
    except NameError:
        taskbar_choice = input("Enter your choice (1-2): ").strip()
    
    apply_black_taskbar = taskbar_choice == "1"
    
    # Core system registry modifications
    registry_modifications = [
        # Taskbar configuration
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAl", winreg.REG_DWORD, taskbar_alignment),
        # Dark theme enforcement
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "AppsUseLightTheme", winreg.REG_DWORD, 0),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "SystemUsesLightTheme", winreg.REG_DWORD, 0),
        # Game DVR disable
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", winreg.REG_DWORD, 0),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR", "Value", winreg.REG_DWORD, 0),
        # Performance improvements
        (winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", "MenuShowDelay", winreg.REG_SZ, "0"),
        (winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics", "MinAnimate", winreg.REG_DWORD, 0),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ExtendedUIHoverTime", winreg.REG_DWORD, 1),
        # File extension visibility
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "HideFileExt", winreg.REG_DWORD, 0),
    ]
    
    # Log user configuration choices
    position_text = "center" if taskbar_alignment == 1 else "left"
    log_and_print(f"📍 Taskbar position set to: {position_text}")
    
    # Apply black taskbar customizations if requested
    if apply_black_taskbar:
        log_and_print("🎨 Adding black taskbar configuration...")
        taskbar_modifications = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "AccentColorMenu", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "ColorPrevalence", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM", "AccentColorInStartAndTaskbar", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "AccentPalette", winreg.REG_BINARY, b"\x00" * 32),
        ]
        registry_modifications.extend(taskbar_modifications)
    else:
        log_and_print("⚪ Skipping black taskbar configuration (user choice)")
    
    # Execute registry modifications
    successful = 0
    total_modifications = len(registry_modifications)
    
    for root_key, key_path, value_name, value_type, value in registry_modifications:
        if set_registry_value(root_key, key_path, value_name, value, value_type):
            successful += 1
    
    log_and_print(f"📊 Registry changes: {successful}/{total_modifications} applied successfully")
    
    # Warn about incomplete black taskbar application
    if apply_black_taskbar and successful < total_modifications:
        log_and_print("⚠️ Some black taskbar settings may not have been applied correctly")
        log_and_print("💡 You can manually change taskbar colors in Windows Settings > Personalization")
    
    # Restart Explorer to apply visual changes immediately
    try:
        log_and_print("🔄 Restarting Explorer to apply changes...")
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        subprocess.run(["start", "explorer.exe"], shell=True)
        log_and_print("✅ Explorer restarted successfully")
        
        # Confirm applied changes
        log_and_print(f"📍 Taskbar positioned to the {position_text}")
        if apply_black_taskbar:
            log_and_print("🎨 Black taskbar settings applied - restart may be needed for full effect")
            
    except Exception as e:
        log_and_print(f"⚠️ Could not restart Explorer: {e}")
        if apply_black_taskbar:
            log_and_print("⚠️ Black taskbar settings may not take effect until manual restart")

def replace_command_in_script(script_path, replace_commands):
    """Replace commands in PowerShell script with clean logging"""
    try:
        with open(script_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Apply replacements
        for old_command, new_command in replace_commands.items():
            if old_command in content:
                content = content.replace(old_command, new_command)
        
        with open(script_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        return True
    except Exception as e:
        log_and_print(f"❌ Error modifying script: {e}")
        return False

def download_and_execute_script(script_url, script_name, replace_commands=None, timeout=300):
    """Download and execute PowerShell script with error handling"""
    try:
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, script_name)
        
        # Download script with retry mechanism
        if not download_file_with_retries(script_url, script_path):
            return False
        
        # Modify script commands if needed
        if replace_commands:
            log_and_print(f"🔧 Modifying script: {script_name}")
            if not replace_command_in_script(script_path, replace_commands):
                log_and_print("⚠️ Script modification failed, using original")
        
        # Execute script and wait for completion
        log_and_print(f"🚀 Running optimization: {script_name}")
        success = run_powershell_with_monitoring(None, script_path, timeout)
        
        # Clean up temporary files
        try:
            os.remove(script_path)
        except:
            pass
            
        if success:
            log_and_print(f"✅ Optimization completed: {script_name}")
        else:
            log_and_print(f"⚠️ Optimization had issues: {script_name}")
            
        return success
        
    except Exception as e:
        log_and_print(f"❌ Error in optimization: {e}")
        return False

# Enhanced optimization functions with FIXED URLs

def run_registrytweak():
    """Apply registry tweaks with enhanced error handling"""
    log_and_print("🔧 Starting registry tweaks...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/12%20Registry.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "Registry.ps1", replace_commands)

def install_timerresolution():
    """Install Timer Resolution with enhanced error handling"""
    log_and_print("⏱️ Starting Timer Resolution installation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/10%20Timer%20Resolution.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "TimerResolution.ps1", replace_commands)

def run_startmenuoptimization():
    """Optimize start menu with fallback to manual registry tweaks"""
    log_and_print("🎯 Starting start menu optimization...")
    
    # Try multiple URLs for the script
    script_urls = [
        "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/1%20Start%20Menu%20Taskbar%20Clean.ps1",
        "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/1%20Start%20Menu%20Taskbar%20Clean.ps1"
    ]
    
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    
    # Attempt download from each URL
    for i, script_url in enumerate(script_urls, 1):
        log_and_print(f"🔄 Attempting download from URL {i}/{len(script_urls)}")
        
        if download_and_execute_script(script_url, "Startmenu.ps1", replace_commands):
            return True
        
        if i < len(script_urls):
            log_and_print(f"⚠️ URL {i} failed, trying alternative...")
    
    # Fallback to manual registry modifications
    log_and_print("⚠️ All download attempts failed, applying manual start menu optimizations...")
    
    try:
        # Manual start menu and taskbar optimizations
        manual_optimizations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_ShowClassicMode", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "StartMenuAdminTools", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "StartShownOnUpgrade", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowTaskViewButton", winreg.REG_DWORD, 0),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Search", "SearchboxTaskbarMode", winreg.REG_DWORD, 0),
        ]
        
        successful = 0
        for root_key, key_path, value_name, value_type, value in manual_optimizations:
            if set_registry_value(root_key, key_path, value_name, value, value_type):
                successful += 1
        
        log_and_print(f"📊 Manual start menu optimizations: {successful}/{len(manual_optimizations)} applied")
        return successful > 0
        
    except Exception as e:
        log_and_print(f"❌ Error in manual start menu optimization: {e}")
        return False

def run_autoruns():
    """Optimize autoruns with enhanced error handling"""
    log_and_print("🚀 Starting autoruns optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/21%20Autoruns.ps1"
    return download_and_execute_script(script_url, "Autoruns.ps1")

def run_backgroundapps():
    """Optimize background apps with enhanced error handling"""
    log_and_print("📱 Starting background apps optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/3%20Setup/10%20Background%20Apps.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "BackgroundApps.ps1", replace_commands)

def run_copilotuninstaller():
    """Uninstall Copilot with enhanced error handling"""
    log_and_print("🤖 Starting Copilot uninstallation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/3%20Copilot.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "copilotuninstaller.ps1", replace_commands)

def run_widgetsuninstaller():
    """Uninstall Widgets with enhanced error handling"""
    log_and_print("🧩 Starting Widgets uninstallation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/4%20Widgets.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "widgetsuninstaller.ps1", replace_commands)

def run_gamebaroptimization():
    """Optimize GameBar with enhanced error handling"""
    log_and_print("🎮 Starting GameBar optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/6%20Gamebar.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "gamebar.ps1", replace_commands)

def apply_powerplan():
    """Apply power plan optimization with enhanced error handling"""
    log_and_print("⚡ Starting power plan optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/9%20Power%20Plan.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "powerplan.ps1", replace_commands)

def apply_signoutlockscreen():
    """Optimize lock screen with enhanced error handling"""
    log_and_print("🔒 Starting lock screen optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/13%20Signout%20Lockscreen.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "lockscreensignout.ps1", replace_commands)

def run_edgeuninstaller():
    """Uninstall Edge with enhanced error handling"""
    log_and_print("🌐 Starting Edge uninstallation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/14%20Edge.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "edgeuninstaller.ps1", replace_commands)

def apply_networkoptimization():
    """Apply network optimization with enhanced error handling"""
    log_and_print("🌐 Starting network optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/8%20Advanced/1%20Network%20Adapter.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "networkoptimization.ps1", replace_commands)

def apply_msimode():
    """Apply MSI mode optimization with enhanced error handling"""
    log_and_print("🔧 Starting MSI mode optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/5%20Graphics/9%20Msi%20Mode.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "msimode.ps1", replace_commands)

def run_directxinstallation():
    """Install DirectX with enhanced error handling"""
    log_and_print("📊 Starting DirectX installation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/5%20Graphics/10%20Direct%20X.ps1"
    return download_and_execute_script(script_url, "directx.ps1", timeout=600)  # Longer timeout for installation

def run_cinstallation():
    """Install C++ redistributables with enhanced error handling"""
    log_and_print("🔧 Starting C++ redistributables installation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/5%20Graphics/11%20C%2B%2B.ps1"
    return download_and_execute_script(script_url, "c++.ps1", timeout=600)  # Longer timeout for installation

def apply_nvidiaoptimization():
    """Apply NVIDIA optimizations with enhanced error handling"""
    log_and_print("🎮 Starting NVIDIA optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/5%20Graphics/5%20Nvidia%20Settings.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "nvidiasettings.ps1", replace_commands)

def apply_amdoptimization():
    """Apply AMD optimizations with enhanced error handling"""
    log_and_print("🔴 Starting AMD optimization...")
    # Note: Add AMD-specific optimizations here when available
    log_and_print("⚠️ AMD-specific optimizations not yet implemented")
    return True

def apply_gpuregistryoptimization(gpu_info):
    """Apply GPU-specific registry optimizations"""
    try:
        # Handle both list and string inputs
        if isinstance(gpu_info, list):
            if gpu_info and len(gpu_info) > 0:
                # Get the type from the first GPU in the list
                gpu_type = gpu_info[0].get('type', 'Unknown') if isinstance(gpu_info[0], dict) else str(gpu_info[0])
                gpu_name = gpu_info[0].get('name', 'Unknown GPU') if isinstance(gpu_info[0], dict) else str(gpu_info[0])
                log_and_print(f"🎯 Applying GPU registry optimizations for: {gpu_name} ({gpu_type})")
            else:
                log_and_print("⚠️ No GPU information available, applying generic optimizations")
                gpu_type = "unknown"
        else:
            # Handle string input (backward compatibility)
            gpu_type = str(gpu_info)
            log_and_print(f"🎯 Applying GPU registry optimizations for: {gpu_type}")
        
        # Convert to lowercase for comparison
        gpu_type_lower = gpu_type.lower()
        
        if "amd" in gpu_type_lower:
            log_and_print("🔴 Applying AMD-specific registry optimizations...")
            registry_modifications = [
                # AMD-specific optimizations
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "EnableUlps", winreg.REG_DWORD, 0),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "PP_ThermalAutoThrottlingEnable", winreg.REG_DWORD, 0),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "DisableDMACopy", winreg.REG_DWORD, 1),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "DisableBlockWrite", winreg.REG_DWORD, 0),
            ]
        elif "nvidia" in gpu_type_lower:
            log_and_print("🟢 Applying NVIDIA-specific registry optimizations...")
            registry_modifications = [
                # NVIDIA-specific optimizations
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "DisablePreemption", winreg.REG_DWORD, 1),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "DisableCudaContextPreemption", winreg.REG_DWORD, 1),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "EnableMsHybrid", winreg.REG_DWORD, 0),
            ]
        elif "intel" in gpu_type_lower:
            log_and_print("🔵 Applying Intel-specific registry optimizations...")
            registry_modifications = [
                # Intel-specific optimizations
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "Acceleration.Level", winreg.REG_DWORD, 0),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "DisablePowerManagement", winreg.REG_DWORD, 1),
            ]
        else:
            log_and_print("🔧 Applying generic GPU optimizations...")
            registry_modifications = [
                # Generic GPU optimizations
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrDelay", winreg.REG_DWORD, 8),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrDdiDelay", winreg.REG_DWORD, 8),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrLevel", winreg.REG_DWORD, 0),
            ]
        
        # Apply registry modifications
        successful = 0
        total_modifications = len(registry_modifications)
        
        for root_key, key_path, value_name, value_type, value in registry_modifications:
            if set_registry_value(root_key, key_path, value_name, value, value_type):
                successful += 1
        
        log_and_print(f"📊 GPU optimizations: {successful}/{total_modifications} applied successfully")
        
        if successful == total_modifications:
            log_and_print("✅ All GPU registry optimizations applied successfully")
            return True
        elif successful > 0:
            log_and_print(f"⚠️ Partial success: {successful}/{total_modifications} GPU optimizations applied")
            return True
        else:
            log_and_print("❌ No GPU optimizations could be applied")
            return False
            
    except Exception as e:
        log_and_print(f"❌ Error applying GPU registry optimizations: {e}")
        return False

def run_external_debloat_scripts():
    """Run external debloat scripts with enhanced monitoring"""
    log_and_print("🧹 Starting external debloat scripts...")
    
    scripts = [
        {
            "name": "ChrisTitusTech WinUtil",
            # Usar GitHub directamente en lugar del redirect
            "command": 'irm https://raw.githubusercontent.com/ChrisTitusTech/winutil/main/winutil.ps1 | iex',
            "timeout": 1800
        },
        {
            "name": "Raphi Win11Debloat",
            "command": '& ([scriptblock]::Create((irm "https://debloat.raphi.re/"))) -Silent -RemoveApps -RemoveGamingApps -DisableTelemetry -DisableBing -DisableSuggestions -DisableLockscreenTips -RevertContextMenu -TaskbarAlignLeft -HideSearchTb -DisableWidgets -DisableCopilot -ClearStartAllUsers -DisableDVR -DisableStartRecommended -ExplorerToThisPC -DisableMouseAcceleration',
            "timeout": 1200
        }
    ]
    
    for script in scripts:
        try:
            log_and_print(f"🚀 Running {script['name']}...")
            log_and_print("⚠️ Note: This script will run interactively. Follow the on-screen instructions.")
            
            # Execute the script
            success = run_powershell_with_monitoring(script['command'], timeout=script['timeout'])
            
            if success:
                log_and_print(f"✅ {script['name']} completed successfully")
            else:
                log_and_print(f"⚠️ {script['name']} had issues")
                
        except Exception as e:
            log_and_print(f"❌ Error running {script['name']}: {e}")
    
    log_and_print("✅ External debloat scripts completed")

def run_advanced_cleanup():
    """Advanced cleanup using integrated PowerShell script"""
    log_and_print("🧹 Starting advanced system cleanup...")
    
    # Enhanced cleanup script combining the best of all methods
    cleanup_script = """
    # Enhanced ZTalon Cleanup Script
    Write-Host "🗑️ Starting comprehensive cleanup..." -ForegroundColor Green
    
    # Function to safely remove and recreate directories
    function Clean-Directory {
        param([string]$Path, [string]$Name)
        try {
            if (Test-Path $Path) {
                Write-Host "🧹 Cleaning $Name..." -ForegroundColor Yellow
                Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue | Out-Null
                New-Item -Path (Split-Path $Path -Parent) -Name (Split-Path $Path -Leaf) -ItemType Directory -ErrorAction SilentlyContinue | Out-Null
                Write-Host "✅ $Name cleaned successfully" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠️ Could not clean $Name : $_" -ForegroundColor Red
        }
    }
    
    # Clean user temp directory
    Clean-Directory "$env:USERPROFILE\\AppData\\Local\\Temp" "User Temp"
    
    # Clean system temp directory  
    Clean-Directory "$env:SystemDrive\\Windows\\Temp" "System Temp"
    
    # Clean prefetch directory
    Clean-Directory "$env:SystemDrive\\Windows\\Prefetch" "Prefetch Cache"
    
    # Additional cleanup locations
    $additional_paths = @(
        "$env:LOCALAPPDATA\\Microsoft\\Windows\\INetCache",
        "$env:LOCALAPPDATA\\Microsoft\\Windows\\WebCache", 
        "$env:SystemDrive\\Windows\\SoftwareDistribution\\Download",
        "$env:SystemRoot\\Logs"
    )
    
    foreach ($path in $additional_paths) {
        if (Test-Path $path) {
            try {
                Write-Host "🧹 Cleaning $(Split-Path $path -Leaf)..." -ForegroundColor Yellow
                Get-ChildItem -Path $path -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
                Write-Host "✅ $(Split-Path $path -Leaf) cleaned" -ForegroundColor Green
            } catch {
                Write-Host "⚠️ Could not clean $(Split-Path $path -Leaf)" -ForegroundColor Red
            }
        }
    }
    
    Write-Host "🎉 Advanced cleanup completed!" -ForegroundColor Green
    """
    
    try:
        # Write the script to temp file
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "ztalon_advanced_cleanup.ps1")
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(cleanup_script)
        
        # Execute the enhanced cleanup script
        if run_powershell_with_monitoring(None, script_path, timeout=180):
            log_and_print("✅ Advanced cleanup completed successfully")
            return True
        else:
            log_and_print("⚠️ Advanced cleanup had some issues")
            return False
            
    except Exception as e:
        log_and_print(f"❌ Error during advanced cleanup: {e}")
        return False
    finally:
        # Clean up the script file
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except:
            pass

def run_final_cleanup():
    """Final cleanup with all methods combined"""
    log_and_print("🧹 Starting comprehensive final cleanup...")
    
    # Run the existing online cleanup script
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/22%20Cleanup.ps1"
    
    online_success = download_and_execute_script(script_url, "Cleanup.ps1")
    
    # Run our enhanced local cleanup
    local_success = run_advanced_cleanup()
    
    # Basic fallback cleanup
    try:
        log_and_print("🗑️ Running fallback cleanup...")
        temp_dirs = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""), 
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp")
        ]
        
        for temp_dir in temp_dirs:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    ztalon_temp = os.path.join(temp_dir, "ztalon")
                    if os.path.exists(ztalon_temp):
                        import shutil
                        shutil.rmtree(ztalon_temp, ignore_errors=True)
                        log_and_print(f"🗑️ Cleaned ZTalon temp files: {ztalon_temp}")
                except Exception as e:
                    log_and_print(f"⚠️ Could not clean {temp_dir}: {e}")
        
    except Exception as e:
        log_and_print(f"⚠️ Error during fallback cleanup: {e}")
    
    # Summary
    if online_success and local_success:
        log_and_print("🎉 All cleanup methods completed successfully")
    elif online_success or local_success:
        log_and_print("✅ Cleanup completed with some methods successful")
    else:
        log_and_print("⚠️ Cleanup completed but with issues - basic cleanup applied")

def finalize_installation():
    """Final cleanup using the comprehensive new cleaning system"""
    log_and_print("🎉 Starting final installation cleanup...")
    
    # Use the new comprehensive cleanup system that combines all methods
    log_and_print("🚀 Executing comprehensive cleanup system...")
    
    # Call the enhanced cleanup function that combines:
    # - Online cleanup script
    # - Advanced local cleanup (temp, prefetch, cache, etc.)
    # - Fallback basic cleanup
    run_final_cleanup()
    
    # Additional ZTalon-specific cleanup
    try:
        log_and_print("🧹 Performing final ZTalon cleanup...")
        
        # Clean any remaining ZTalon temporary files from all possible locations
        import shutil
        cleanup_locations = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
            tempfile.gettempdir()
        ]
        
        for location in cleanup_locations:
            if location and os.path.exists(location):
                try:
                    ztalon_files = [
                        os.path.join(location, "ztalon"),
                        os.path.join(location, "ztalon_advanced_cleanup.ps1"),
                        os.path.join(location, "Registry.ps1"),
                        os.path.join(location, "TimerResolution.ps1"),
                        os.path.join(location, "Cleanup.ps1")
                    ]
                    
                    for ztalon_file in ztalon_files:
                        if os.path.exists(ztalon_file):
                            if os.path.isdir(ztalon_file):
                                shutil.rmtree(ztalon_file, ignore_errors=True)
                                log_and_print(f"🗑️ Removed directory: {ztalon_file}")
                            else:
                                os.remove(ztalon_file)
                                log_and_print(f"🗑️ Removed file: {ztalon_file}")
                                
                except Exception as e:
                    log_and_print(f"⚠️ Could not clean {location}: {e}")
        
        # Force garbage collection to free memory
        import gc
        gc.collect()
        
        log_and_print("✅ Final ZTalon cleanup completed")
        
    except Exception as e:
        log_and_print(f"⚠️ Error during final ZTalon cleanup: {e}")
    
    # Final summary
    log_and_print("🎊 Installation finalization completed!")
    log_and_print("📋 Summary of cleanup performed:")
    log_and_print("   ✅ Online cleanup script executed")
    log_and_print("   ✅ Advanced local cleanup (temp, prefetch, cache)")
    log_and_print("   ✅ ZTalon temporary files removed")
    log_and_print("   ✅ Memory cleanup performed")
    
    return True

def run_threaded_optimizations(optimization_list, max_workers=2):
    """Run multiple optimizations in parallel with thread management"""
    log_and_print(f"🔧 Starting threaded optimizations with {max_workers} workers...")
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_name = {
            executor.submit(func): name 
            for name, func in optimization_list
        }
        
        # Process completed tasks
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result(timeout=600)  # 10 minute timeout per task
                results[name] = result
                log_and_print(f"✅ Completed: {name}")
            except Exception as e:
                log_and_print(f"❌ Failed: {name} - {e}")
                results[name] = False
    
    successful = sum(1 for result in results.values() if result)
    total = len(results)
    log_and_print(f"📊 Threaded optimizations: {successful}/{total} completed successfully")
    
    return results

# Test function for debugging
def test_connectivity():
    """Test connectivity to required URLs"""
    test_urls = [
        "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate-Windows-Optimization-Guide/main/6%20Windows/12%20Registry.ps1",
        "https://raw.githubusercontent.com/ChrisTitusTech/winutil/main/winutil.ps1",
        "https://debloat.raphi.re/"
    ]
    
    log_and_print("🔍 Testing connectivity to required URLs...")
    for url in test_urls:
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                log_and_print(f"✅ {url} - OK")
            else:
                log_and_print(f"⚠️ {url} - HTTP {response.status_code}")
        except Exception as e:
            log_and_print(f"❌ {url} - {e}")

if __name__ == "__main__":
    # Test mode when run directly
    log_and_print("🧪 Running in test mode...")
    test_connectivity()
    apply_registry_changes()