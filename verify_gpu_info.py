import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from components import debloat_windows

print("Testing get_gpu_info_advanced()...")
try:
    gpu_info = debloat_windows.get_gpu_info_advanced()
    print(f"Result type: {type(gpu_info)}")
    print(f"Result content: {json.dumps(gpu_info, indent=2)}")
    
    if isinstance(gpu_info, list):
        print("✅ Function returned a list as expected.")
        if len(gpu_info) > 0:
            print("✅ GPU info found.")
        else:
            print("⚠️ No GPU info found (list empty), but function ran.")
    else:
        print("❌ Function did not return a list.")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error calling function: {e}")
    sys.exit(1)
