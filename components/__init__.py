"""
ZTalon Components Package
========================

This package contains the core components of ZTalon:
- app_install: Application installer functionality  
- debloat_windows: System optimization and debloating functions
- utils: Enhanced utilities for logging, admin checks, SSL, etc.
"""

# Core functionality imports
from .app_install import run_appinstaller
from .debloat_windows import (
    apply_registry_changes,
    finalize_installation,
    run_threaded_optimizations,
    test_connectivity,
    apply_gpuregistryoptimization,
    run_registrytweak,
    install_timerresolution,
    run_startmenuoptimization,
    run_backgroundapps,
    run_copilotuninstaller,
    run_widgetsuninstaller,
    run_gamebaroptimization,
    apply_powerplan,
    apply_signoutlockscreen,
    run_edgeuninstaller,
    apply_networkoptimization,
    apply_msimode,
    run_directxinstallation,
    run_cinstallation,
    apply_nvidiaoptimization,
    apply_amdoptimization,
)

# Enhanced utilities
from .utils import (
    create_ssl_context,
    download_with_ssl,
    check_admin_privileges,
    handle_error,
    ZTalonError,
    verify_file_integrity,
    get_secure_temp_dir,
    get_system_info,
    setup_enhanced_logging
)

# Metadata
__version__ = "1.0.1"
__author__ = "sogik"
__license__ = "BSD-3-Clause"
__description__ = "ZTalon Windows Optimization and Debloating Tool"
__url__ = "https://github.com/sogik/ZTalon"

__all__ = [
    'run_appinstaller',
    'apply_registry_changes',
    'finalize_installation',
    'test_connectivity',
    'apply_gpuregistryoptimization',
    'apply_nvidiaoptimization', 
    'apply_amdoptimization',
    'run_registrytweak',
    'install_timerresolution',
    'run_startmenuoptimization',
    'run_backgroundapps',
    'apply_powerplan',
    'download_file_with_retries',
    'download_and_execute_script',
    'set_registry_value',
]

# Enhanced error handling
try:
    import requests
    import certifi
    __dependencies_ok__ = True
except ImportError as e:
    __dependencies_ok__ = False
    __dependency_error__ = str(e)

def get_package_info():
    """Return comprehensive package information"""
    return {
        'name': 'ZTalon Components',
        'version': __version__,
        'author': __author__,
        'license': __license__,
        'description': __description__,
        'url': __url__,
        'dependencies_ok': __dependencies_ok__,
        'available_functions': len(__all__)
    }

# Logging setup for the package
import logging
import os

def setup_package_logging():
    """Setup enhanced logging for the components package"""
    log_file = "ztalon_components.log"
    
    logger = logging.getLogger('ztalon.components')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger

# Initialize package logging
_package_logger = setup_package_logging()
_package_logger.info(f"ZTalon Components v{__version__} initialized")

if not __dependencies_ok__:
    _package_logger.error(f"Missing dependencies: {__dependency_error__}")