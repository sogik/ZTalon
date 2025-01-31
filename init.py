import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread
from browser_select_screen import BrowserSelectScreen
from defender_check import DefenderCheck
from raven_app_screen import RavenAppScreen
from install_screen import InstallScreen
import subprocess
from debloat_windows import apply_registry_changes
import raven_software_install
import browser_install

def is_running_as_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def restart_system():
    print("Restarting system...")
    subprocess.call(["shutdown", "/r", "/f", "/t", "0"])

def restart_as_admin():
    script = sys.argv[0]
    params = ' '.join(sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)

def main():
    app = QApplication(sys.argv)

    try:
        if not is_running_as_admin():
            print("This program requires administrator privileges. Restarting with admin rights...")
            restart_as_admin()
            sys.exit()
    except Exception as e:
        print(f"Error checking admin privileges: {e}")

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

    def on_installation_complete():
        try:
            print("Optionally installing Raven software...")
            if install_raven:
                raven_software_install.main()
            print("Installing selected browser...")
            browser_install.install_browser(selected_browser)
            print("All installations and configurations completed.")
        except Exception as e:
            print(f"Error during installation: {e}")
        finally:
            install_screen.close()
            restart_system()

    try:
        debloat_thread = QThread()
        debloat_worker = lambda: apply_registry_changes()
        debloat_thread.run = debloat_worker
        debloat_thread.finished.connect(on_installation_complete)
        debloat_thread.start()
    except Exception as e:
        print(f"Error starting debloat thread: {e}")

    app.exec_()

if __name__ == "__main__":
    main()
