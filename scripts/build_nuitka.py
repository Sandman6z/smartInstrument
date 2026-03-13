import os
import sys
import shutil
import subprocess

def build():
    # Clean previous builds
    if os.path.exists('dist_nuitka'):
        print("Cleaning previous build...")
        shutil.rmtree('dist_nuitka')
        
    print("Building with Nuitka...")
    
    # Nuitka command
    # Using sys.executable ensures we use the uv venv python
    cmd = [
        sys.executable,
        "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--enable-plugin=tk-inter",
        "--windows-console-mode=disable", # Hide console window
        "--output-dir=dist_nuitka",
        "--output-filename=SmartInstrument.exe",
        "--remove-output",  # Remove temporary build directory
        "--assume-yes-for-downloads", # Automatically download C compiler if needed
        # Explicitly include the source package if needed, but Nuitka usually finds it via imports
        # "--include-package=smart_instrument", 
        "entry_point.py"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\nBuild complete! Check dist_nuitka/SmartInstrument.exe")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error code {e.returncode}")

if __name__ == "__main__":
    build()