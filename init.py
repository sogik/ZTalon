import sys
import os
import ctypes
import subprocess
import logging
import time
import platform
import winreg
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from components import debloat_windows
from components import app_install
# Importar las nuevas utilidades
from components.utils import (
    setup_enhanced_logging,
    check_admin_privileges,
    get_secure_temp_dir,
    get_system_info,
    ZTalonError,
    handle_error
)

enhanced_logger = setup_enhanced_logging("INFO")

LOG_FILE = "ztalon.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode='w',
    encoding='utf-8'
)

def log_and_print(message):
    """Function to log and display in console using enhanced logging"""
    enhanced_logger.info(message)
    print(message)

def show_error_popup(message, allow_continue=True):
    """Show error popup with option to continue or exit"""
    enhanced_logger.error(f"ERROR: {message}")
    print(f"\n❌ ERROR: {message}")
    if allow_continue:
        choice = input("Press Enter to continue or 'q' to quit: ").lower()
        if choice == 'q':
            sys.exit(1)
    else:
        input("Press Enter to exit...")
        sys.exit(1)

def is_console_available():
    """Check if console is available for input"""
    try:
        # Try to get console window handle
        return ctypes.windll.kernel32.GetConsoleWindow() != 0
    except:
        return False

def safe_input(prompt="", default=""):
    """Safe input function that handles EOF errors with timeout"""
    try:
        if is_console_available():
            print(prompt, end="", flush=True)
            # Use a timeout to prevent hanging
            import select
            import sys
            
            # For Windows, we need a different approach
            if os.name == 'nt':
                import msvcrt
                import time
                
                start_time = time.time()
                input_chars = []
                
                while True:
                    if msvcrt.kbhit():
                        char = msvcrt.getch()
                        if char in [b'\r', b'\n']:  # Enter key
                            print()  # New line
                            return ''.join(input_chars) if input_chars else default
                        elif char == b'\x08':  # Backspace
                            if input_chars:
                                input_chars.pop()
                                print('\b \b', end='', flush=True)
                        elif char == b'\x03':  # Ctrl+C
                            raise KeyboardInterrupt
                        else:
                            try:
                                decoded_char = char.decode('utf-8')
                                input_chars.append(decoded_char)
                                print(decoded_char, end='', flush=True)
                            except:
                                pass
                    
                    # Timeout after 30 seconds
                    if time.time() - start_time > 30:
                        print(f"\n⏱️ Input timeout. Using default: {default}")
                        return default
                    
                    time.sleep(0.1)
            else:
                # Unix-like systems
                return input(prompt)
        else:
            # If no console, create one or use default
            try:
                # Allocate a console for the process
                ctypes.windll.kernel32.AllocConsole()
                # Reopen stdin, stdout, stderr
                sys.stdin = open('CONIN$', 'r')
                sys.stdout = open('CONOUT$', 'w') 
                sys.stderr = open('CONOUT$', 'w')
                print(prompt, end="", flush=True)
                
                # Try input with timeout
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError("Input timeout")
                
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(30)  # 30 second timeout
                
                try:
                    result = input()
                    signal.alarm(0)  # Cancel alarm
                    return result if result else default
                finally:
                    signal.signal(signal.SIGALRM, old_handler)
                    
            except (TimeoutError, Exception):
                print(f"\n⏱️ Input timeout or error. Using default: {default}")
                return default
                
    except EOFError:
        print(f"\n⚠️ No console input available. Using default: {default}")
        return default
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Input error: {e}. Using default: {default}")
        return default

def pause_and_continue(message="Press Enter to continue..."):
    """Pauses the program until the user presses Enter (ALWAYS) with timeout"""
    print(f"\n{message}")
    try:
        result = safe_input("", "")
        # Always continue regardless of input
        return result
    except Exception as e:
        print(f"⚠️ Input error, continuing automatically: {e}")
        time.sleep(1)
        return ""

def clear_screen():
    """Clears the screen"""
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except:
        print("\n" * 50)  # Fallback if cls doesn't work

