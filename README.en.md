[中文版本](README.md) | English

# Automated Test Tool

## Project Overview

This is an automated test tool for electronic test equipment, providing an intuitive GUI interface for device control and data collection. It supports IT8811 (electronic load), DMM6500 (digital multimeter), and KEYSIGHT 34461A (multimeter) devices.

## Main Features

- **Device Auto-scan and Recognition**: Automatically scans available VISA devices and prioritizes LAN-connected devices
- **Device Connection Management**: Supports connection and disconnection operations for IT8811, DMM6500, and KEYSIGHT 34461A
- **IT8811 Control**:
  - Resistance value setting (supports input box and slider adjustment, range 10-7500Ω)
  - Output switch control (slide toggle button)
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
# Install dependencies using pip
pip install -r requirements.txt

# Or install dependencies using uv
uv install
```

### 2. Run the Application

```bash
python run.py
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

## Device Requirements

- IT8811 electronic load device
- DMM6500 digital multimeter device
- KEYSIGHT 34461A multimeter device (optional)
- VISA driver (needs to be installed in advance)

## Dependencies

- pyvisa>=1.14.0: For device communication
- openpyxl>=3.1.0: For Excel file operations

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