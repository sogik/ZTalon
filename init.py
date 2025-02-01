import sys
import os
import ctypes
import subprocess
import threading
from PyQt5.QtWidgets import QApplication
from browser_select_screen import BrowserSelectScreen
from defender_check import DefenderCheck
from raven_app_screen import RavenAppScreen
from install_screen import InstallScreen
import debloat_windows
import raven_software_install
import browser_install

def is_running_as_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        print(f"Error checking admin privileges: {e}")
        return False

def restart_system():
    print("Restarting system...")
    try:
        subprocess.call(["shutdown", "/r", "/f", "/t", "0"])
    except Exception as e:
        print(f"Failed to restart system: {e}")

def restart_as_admin():
    try:
        script = sys.argv[0]
        params = ' '.join(sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit()
    except Exception as e:
        print(f"Error restarting as admin: {e}")

def main():
    app = QApplication(sys.argv)

    if not is_running_as_admin():
        print("This program requires administrator privileges. Restarting with admin rights...")
        restart_as_admin()

    try:
        defender_check_window = DefenderCheck()
        defender_check_window.defender_disabled_signal.connect(defender_check_window.close)
        defender_check_window.show()
        while defender_check_window.isVisible():
            app.processEvents()
        print("Defender is disabled, proceeding with the rest of the program.")
    except Exception as e:
        print(f"Error during Defender check: {e}")

    selected_browser = None
    try:
        browser_select_screen = BrowserSelectScreen()
        browser_select_screen.show()
        while selected_browser is None:
            app.processEvents()
            if browser_select_screen.selected_browser is not None:
                selected_browser = browser_select_screen.selected_browser
        print(f"Browser Selected: {selected_browser}")
        browser_select_screen.close()
    except Exception as e:
        print(f"Error during browser selection: {e}")

    install_raven = None
    try:
        raven_app_screen = RavenAppScreen()
        raven_app_screen.show()
        while install_raven is None:
            app.processEvents()
            if raven_app_screen.selected_option is not None:
                install_raven = raven_app_screen.selected_option
        print(f"Raven App Installation Decision: {'Yes' if install_raven else 'No'}")
        raven_app_screen.close()
    except Exception as e:
        print(f"Error during Raven app installation decision: {e}")

    try:
        install_screen = InstallScreen()
        install_screen.show()
        print("Starting Windows debloat and customization...")
    except Exception as e:
        print(f"Error during installation screen setup: {e}")

    def perform_installation():
        try:
            print("Applying Windows registry modifications and customizations...")
            debloat_windows.apply_registry_changes()
            print("Debloat and customization complete.")
        except Exception as e:
            print(f"Error applying registry changes: {e}")

        try:
            if install_raven:
                print("Installing Raven software...")
                raven_software_install.main()
                print("Raven software installed.")
        except Exception as e:
            print(f"Error during Raven software installation: {e}")

        try:
            print(f"Installing {selected_browser} browser...")
            browser_install.install_browser(selected_browser)
            print(f"{selected_browser} browser installation complete.")
        except Exception as e:
            print(f"Error during browser installation: {e}")

        print("All installations and configurations completed.")
        install_screen.close()

        restart_system()

    try:
        install_thread = threading.Thread(target=perform_installation)
        install_thread.start()
        install_thread.join()
    except Exception as e:
        print(f"Error starting installation thread: {e}")

    app.exec_()

if __name__ == "__main__":
    main()
