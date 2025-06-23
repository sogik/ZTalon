"""
ZTalon Components Package
========================

This package contains the core components of ZTalon:
- app_install: Application installer functionality
- debloat_windows: System optimization and debloating functions
"""

from .app_install import run_appinstaller
from .debloat_windows import (
    apply_registry_changes,
    finalize_installation,
    run_threaded_optimizations,
    test_connectivity,
)

__version__ = "1.0.0"
__author__ = "sogik"