def run_as_admin():
    """Relaunch the program with administrator privileges"""
    if getattr(sys, 'frozen', False):
        executable = sys.executable
        params = ' '.join(f'"{arg}"' for arg in sys.argv[1:])
    else:
        executable = sys.executable
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{script}"'] + [f'"{arg}"' for arg in sys.argv[1:]])
    
    cwd = os.getcwd()
    log_and_print(f"Elevating: {executable} {params}")
    
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # verb
            executable,     # file
            params,         # parameters
            cwd,           # directory
            1              # show cmd window normally
        )
    except Exception as e:
        logging.exception("Failed to relaunch with admin privileges")
        show_error_popup(f"Unable to elevate to Administrator:\n{e}", allow_continue=False)
        sys.exit(1)

def is_admin():
    """Check if running as administrator using enhanced utils"""
    return check_admin_privileges()

def ensure_admin():
    """Ensure the program is running with administrator privileges"""
    if not is_admin():
        log_and_print("Administrator privileges required; relaunching with UAC prompt...")
        run_as_admin()
        sys.exit(0)
    else:
        log_and_print("Running with Administrator privileges.")


def show_system_info(windows_info, gpu_info):
    """Show comprehensive system information using enhanced utils"""
    system_info = get_system_info()
    
    clear_screen()
    print("=" * 70)
    print("                SYSTEM INFORMATION")
    print("=" * 70)
    print()
    
    if 'os' in system_info:
        print("🖥️  Operating System:")
        print(f"   Platform: {system_info['os'].get('platform', 'Unknown')}")
        print(f"   Architecture: {system_info['os'].get('architecture', ['Unknown'])[0]}")
        print()
    
    if 'python' in system_info:
        print("🐍 Python:")
        print(f"   Version: {system_info['python'].get('version', 'Unknown')}")
        print(f"   Implementation: {system_info['python'].get('implementation', 'Unknown')}")
        print()
    
    if 'system' in system_info:
        print("⚙️  System Resources:")
        print(f"   CPU Cores: {system_info['system'].get('cpu_count', 'Unknown')}")
        print(f"   Memory: {system_info['system'].get('memory_gb', 'Unknown')} GB")
        print(f"   Free Disk Space: {system_info['system'].get('disk_free_gb', 'Unknown')} GB")
        print()
    
    if 'ztalon' in system_info:
        print("🛠️  ZTalon Status:")
        admin_status = "✅ Yes" if system_info['ztalon'].get('admin_privileges') else "❌ No"
        print(f"   Admin Privileges: {admin_status}")
        print(f"   Temp Directory: {system_info['ztalon'].get('temp_dir', 'Unknown')}")
        print(f"   SSL Support: ✅ Enhanced" if system_info['ztalon'].get('ssl_support') else "⚠️ Basic")
        print()
    
    print("🎮 GPU Information:")
    print(f"   Detected GPU: {gpu_info}")
    print()
    
    print("=" * 70)


@handle_error
def check_temp_writable():
    """Check if temp directory is writable using enhanced utils"""
    secure_temp = get_secure_temp_dir()
    
    try:
        test_path = os.path.join(secure_temp, "_write_test")
        with open(test_path, "w") as f:
            f.write("test")
        os.remove(test_path)
        log_and_print(f"✅ Secure temp directory ready: {secure_temp}")
        return True
    except Exception as e:
        log_and_print(f"❌ Temp dir check failed: {e}")
        show_error_popup(
            f"Could not write files to {secure_temp}.\n"
            "Please free up disk space or check permissions.",
            allow_continue=True
        )
        return False

def check_connectivity():
    """Check internet connectivity to required domains"""
    test_urls = [
        "https://raw.githubusercontent.com",
        "https://github.com",  # Cambiar christitus.com por github.com
        "https://debloat.raphi.re"
    ]
    
    for url in test_urls:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10):
                log_and_print(f"✅ Connectivity check passed: {url}")
        except Exception as e:
            log_and_print(f"⚠️ Connectivity issue with {url}: {e}")
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            if parsed_url.hostname == "github.com":
                # Si GitHub falla es más crítico
                show_error_popup(
                    f"Could not reach GitHub. Please check your internet connection.\n"
                    "GitHub is required to download optimization scripts.",
                    allow_continue=True
                )

