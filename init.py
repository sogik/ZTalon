import sys
import os
import ctypes
import subprocess
import threading
import logging
import debloat_windows
import time
import platform
import winreg
import app_install

LOG_FILE = "ztalon.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode='w'
)

def log_and_print(message):
    """Function to log and display in console"""
    logging.info(message)
    print(message)

def pause_and_continue(message="Press Enter to continue..."):
    """Pauses the program until the user presses Enter (ALWAYS)"""
    print(f"\n{message}")
    input()

def clear_screen():
    """Clears the screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_menu():
    """Shows the main menu"""
    clear_screen()
    print("=" * 60)
    print("              ZTALON - WINDOWS OPTIMIZER")
    print("=" * 60)
    print()
    print("What would you like to do?")
    print()
    print("1. Install applications + Optimize system")
    print("2. Only optimize system (without installing apps)")
    print("3. View system information")
    print("4. Exit")
    print()
    print("=" * 60)

def get_user_choice():
    """Gets user choice with validation"""
    while True:
        show_menu()
        choice = input("Enter your option (1-4): ").strip()
        
        if choice == "1":
            return "install"
        elif choice == "2":
            return "optimize"
        elif choice == "3":
            return "info"
        elif choice == "4":
            return "exit"
        else:
            print("\n❌ Invalid option. Please choose an option from 1 to 4.")
            pause_and_continue()

def show_app_install_menu():
    """Shows the application installation menu"""
    clear_screen()
    print("=" * 70)
    print("                APPLICATION INSTALLER")
    print("=" * 70)
    print()
    print("The application installer will be downloaded and executed.")
    print("You'll be able to select which programs to install from a list that includes:")
    print()
    print("📦 Utilities:")
    print("   • 7-Zip - File compressor")
    print("   • Notepad++ - Advanced text editor")
    print()
    print("🎮 Games and Launchers:")
    print("   • Discord - Chat for gamers")
    print("   • OBS Studio - Recording and streaming")
    print("   • Roblox, Valorant, League of Legends")
    print("   • Escape From Tarkov")
    print()
    print("🌐 Browsers:")
    print("   • Chrome, Firefox, Edge")
    print()
    print("🎵 Multimedia:")
    print("   • Spotify - Streaming music")
    print()
    print("💼 Office:")
    print("   • Microsoft Office 2024 LSTC Edition")
    print()
    print("Do you want to continue with the application installation?")
    print()
    print("1. Yes, install applications")
    print("2. No, only optimize system")
    print()
    print("=" * 70)
    
    while True:
        choice = input("Enter your option (1-2): ").strip()
        if choice == "1":
            return True
        elif choice == "2":
            return False
        else:
            print("❌ Invalid option. Please choose 1 or 2.")

def show_optimization_menu():
    """Shows available optimization options"""
    optimizations = [
        ("GPU registry optimization", "GPU registry optimization"),
        ("DirectX installation", "DirectX installation"),
        ("C++ installation", "C++ installation"),
        ("Start menu optimization", "Start menu optimization"),
        ("Uninstall Copilot", "Copilot uninstaller"),
        ("Uninstall Widgets", "Widgets uninstaller"),
        ("GameBar optimization", "Gamebar optimization"),
        ("Configure power plan", "Power plan"),
        ("Install Timer Resolution", "Timer Resolution installation"),
        ("Registry tweaks", "Registry tweaks"),
        ("Registry changes", "Registry changes"),
        ("Lock screen optimization", "Signout lockscreen optimization"),
        ("Uninstall Edge", "Edge uninstaller"),
        ("Background apps optimization", "Background apps optimization"),
        ("Autoruns optimization", "Autoruns optimization"),
        ("Network optimization", "Network optimization")
    ]
    
    clear_screen()
    print("=" * 70)
    print("                    AVAILABLE OPTIMIZATIONS")
    print("=" * 70)
    print()
    
    for i, (english, _) in enumerate(optimizations, 1):
        print(f"{i:2d}. {english}")
    
    print()
    print("a. All optimizations (INTERACTIVE)")
    print("s. Select specific optimizations")
    print("c. Cancel")
    print()
    print("=" * 70)
    
    return optimizations

def is_running_as_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logging.error(f"Error checking admin privileges: {e}")
        return False

def get_gpu_info_advanced():
    """Get GPU information using multiple methods"""
    try:
        gpu_info = []
        
        # Method 1: PowerShell with Get-CimInstance (more modern)
        try:
            log_and_print("🔍 Detecting GPU with PowerShell...")
            ps_script = """
            $gpus = Get-CimInstance -ClassName Win32_VideoController
            foreach ($gpu in $gpus) {
                if ($gpu.Name -and $gpu.Name -notlike "*Basic*" -and $gpu.Name -notlike "*Generic*") {
                    $output = @{
                        Name = $gpu.Name
                        DriverVersion = $gpu.DriverVersion
                        AdapterRAM = $gpu.AdapterRAM
                        PNPDeviceID = $gpu.PNPDeviceID
                    }
                    $output | ConvertTo-Json
                    Write-Output "---SEPARATOR---"
                }
            }
            """
            
            result = subprocess.run([
                'powershell', '-Command', ps_script
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout:
                import json
                gpu_blocks = result.stdout.split("---SEPARATOR---")
                
                for block in gpu_blocks:
                    block = block.strip()
                    if block:
                        try:
                            gpu_data = json.loads(block)
                            name = gpu_data.get('Name', '').strip()
                            driver_version = gpu_data.get('DriverVersion', 'Unknown')
                            
                            if name:
                                gpu_type = detect_gpu_type(name)
                                gpu_info.append({
                                    'name': name,
                                    'driver_version': driver_version,
                                    'type': gpu_type
                                })
                                log_and_print(f"✅ GPU detected: {name} ({gpu_type})")
                        except:
                            continue
        except Exception as e:
            log_and_print(f"⚠️ PowerShell method failed: {e}")
        
        return gpu_info
        
    except Exception as e:
        log_and_print(f"❌ General error detecting GPU: {e}")
        return []

def detect_gpu_type(gpu_name):
    """Detects GPU type based on name"""
    name_upper = gpu_name.upper()
    
    nvidia_keywords = ['NVIDIA', 'GEFORCE', 'RTX', 'GTX', 'QUADRO', 'TESLA']
    amd_keywords = ['AMD', 'RADEON', 'RX ', 'VEGA', 'NAVI', 'RDNA']
    intel_keywords = ['INTEL', 'UHD', 'IRIS', 'ARC']
    
    for keyword in nvidia_keywords:
        if keyword in name_upper:
            return 'NVIDIA'
    
    for keyword in amd_keywords:
        if keyword in name_upper:
            return 'AMD'
    
    for keyword in intel_keywords:
        if keyword in name_upper:
            return 'INTEL'
    
    return 'Unknown'

def get_real_windows_version():
    """Gets the real Windows version"""
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        
        try:
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            build_number, _ = winreg.QueryValueEx(key, "CurrentBuildNumber")
            display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            
            build_num = int(build_number)
            
            if build_num >= 22000:
                if "Pro" in product_name:
                    real_product_name = "Windows 11 Pro"
                elif "Home" in product_name:
                    real_product_name = "Windows 11 Home"
                elif "Enterprise" in product_name:
                    real_product_name = "Windows 11 Enterprise"
                else:
                    real_product_name = "Windows 11"
            else:
                real_product_name = product_name
            
            winreg.CloseKey(key)
            winreg.CloseKey(reg)
            
            return {
                'product_name': real_product_name,
                'build': build_number,
                'display_version': display_version
            }
            
        except Exception as e:
            winreg.CloseKey(key)
            winreg.CloseKey(reg)
            raise e
            
    except Exception as e:
        log_and_print(f"Error getting Windows version: {e}")
        return None

def get_windows_info():
    try:
        windows_version = platform.win32_ver()
        
        real_version_info = get_real_windows_version()
        
        if real_version_info:
            product_name = real_version_info['product_name']
            build_number = real_version_info['build']
            display_version = real_version_info['display_version']
        else:
            reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
            key = winreg.OpenKey(reg, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            
            build_number = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
            product_name = winreg.QueryValueEx(key, "ProductName")[0]
            display_version = winreg.QueryValueEx(key, "DisplayVersion")[0]
            
            winreg.CloseKey(key)
            winreg.CloseKey(reg)
        
        gpu_info = get_gpu_info_advanced()
        
        return {
            'version': windows_version[0],
            'build': build_number,
            'product_name': product_name,
            'display_version': display_version,
            'gpu_info': gpu_info
        }
    except Exception as e:
        logging.error(f"Error getting Windows information: {e}")
        return None

def show_system_info(windows_info, gputype):
    """Shows detailed system information"""
    clear_screen()
    print("=" * 60)
    print("                SYSTEM INFORMATION")
    print("=" * 60)
    print()
    
    if windows_info:
        print(f"📟 Operating System: {windows_info['product_name']}")
        print(f"🔢 Build Number: {windows_info['build']}")
        print(f"📋 Version: {windows_info['display_version']}")
        print()
        print("🎮 GPU Information:")
        
        if windows_info['gpu_info']:
            for i, gpu in enumerate(windows_info['gpu_info'], 1):
                print(f"   GPU {i}: {gpu['name']}")
                print(f"          Driver Version: {gpu['driver_version']}")
                print(f"          Type: {gpu['type']}")
                print()
        else:
            print("   ❌ Could not detect GPU information")
        
        print(f"🎯 GPU detected for optimization: {gputype}")
    else:
        print("❌ Could not get system information")
    
    print()
    print("=" * 60)
    pause_and_continue()

def run_optimization(name, func, step_num, total_steps):
    """Executes individual optimization with feedback ALWAYS INTERACTIVE"""
    print(f"\n[{step_num}/{total_steps}] 🔄 Applying {name}...")
    try:
        func()
        print(f"✅ {name} completed successfully")
        pause_and_continue(f"Press Enter to continue with the next optimization...")
        return True
    except Exception as e:
        print(f"❌ Error applying {name}: {e}")
        log_and_print(f"Error applying {name}: {e}")
        pause_and_continue(f"Error in {name}. Press Enter to continue...")
        return False

def run_app_installer_simple_fixed():
    """Executes the application installer simply in the current window"""
    try:
        log_and_print("🚀 Starting application installer...")
        
        import tempfile
        import requests
        
        script_url = "https://raw.githubusercontent.com/sogik/ZTalon/refs/heads/main/src/scripts/appinstallers.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "appinstaller.ps1")
        
        log_and_print(f"📥 Downloading script from: {script_url}")
        
        # Download the script
        response = requests.get(script_url)
        
        if response.status_code == 200:
            with open(script_path, "wb") as file:
                file.write(response.content)
            log_and_print("✅ Script downloaded successfully")
            
            clear_screen()
            print("=" * 70)
            print("                APPLICATION INSTALLER")
            print("=" * 70)
            print()
            print("🎮 Installer running in this window...")
            print("📱 Follow the instructions that appear below.")
            print()
            print("=" * 70)
            print()
            
            # Execute directly in current window without -NoExit
            result = subprocess.run([
                "powershell", 
                "-ExecutionPolicy", "Bypass",
                "-File", script_path
            ], cwd=temp_dir)
            
            print("\n" + "=" * 70)
            if result.returncode == 0:
                print("✅ Installer completed successfully")
            else:
                print(f"⚠️ Installer finished with code: {result.returncode}")
            print("=" * 70)
            
            log_and_print("✅ Application installer completed")
            return True
            
        else:
            log_and_print(f"❌ Error downloading script: {response.status_code}")
            return False
            
    except Exception as e:
        log_and_print(f"❌ Error in application installer: {e}")
        return False

def ask_restart():
    """Asks the user if they want to restart"""
    clear_screen()
    print("=" * 60)
    print("              INSTALLATION COMPLETED")
    print("=" * 60)
    print()
    print("🎉 All optimizations have been applied successfully!")
    print()
    print("For some changes to take full effect, it is recommended")
    print("to restart the system.")
    print()
    print("What would you like to do?")
    print()
    print("1. Restart now")
    print("2. Restart later")
    print("3. View change log")
    print()
    
    while True:
        choice = input("Enter your option (1-3): ").strip()
        
        if choice == "1":
            print("\n🔄 Restarting system...")
            print("The system will restart in 10 seconds...")
            print("Press Ctrl+C to cancel...")
            try:
                for i in range(10, 0, -1):
                    print(f"\rRestarting in {i} seconds...", end="", flush=True)
                    time.sleep(1)
                print("\n")
                subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
                print("🔄 Restarting system...")
            except KeyboardInterrupt:
                print("\n🛑 Restart cancelled by user.")
                pause_and_continue()
            except Exception as e:
                print(f"❌ Error restarting: {e}")
                print("Please restart manually.")
                pause_and_continue()
            break
        elif choice == "2":
            print("\n✅ Perfect! Remember to restart when you can so that")
            print("all changes take effect.")
            pause_and_continue()
            break
        elif choice == "3":
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    print("\n" + "="*60)
                    print("CHANGE LOG:")
                    print("="*60)
                    content = f.read()
                    # Show only the last 50 lines if it's too long
                    lines = content.split('\n')
                    if len(lines) > 50:
                        print("... (showing last 50 lines)")
                        print('\n'.join(lines[-50:]))
                    else:
                        print(content)
                    print("="*60)
            except Exception as e:
                print(f"❌ Could not read log file: {e}")
            pause_and_continue()
        else:
            print("❌ Invalid option. Please choose 1, 2 or 3.")

def main():
    try:
        clear_screen()
        print("=" * 60)
        print("              ZTALON - INITIALIZING...")
        print("=" * 60)
        
        log_and_print("🔐 Checking administrator privileges...")
        if not is_running_as_admin():
            print("\n❌ ERROR: Administrator privileges are required.")
            print("Please run the program as administrator.")
            pause_and_continue("Press Enter to exit...")
            return

        print("✅ Administrator privileges verified.")
        time.sleep(1)
        
        print("📊 Getting system information...")
        windows_info = get_windows_info()
        gputype = "Unknown"
        
        if windows_info and windows_info['gpu_info']:
            for gpu in windows_info['gpu_info']:
                if gpu['type'] == 'NVIDIA':
                    gputype = "nvidia"
                    break
                elif gpu['type'] == 'AMD':
                    gputype = "amd"
                    break
                elif gpu['type'] == 'INTEL':
                    gputype = "intel"
        
        print("✅ System information obtained.")
        time.sleep(1)
        
        while True:
            user_choice = get_user_choice()
            
            if user_choice == "exit":
                print("\n👋 Thank you for using ZTalon!")
                break
            elif user_choice == "info":
                show_system_info(windows_info, gputype)
                continue
            elif user_choice == "install":
                if show_app_install_menu():
                    run_app_installer_simple_fixed()
                    pause_and_continue("Press Enter to continue with optimizations...")
                # DO NOT EXIT LOOP - Continue to optimization menu
            
            # Show optimization menu
            optimizations_list = show_optimization_menu()
            
            while True:
                choice = input("Enter your option: ").strip().lower()
                
                if choice == "c":
                    break  # Exit to main menu
                elif choice == "a":
                    clear_screen()
                    print("🔧 INTERACTIVE MODE - Applying all optimizations...")
                    print("📋 Confirmation will be requested after each step.")
                    print("=" * 60)
                    pause_and_continue("Press Enter to begin...")
                    
                    optimization_functions = [
                        ("GPU registry optimization", lambda: debloat_windows.apply_gpuregistryoptimization(gputype)),
                        ("DirectX installation", debloat_windows.run_directxinstallation),
                        ("C++ installation", debloat_windows.run_cinstallation),
                        ("Start menu optimization", debloat_windows.run_startmenuoptimization),
                        ("Uninstall Copilot", debloat_windows.run_copilotuninstaller),
                        ("Uninstall Widgets", debloat_windows.run_widgetsuninstaller),
                        ("GameBar optimization", debloat_windows.run_gamebaroptimization),
                        ("Configure power plan", debloat_windows.apply_powerplan),
                        ("Install Timer Resolution", debloat_windows.install_timerresolution),
                        ("Registry tweaks", debloat_windows.run_registrytweak),
                        ("Registry changes", debloat_windows.apply_registry_changes),
                        ("Lock screen optimization", debloat_windows.apply_signoutlockscreen),
                        ("Uninstall Edge", debloat_windows.run_edgeuninstaller),
                        ("Background apps optimization", debloat_windows.run_backgroundapps),
                        ("Autoruns optimization", debloat_windows.run_autoruns),
                        ("Network optimization", debloat_windows.apply_networkoptimization),
                        ("System final cleanup", debloat_windows.finalize_installation)
                    ]
                    
                    total_steps = len(optimization_functions)
                    successful = 0
                    
                    for i, (name, func) in enumerate(optimization_functions, 1):
                        if run_optimization(name, func, i, total_steps):
                            successful += 1
                    
                    print(f"\n🎯 Summary: {successful}/{total_steps} optimizations applied successfully")
                    pause_and_continue("Press Enter to continue...")
                    
                    ask_restart()
                    return  # Exit program completely
                    
                elif choice == "s":
                    print("\nSpecific selection functionality coming soon...")
                    pause_and_continue()
                else:
                    print("❌ Invalid option. Please choose 'a', 's' or 'c'.")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user.")
        pause_and_continue()
    except Exception as e:
        print(f"\n❌ Critical error in main function: {e}")
        import traceback
        log_and_print(f"Full traceback: {traceback.format_exc()}")
        pause_and_continue("Press Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        pause_and_continue("Press Enter to exit...")