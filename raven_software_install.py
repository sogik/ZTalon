import os
import sys
import json
import logging
import platform
import subprocess
import ssl
import urllib.request
from pathlib import Path
from tqdm import tqdm

def log(message):
    logging.info(message)

def get_packages_json():
    url = "https://raw.githubusercontent.com/ravendevteam/toolbox/refs/heads/main/packages.json"
    try:
        context = ssl._create_unverified_context()
        response = urllib.request.urlopen(url, context=context)
        return json.loads(response.read().decode())
    except Exception as e:
        log(f"Error downloading packages.json: {e}")
        return None

def get_installation_path():

    if platform.system() == "Windows":
        return Path(os.getenv('APPDATA')) / "ravendevteam"
    else:
        return Path.home() / "Library" / "Application Support" / "ravendevteam"

def download_file(url, destination, desc="Downloading"):

    try:
        context = ssl._create_unverified_context()
        with tqdm(unit='B', unit_scale=True, desc=desc) as pbar:
            def report_hook(count, block_size, total_size):
                if total_size > 0:
                    pbar.total = total_size
                pbar.update(block_size)
            
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(url, destination, reporthook=report_hook)
        return True
    except Exception as e:
        log(f"Download error: {e}")
        return False

def create_shortcut(target_path, shortcut_name):

    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
        
        os.system(f'cmd /c mklink "{shortcut_path}" "{target_path}"')
        log(f"Created shortcut for {shortcut_name}")
        return True
    except Exception as e:
        log(f"Failed to create shortcut: {e}")
        return False

def install_package(package, install_dir):

    platform_name = platform.system()
    
    if platform_name not in package["os"]:
        log(f"Package {package['name']} is not available for {platform_name}")
        return False

    package_dir = install_dir / package["name"]
    package_dir.mkdir(parents=True, exist_ok=True)

    url = package["url"][platform_name]
    file_name = url.split("/")[-1]
    download_path = package_dir / file_name

    log(f"Installing {package['name']} v{package['version']}...")
    
    if not download_file(url, download_path, f"Downloading {package['name']}"):
        return False

    if package["shortcut"] and platform_name == "Windows":
        create_shortcut(str(download_path), package["name"])

    log(f"Successfully installed {package['name']}")
    return True

def run_toolbox():

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    log("Fetching package list...")
    packages_data = get_packages_json()
    if not packages_data:
        return False

    install_dir = get_installation_path()
    install_dir.mkdir(parents=True, exist_ok=True)

    success = True
    for package in packages_data["packages"]:
        if not install_package(package, install_dir):
            success = False
            log(f"Failed to install {package['name']}")
        else:
            log(f"Successfully installed {package['name']}")

    if success:
        log("All packages installed successfully")
        sys.exit(1)
    else:
        log("Some packages failed to install")
        sys.exit(1)

    return success

def main():
    try:
        success = run_toolbox()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