def check_temp_writable():
    """Check if temp directory is writable"""
    temp_root = os.environ.get("TEMP", tempfile.gettempdir())
    ztalon_dir = os.path.join(temp_root, "ztalon")
    
    try:
        os.makedirs(ztalon_dir, exist_ok=True)
        test_path = os.path.join(ztalon_dir, "_write_test")
        with open(test_path, "w") as f:
            f.write("test")
        os.remove(test_path)
        log_and_print(f"✅ Temp directory writable: {ztalon_dir}")
        return True
    except Exception as e:
        log_and_print(f"❌ Temp dir check failed: {e}")
        show_error_popup(
            f"Could not write files to {ztalon_dir}.\n"
            "Please free up disk space or check permissions.",
            allow_continue=True
        )
        return False

def check_windows_version():
    """Check if running on supported Windows version"""
    try:
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        
        product_name, _ = winreg.QueryValueEx(key, "ProductName")
        build_number, _ = winreg.QueryValueEx(key, "CurrentBuildNumber")
        
        winreg.CloseKey(key)
        winreg.CloseKey(reg)
        
        build_num = int(build_number)
        
        if build_num < 19041:  # Windows 10 version 2004
            show_error_popup(
                f"Unsupported Windows version detected: {product_name} (Build {build_number})\n"
                "ZTalon requires Windows 10 version 2004 or later.",
                allow_continue=False
            )
            return False
        
        if "Home" in product_name or "Pro" in product_name or "Enterprise" in product_name:
            log_and_print(f"✅ Supported Windows version: {product_name} (Build {build_number})")
            return True
        else:
            log_and_print(f"⚠️ Untested Windows edition: {product_name}")
            return True
            
    except Exception as e:
        log_and_print(f"❌ Could not verify Windows version: {e}")
        show_error_popup(f"Could not verify Windows version: {e}", allow_continue=True)
        return True

def run_pre_checks():
    """Run all pre-installation checks"""
    log_and_print("🔍 Running pre-installation checks...")
    
    # Check Windows version
    if not check_windows_version():
        return False
    
    # Check connectivity
    check_connectivity()
    
    # Check temp directory
    if not check_temp_writable():
        return False
    
    log_and_print("✅ All pre-checks completed successfully")
    return True

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
    print("4. Run system checks")
    print("5. Exit")
    print()
    print("=" * 60)

def get_user_choice():
    """Gets user choice with validation"""
    while True:
        show_menu()
        choice = safe_input("Enter your option (1-5): ", "2").strip()
        
        if choice == "1":
            return "install"
        elif choice == "2":
            return "optimize"
        elif choice == "3":
            return "info"
        elif choice == "4":
            return "checks"
        elif choice == "5":
            return "exit"
        else:
            print("\n❌ Invalid option. Please choose an option from 1 to 5.")
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
        choice = safe_input("Enter your option (1-2): ", "2").strip()
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
        ("Network optimization", "Network optimization"),
        ("Disable WPBT (Platform Binary Table)", "Disable WPBT"),
        ("Disable folder type discovery in Explorer", "Disable folder discovery")
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
    """Execute individual optimization with automatic continuation"""
    print(f"\n[{step_num}/{total_steps}] 🔄 Applying {name}...")
    log_and_print(f"Starting optimization: {name}")
    
    try:
        # Execute optimization and wait for completion
        success = func()
        
        if success:
            print(f"✅ {name} completed successfully")
            log_and_print(f"✅ Optimization completed: {name}")
        else:
            print(f"⚠️ {name} completed with warnings")
            log_and_print(f"⚠️ Optimization completed with warnings: {name}")
        
        # Brief delay to show completion status
        time.sleep(1.5)
        
        # Auto-continue to next optimization
        if step_num < total_steps:
            print(f"🔄 Proceeding to next optimization ({step_num + 1}/{total_steps})...")
        
        return True
        
    except Exception as e:
        error_msg = f"Error applying {name}: {e}"
        print(f"❌ {error_msg}")
        log_and_print(error_msg)
        
        # Log full error details
        import traceback
        full_traceback = traceback.format_exc()
        logging.error(f"Full traceback for {name}: {full_traceback}")
        
        # Ask user to continue only on error
        print(f"\n⚠️ An error occurred during {name}")
        choice = safe_input(f"Continue with remaining optimizations? (Y/n): ", "y").lower()
        if choice == 'n':
            show_error_popup(f"Optimization stopped due to error in {name}", allow_continue=False)
            return False
        
        print(f"🔄 Continuing with remaining optimizations...")
        return False

