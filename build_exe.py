import PyInstaller.__main__
import shutil
import os

def build():
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')

    print("Building executable...")
    
    PyInstaller.__main__.run([
        'entry_point.py',
        '--name=SmartInstrument',
        '--onefile',
        '--windowed',
        '--clean',
        '--noconfirm',
        # Ensure we pick up the package structure
        '--paths=src',
    ])
    
    print("Build complete. check dist/SmartInstrument.exe")

if __name__ == "__main__":
    build()