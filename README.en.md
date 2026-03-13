[中文版本](README.md) | English

# Automated Test Tool

## Project Overview

This is an automated test tool for electronic test equipment, providing an intuitive GUI interface for device control and data collection. It supports IT8811 (electronic load), DMM6500 (digital multimeter), and KEYSIGHT 34461A (multimeter) devices.

## Main Features

- **Device Auto-scan and Recognition**: Automatically scans available VISA devices and prioritizes LAN-connected devices
- **Device Connection Management**: Supports connection and disconnection operations for IT8811, DMM6500, and KEYSIGHT 34461A
- **IT8811 Control**:
  - Resistance value setting (supports input box and slider adjustment, range 0-7500Ω)
  - Output switch control (supports ON/OFF toggling)
- **DMM6500 Measurement**: Real-time voltage measurement
- **KEYSIGHT 34461A Measurement**: Real-time current measurement (automatically converted to μA unit)
- **Data Recording**:
  - Manual trigger data collection
  - Real-time data display in table
  - Data saving to CSV files
  - Support for clearing test data
- **Real-time Logging**: Operation logs output in real-time

## Technical Features

- Uses tkinter to build an intuitive GUI interface
- Uses pyvisa library for device communication
- Uses multi-threading for device communication to avoid UI blocking
- Has good error handling and logging mechanisms
- Supports multiple device command formats to improve compatibility
- Intelligent device recognition, prioritizing LAN-connected devices

## Installation and Usage

### 1. Install Dependencies

```bash
# Install dependencies using uv (Recommended)
uv sync

# Or install dependencies using pip
pip install -r requirements.txt
```

### 2. Run the Application

```bash
# Run using uv
uv run smart_instrument

# Or run entry point script directly
python entry_point.py
```

### 3. Usage Steps

1. After starting the application, the system will automatically scan for available VISA devices and try to automatically connect to identified devices
2. If not automatically connected, you can manually select and connect IT8811, DMM6500, and KEYSIGHT 34461A devices
3. Set the resistance value of IT8811 (via input box or slider adjustment)
4. Control the output switch of IT8811
5. Click the "Manual Trigger Record" button to collect data
6. Data will be displayed in the table in real-time
7. Click the "Save Data to CSV" button to save data
8. To clear data, click the "Clear Test Data" button

## Packaging and Distribution

This project provides two ways to package the application into a standalone EXE executable.

### Method 1: PyInstaller (Standard)

Using PyInstaller for packaging, good compatibility, but larger file size.

1. **Install Dependencies**
   ```bash
   uv add --dev pyinstaller
   ```

2. **Build**
   ```bash
   uv run python scripts/build_exe.py
   ```

3. **Get Result**
   - Output: `dist/SmartInstrument.exe`
   - Note: Includes full Python runtime, size ~35MB+.

### Method 2: Nuitka (Recommended)

Using Nuitka to compile Python code to C code then package, **faster execution, smaller file size**.

1. **Install Dependencies**
   ```bash
   uv add --dev nuitka zstandard
   ```

2. **Build**
   ```bash
   uv run python scripts/build_nuitka.py
   ```
   > Note: First run may take time as Nuitka downloads the C compiler.

3. **Get Result**
   - Output: `dist_nuitka/SmartInstrument.exe`
   - Note: Optimized and compressed, size ~10MB.
   - Features: Faster startup, harder to reverse engineer.

### Packaging Notes

1. **Driver Dependency**: The generated EXE does **NOT** include VISA drivers. Users must install [NI-VISA](https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html) or Keysight IO Libraries to connect to instruments.
2. **Antivirus**: Programs compiled with Nuitka may be flagged by some antivirus software. Add to trust list if needed.
3. **Permissions**: Run the software in a directory with read/write permissions (e.g., Desktop) to save CSV data files properly.

## Device Requirements

- IT8811 electronic load device
- DMM6500 digital multimeter device
- KEYSIGHT 34461A multimeter device (optional)
- VISA driver (needs to be installed in advance)

## Dependencies

- pyvisa>=1.14.0: For device communication
- tkinter: GUI support (Python built-in)

## Notes

1. Ensure that the VISA driver is correctly installed
2. Ensure that the devices are correctly connected to the computer
3. Ensure that you understand the basic operation methods of the devices before operating them
4. Do not disconnect the devices during data collection

## Troubleshooting

- **Device Not Found**: Check device connection and VISA driver installation
- **Connection Failed**: Check if the device address is correct and if the device is working properly
- **Command Execution Failed**: The device may be in an abnormal state, try reconnecting the device
- **Data Collection Timeout**: Check the device response time, you may need to adjust the timeout setting

## Version History

- v0.1.0: Initial version

## License

MIT License