def run_app_installer_simple_fixed():
    """Executes the application installer with better error handling"""
    try:
        log_and_print("🚀 Starting application installer...")
        
        import tempfile
        import requests
        
        script_url = "https://raw.githubusercontent.com/sogik/ZTalon/refs/heads/main/src/scripts/appinstallers.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "appinstaller.ps1")
        
        log_and_print(f"📥 Downloading script from: {script_url}")
        
        # Download the script with timeout and retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(script_url, timeout=30)
                if response.status_code == 200:
                    break
                else:
                    raise requests.RequestException(f"HTTP {response.status_code}")
            except Exception as e:
                if attempt < max_retries - 1:
                    log_and_print(f"⚠️ Download attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(2)
                else:
                    raise
        
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
            
            # Execute directly in current window
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
            error_msg = f"Error downloading script: HTTP {response.status_code}"
            log_and_print(f"❌ {error_msg}")
            show_error_popup(error_msg, allow_continue=True)
            return False
            
    except Exception as e:
        error_msg = f"Error in application installer: {e}"
        log_and_print(f"❌ {error_msg}")
        show_error_popup(error_msg, allow_continue=True)
        return False

def ask_restart():
    """Asks the user if they want to restart with better error handling"""
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
        choice = safe_input("Enter your option (1-3): ", "2").strip()
        
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
                error_msg = f"Error restarting: {e}"
                print(f"❌ {error_msg}")
                show_error_popup(f"{error_msg}\nPlease restart manually.", allow_continue=True)
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
                error_msg = f"Could not read log file: {e}"
                print(f"❌ {error_msg}")
                show_error_popup(error_msg, allow_continue=True)
            pause_and_continue()
        else:
            print("❌ Invalid option. Please choose 1, 2 or 3.")

def ensure_console():
    """Ensure console is available for the application"""
    try:
        # Try to allocate console if we don't have one
        if not is_console_available():
            ctypes.windll.kernel32.AllocConsole()
            # Redirect stdout, stderr, stdin
            sys.stdout = open('CONOUT$', 'w')
            sys.stderr = open('CONOUT$', 'w')
            sys.stdin = open('CONIN$', 'r')
            log_and_print("✅ Console allocated successfully")
    except Exception as e:
        log_and_print(f"⚠️ Could not allocate console: {e}")

def show_individual_optimization_menu(optimizations):
    """Shows menu for selecting individual optimizations"""
    selected_optimizations = []
    
    while True:
        clear_screen()
        print("=" * 80)
        print("                    SELECT SPECIFIC OPTIMIZATIONS")
        print("=" * 80)
        print()
        print("✅ Select the optimizations you want to apply:")
        print()
        
        # Show all optimizations with selection status
        for i, (english, _) in enumerate(optimizations, 1):
            status = "✅" if i in selected_optimizations else "⬜"
            print(f"{status} {i:2d}. {english}")
        
        print()
        print("=" * 80)
        print("📋 COMMANDS:")
        print("   • Enter numbers (1-16) to toggle optimizations")
        print("   • 'a' = Select all")
        print("   • 'n' = Select none")
        print("   • 'r' = Run selected optimizations")
        print("   • 'c' = Cancel and return to main menu")
        print()
        
        if selected_optimizations:
            print(f"🎯 Selected: {len(selected_optimizations)} optimization(s)")
        else:
            print("⚠️  No optimizations selected")
        
        print("=" * 80)
        
        choice = safe_input("Enter your choice: ", "").lower().strip()
        
        if choice == 'c':
            return None  # Cancel
        elif choice == 'a':
            selected_optimizations = list(range(1, len(optimizations) + 1))
            print("✅ All optimizations selected!")
            time.sleep(1)
        elif choice == 'n':
            selected_optimizations = []
            print("⬜ All optimizations deselected!")
            time.sleep(1)
        elif choice == 'r':
            if selected_optimizations:
                return selected_optimizations
            else:
                print("❌ No optimizations selected! Please select at least one.")
                time.sleep(2)
        else:
            # Try to parse as numbers
            try:
                numbers = []
                for num_str in choice.replace(',', ' ').split():
                    num = int(num_str)
                    if 1 <= num <= len(optimizations):
                        numbers.append(num)
                    else:
                        print(f"❌ Invalid number: {num}. Must be between 1 and {len(optimizations)}")
                        time.sleep(1)
                        break
                else:
                    # Toggle selected numbers
                    for num in numbers:
                        if num in selected_optimizations:
                            selected_optimizations.remove(num)
                            print(f"⬜ Deselected: {optimizations[num-1][0]}")
                        else:
                            selected_optimizations.append(num)
                            print(f"✅ Selected: {optimizations[num-1][0]}")
                    
                    if numbers:
                        time.sleep(1)
                        
            except ValueError:
                print("❌ Invalid input. Please enter numbers (1-16), 'a', 'n', 'r', or 'c'")
                time.sleep(2)

def run_selected_optimizations(selected_indices, optimizations):
    """Execute only user-selected optimizations"""
    
    # Detect GPU hardware for optimization targeting
    gputype = get_gpu_info_advanced()
    log_and_print(f"🎮 Detected GPU: {gputype}")
    
    # Build targeted optimization function list
    optimization_functions = []
    
    for index in sorted(selected_indices):
        opt_name, _ = optimizations[index - 1]
        
        # Map optimization names to their respective functions
        if "GPU registry optimization" in opt_name:
            optimization_functions.append((opt_name, lambda: debloat_windows.apply_gpuregistryoptimization(gputype)))
        elif "DirectX installation" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_directxinstallation))
        elif "C++ installation" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_cinstallation))
        elif "Start menu optimization" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_startmenuoptimization))
        elif "Uninstall Copilot" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_copilotuninstaller))
        elif "Uninstall Widgets" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_widgetsuninstaller))
        elif "GameBar optimization" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_gamebaroptimization))
        elif "Configure power plan" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.apply_powerplan))
        elif "Install Timer Resolution" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.install_timerresolution))
        elif "Registry tweaks" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_registrytweak))
        elif "Registry changes" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.apply_registry_changes))
        elif "Lock screen optimization" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.apply_signoutlockscreen))
        elif "Uninstall Edge" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_edgeuninstaller))
        elif "Background apps optimization" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_backgroundapps))
        elif "Autoruns optimization" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.run_autoruns))
        elif "Network optimization" in opt_name:
            optimization_functions.append((opt_name, debloat_windows.apply_networkoptimization))
    
    # Always add system cleanup as final step
    if optimization_functions:
        optimization_functions.append(("System final cleanup", debloat_windows.finalize_installation))
    
    # Display confirmation before execution
    clear_screen()
    print("=" * 70)
    print("                    SELECTED OPTIMIZATIONS")
    print("=" * 70)
    print()
    print("🎯 The following optimizations will be applied:")
    print()
    
    for i, (name, _) in enumerate(optimization_functions, 1):
        print(f"   {i}. {name}")
    
    print()
    print("=" * 70)
    
    confirm = safe_input("Do you want to proceed? (y/N): ", "n").lower()
    if confirm != 'y':
        print("❌ Operation cancelled by user.")
        return
    
    # Execute optimization pipeline
    total_steps = len(optimization_functions)
    successful = 0
    failed = 0
    
    log_and_print(f"🚀 Starting {total_steps} selected optimizations...")
    print(f"\n🎯 Optimization Progress: 0/{total_steps}")
    
    for i, (name, func) in enumerate(optimization_functions, 1):
        print(f"\n{'='*70}")
        print(f"                OPTIMIZATION {i}/{total_steps}")
        print(f"{'='*70}")
        
        if run_optimization(name, func, i, total_steps):
            successful += 1
        else:
            failed += 1
        
        # Update progress tracker
        print(f"\n📊 Progress: {i}/{total_steps} completed | ✅ {successful} successful | ❌ {failed} failed")
    
    # Display comprehensive results
    print(f"\n{'='*70}")
    print(f"              OPTIMIZATION COMPLETE")
    print(f"{'='*70}")
    print(f"🎯 Final Summary:")
    print(f"   • Total optimizations: {total_steps}")
    print(f"   • Successful: {successful}")
    print(f"   • Failed: {failed}")
    print(f"   • Success rate: {(successful/total_steps)*100:.1f}%")
    print(f"{'='*70}")
    
    log_and_print(f"🎯 Optimization Summary: {successful}/{total_steps} successful, {failed} failed")
    
    # Brief pause to review results
    time.sleep(2)
    ask_restart()

