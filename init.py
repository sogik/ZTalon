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

LOG_FILE = "talon.txt"
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

def main():
    try:
            logging.info("Comprobave is Running as admin.")
            is_running_as_admin()
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
            logging.info("Applying Signout lockscreen optimzations...")
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