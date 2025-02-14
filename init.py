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
            logging.info("Applying Windows registry modifications and customizations...")
            debloat_windows.run_registrytweak()
            debloat_windows.apply_registry_changes()
            debloat_windows.run_autoruns()
            logging.info("Debloat and customization of registry complete.")
            logging.info("Applying Start menu debloat and optimization...")
            #debloat_windows.run_startmenuoptimization()
            logging.info("Start menu optimization complete.")
            logging.info("Installing Timer Resolution.")
            debloat_windows.install_timerresolution()
            logging.info("Timer Resolution installed.")
            logging.info("Applying background apps optimization.")
            debloat_windows.run_backgroundapps()
            logging.info("Background apps optimization complete.")
    except Exception as e:
            logging.error(f"Error applying registry changes: {e}")

    logging.info("All installations and configurations completed.")
    logging.info("Installation complete. Restarting system...")
    debloat_windows.finalize_installation()

if __name__ == "__main__":
    main()