def main():
    """Main application entry point"""
    try:
        ensure_console()
        ensure_admin()
        
        # Run system compatibility checks
        if not run_pre_checks():
            show_error_popup("Pre-checks failed. Cannot continue.", allow_continue=False)
            return
        
        # Main application loop
        while True:
            choice = get_user_choice()
            
            if choice == "install":
                # Handle app installation + system optimization
                if show_app_install_menu():
                    if not run_app_installer_simple_fixed():
                        show_error_popup("Application installation failed", allow_continue=True)
                
                # Present optimization options
                optimizations = show_optimization_menu()
                
                while True:
                    opt_choice = safe_input("Choose option (a/s/c): ", "").lower()
                    
                    if opt_choice == "c":
                        break
                    elif opt_choice == "a":
                        # Execute all available optimizations
                        gputype = get_gpu_info_advanced()
                        log_and_print(f"🎮 Detected GPU: {gputype}")
                        
                        # Build complete optimization pipeline
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
                            ("Disable WPBT (Platform Binary Table)", debloat_windows.disable_wpbt),
                            ("Disable folder type discovery in Explorer", debloat_windows.disable_folder_discovery),
                            ("System final cleanup", debloat_windows.finalize_installation)
                        ]
                        
                        total_steps = len(optimization_functions)
                        successful = 0
                        
                        # Execute optimization pipeline sequentially
                        for i, (name, func) in enumerate(optimization_functions, 1):
                            if run_optimization(name, func, i, total_steps):
                                successful += 1
                        
                        print(f"\n🎯 Summary: {successful}/{total_steps} optimizations applied successfully")
                        
                        ask_restart()
                        return
                        
                    elif opt_choice == "s":
                        # Handle user-selected optimizations
                        selected_indices = show_individual_optimization_menu(optimizations)
                        if selected_indices:
                            run_selected_optimizations(selected_indices, optimizations)
                            return
                    else:
                        print("❌ Invalid option. Please choose 'a', 's' or 'c'.")
            
            elif choice == "optimize":
                # System optimization without app installation
                optimizations = show_optimization_menu()
                
                while True:
                    opt_choice = safe_input("Choose option (a/s/c): ", "").lower()
                    
                    if opt_choice == "c":
                        break
                    elif opt_choice == "a":
                        # Execute same optimization pipeline as above
                        gputype = get_gpu_info_advanced()
                        log_and_print(f"🎮 Detected GPU: {gputype}")
                        
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
                        
                        ask_restart()
                        return
                        
                    elif opt_choice == "s":
                        selected_indices = show_individual_optimization_menu(optimizations)
                        if selected_indices:
                            run_selected_optimizations(selected_indices, optimizations)
                            return
                    else:
                        print("❌ Invalid option. Please choose 'a', 's' or 'c'.")
            
            elif choice == "info":
                # Show detailed system information
                windows_info = get_windows_info()
                gputype = get_gpu_info_advanced()
                show_system_info(windows_info, gputype)
            
            elif choice == "checks":
                # Verify system compatibility
                run_pre_checks()
                pause_and_continue()
            
            elif choice == "exit":
                print("👋 Thanks for using ZTalon!")
                break
        
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user.")
        pause_and_continue()
    except Exception as e:
        print(f"\n❌ Critical error in main function: {e}")
        import traceback
        full_traceback = traceback.format_exc()
        log_and_print(f"Full traceback: {full_traceback}")
        show_error_popup(f"Critical error: {e}", allow_continue=False)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        pause_and_continue("Press Enter to exit...")