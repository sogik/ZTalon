"""
ZTalon Enhanced Utilities
========================

Enhanced utility functions with improved error handling, SSL support, and logging.
"""

import ssl
import certifi
import urllib.request
import urllib.parse
import os
import sys
import ctypes
import logging
import tempfile
import hashlib
import time
from typing import Optional, Dict, Any, Callable
import requests

# Enhanced SSL Context Creation
def create_ssl_context() -> ssl.SSLContext:
    """
    Create a secure SSL context using certifi certificates
    This improves HTTPS connection reliability
    """
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context
    except Exception as e:
        logging.warning(f"Failed to create SSL context with certifi: {e}")
        # Fallback to default context
        return ssl.create_default_context()

# Enhanced Download Handler
def download_with_ssl(url: str, dest_path: str, timeout: int = 30, max_retries: int = 3) -> bool:
    """
    Enhanced download function with SSL support and retry mechanism
    """
    ssl_context = create_ssl_context()
    
    for attempt in range(max_retries):
        try:
            # Validate URL
            parsed_url = urllib.parse.urlparse(url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                raise ValueError(f"Invalid URL format: {url}")
            
            # Create request with SSL context
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'ZTalon/0.0.4 (Windows)')
            
            # Download with progress tracking
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                with open(dest_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Show progress for large files
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r📥 Progress: {percent:.1f}%", end="", flush=True)
                
                print()  # New line after progress
                logging.info(f"Successfully downloaded: {url} -> {dest_path}")
                return True
                
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"Download attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(2)
            else:
                logging.error(f"Download failed after {max_retries} attempts: {e}")
                return False
    
    return False

# Enhanced Admin Check
def check_admin_privileges() -> bool:
    """
    Enhanced admin privilege check with detailed logging
    """
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            logging.info("✅ Running with administrator privileges")
        else:
            logging.warning("⚠️ Not running with administrator privileges")
        return bool(is_admin)
    except Exception as e:
        logging.error(f"Failed to check admin privileges: {e}")
        return False

# Enhanced Error Handler
class ZTalonError(Exception):
    """Custom exception class for ZTalon-specific errors"""
    def __init__(self, message: str, error_code: Optional[int] = None, details: Optional[Dict] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = time.time()

def handle_error(func: Callable) -> Callable:
    """
    Decorator for enhanced error handling with logging
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error in {func.__name__}: {e}"
            logging.error(error_msg)
            
            # Create detailed error info
            error_details = {
                'function': func.__name__,
                'args': str(args)[:100],  # Truncate long args
                'kwargs': str(kwargs)[:100],
                'exception_type': type(e).__name__,
                'timestamp': time.time()
            }
            
            raise ZTalonError(error_msg, details=error_details) from e
    
    return wrapper

# Enhanced File Verification
def verify_file_integrity(file_path: str, expected_hash: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify file integrity with multiple hash algorithms
    """
    if not os.path.exists(file_path):
        return {'valid': False, 'error': 'File not found'}
    
    try:
        # Calculate hashes
        hash_md5 = hashlib.md5()
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_md5.update(chunk)
                hash_sha256.update(chunk)
        
        result = {
            'valid': True,
            'file_size': os.path.getsize(file_path),
            'md5': hash_md5.hexdigest(),
            'sha256': hash_sha256.hexdigest(),
            'path': file_path
        }
        
        # Verify against expected hash if provided
        if expected_hash:
            expected_hash = expected_hash.lower().strip()
            if len(expected_hash) == 32:  # MD5
                result['hash_match'] = result['md5'] == expected_hash
            elif len(expected_hash) == 64:  # SHA256
                result['hash_match'] = result['sha256'] == expected_hash
            else:
                result['hash_match'] = False
                result['error'] = 'Invalid expected hash format'
        
        return result
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}

# Enhanced Temp Directory Management
def get_secure_temp_dir() -> str:
    """
    Get a secure temporary directory for ZTalon operations
    """
    base_temp = tempfile.gettempdir()
    ztalon_temp = os.path.join(base_temp, "ztalon_secure")
    
    try:
        os.makedirs(ztalon_temp, mode=0o700, exist_ok=True)  # Restrictive permissions
        
        # Test write access
        test_file = os.path.join(ztalon_temp, "_write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        
        logging.info(f"Using secure temp directory: {ztalon_temp}")
        return ztalon_temp
        
    except Exception as e:
        logging.warning(f"Could not create secure temp dir: {e}")
        # Fallback to standard temp
        return tempfile.gettempdir()

# System Information Gatherer
def get_system_info() -> Dict[str, Any]:
    """
    Gather comprehensive system information for debugging
    """
    import platform
    import psutil
    
    try:
        info = {
            'os': {
                'name': os.name,
                'platform': platform.platform(),
                'version': platform.version(),
                'architecture': platform.architecture(),
                'machine': platform.machine(),
                'processor': platform.processor()
            },
            'python': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation(),
                'executable': sys.executable
            },
            'system': {
                'cpu_count': os.cpu_count(),
                'memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'disk_free_gb': round(psutil.disk_usage('/').free / (1024**3), 2)
            },
            'ztalon': {
                'admin_privileges': check_admin_privileges(),
                'temp_dir': get_secure_temp_dir(),
                'ssl_support': True  # Always True with certifi
            }
        }
        
        return info
        
    except ImportError:
        # Fallback if psutil not available
        return {
            'os': {'platform': platform.platform()},
            'python': {'version': platform.python_version()},
            'ztalon': {'admin_privileges': check_admin_privileges()}
        }
    except Exception as e:
        logging.error(f"Failed to gather system info: {e}")
        return {'error': str(e)}

# Enhanced Logger Setup
def setup_enhanced_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup enhanced logging with rotation and formatting
    """
    logger = logging.getLogger('ztalon')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler with rotation
        log_file = os.path.join(get_secure_temp_dir(), "ztalon_enhanced.log")
        
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file, maxBytes=5*1024*1024, backupCount=3
            )
        except ImportError:
            # Fallback to basic file handler
            file_handler = logging.FileHandler(log_file, mode='a')
        
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger

# Export main utilities
__all__ = [
    'create_ssl_context',
    'download_with_ssl', 
    'check_admin_privileges',
    'handle_error',
    'ZTalonError',
    'verify_file_integrity',
    'get_secure_temp_dir',
    'get_system_info',
    'setup_enhanced_logging'
]