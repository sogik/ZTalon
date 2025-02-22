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
import GPUtil
import app_install

LOG_FILE = "ztalon.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def is_running_as_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logging.error(f"Error checking admin privileges: {e}")
        return False

def get_windows_info():
    try:
        windows_version = platform.win32_ver()
        reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
        key = winreg.OpenKey(reg, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        
        build_number = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
        product_name = winreg.QueryValueEx(key, "ProductName")[0]
        display_version = winreg.QueryValueEx(key, "DisplayVersion")[0]
        
        gpus = GPUtil.getGPUs()
        gpu_info = []
        for gpu in gpus:
            if 'NVIDIA' in gpu.name.upper():
                gpu_type = 'NVIDIA'
            elif 'AMD' in gpu.name.upper() or 'RADEON' in gpu.name.upper():
                gpu_type = 'AMD'
            else:
                gpu_type = 'Unknown'
            gpu_info.append({
                'name': gpu.name,
                'driver_version': gpu.driver,
                'type': gpu_type
            })
        
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

def ask_user_choice():
    powershell_script = """
    $choice = Read-Host "What would you like to do? (1) Install applications (2) Optimize only"
    if ($choice -eq "1") {
        Write-Output "install"
    } elseif ($choice -eq "2") {
        Write-Output "optimize"
    } else {
        Write-Output "invalid"
    }
    """
    result = subprocess.run(["powershell", "-Command", powershell_script], capture_output=True, text=True)
    return result.stdout.strip()

def main():
    windows_info = get_windows_info()
    if windows_info:
        logging.info(f"Windows Version: {windows_info['product_name']}")
        logging.info(f"Build Number: {windows_info['build']}")
        logging.info(f"Display Version: {windows_info['display_version']}")
        logging.info("GPU Information:")
        for gpu in windows_info['gpu_info']:
            logging.info(f"Name: {gpu['name']}, Driver Version: {gpu['driver_version']}, Type: {gpu['type']}")
            if gpu['type'] == 'NVIDIA':
                logging.info("NVIDIA GPU detected.")
                gputype = "NVIDIA"
            elif gpu['type'] == 'AMD':
                logging.info("AMD GPU detected.")
                gputype = "AMD"
            else:
                logging.info("Unknown GPU detected.")

    try:
        logging.info("Checking if running as administrator.")
        if not is_running_as_admin():
            logging.error("No administrator privileges.")
            return

        logging.info("Admin privileges verified.")
        
        user_choice = ask_user_choice()
        if user_choice == "install":
            logging.info("Starting app installation...")
            app_install.run_appinstaller()
            logging.info("App installation complete.")
        elif user_choice == "optimize":
            logging.info("Skipping app installation. Proceeding with optimization...")
        else:
            logging.error("Invalid choice. Exiting.")
            return

        logging.info("Applying GPU registry optimization...")
        debloat_windows.run_gpuregistryoptimization(gputype)
        logging.info("GPU registry optimization complete.")
        logging.info("Installing dependencies...")
        debloat_windows.run_directxinstallation()
        debloat_windows.run_cinstallation()
        logging.info("Dependencies installed.")
        logging.info("Applying Start menu debloat and optimization...")
        debloat_windows.run_startmenuoptimization()
        logging.info("Start menu debloat and optimization complete.")
        logging.info("Uninstalling copilot...")
        debloat_windows.run_copilotuninstaller()
        logging.info("Copilot uninstalled.")
        logging.info("Uninstalling widgets...")
        debloat_windows.run_widgetsuninstaller()
        logging.info("Widgets uninstalled.")
        logging.info("Applying gamebar optimizations...")
        debloat_windows.run_gamebaroptimization()
        logging.info("Gamebar optimization complete.")
        logging.info("Applying power plan...")
        debloat_windows.apply_powerplan()
        logging.info("Power plan applied.")
        logging.info("Installing Timer Resolution.")
        debloat_windows.install_timerresolution()
        logging.info("Timer Resolution installed.")
        logging.info("Applying Windows registry modifications and customizations...")
        debloat_windows.run_registrytweak()
        debloat_windows.apply_registry_changes()
        logging.info("Windows registry modifications and customizations complete.")
        logging.info("Applying Signout lockscreen optimizations...")
        debloat_windows.apply_signoutlockscreen()
        logging.info("Signout lockscreen optimizations applied.")
        logging.info("Uninstalling edge...")
        debloat_windows.run_edgeuninstaller()
        logging.info("Edge uninstalled.")
        logging.info("Applying background apps optimization.")
        debloat_windows.run_backgroundapps()
        logging.info("Background apps optimization complete.")
        logging.info("Applying autoruns optimizations...")
        debloat_windows.run_autoruns()
        logging.info("Autoruns complete.")
        logging.info("Applying network optimization...")
        debloat_windows.apply_networkoptimization()
        logging.info("Network optimization complete.")
    except Exception as e:
        logging.error(f"Error applying registry changes: {e}")

    logging.info("All installations and configurations completed.")
    logging.info("Installation complete. Restarting system...")
    debloat_windows.finalize_installation()

if __name__ == "__main__":
    main()