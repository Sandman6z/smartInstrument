[中文版本](README.md) | English

# Automated Test Tool

## Project Overview

This is an automated test tool for IT8811 (electronic load) and DMM6500 (digital multimeter) devices, providing an intuitive GUI interface for device control and data collection.

## Main Features

- **Device Auto-scan and Recognition**: Automatically scans available VISA devices and identifies IT8811 and DMM6500 devices
- **Device Connection Management**: Supports connection and disconnection operations for IT8811 and DMM6500
- **IT8811 Control**:
  - Resistance value setting (supports input box and slider adjustment)
  - Output switch control (slide toggle button)
- **DMM6500 Measurement**: Real-time voltage measurement
- **Data Recording**:
  - Manual trigger data collection
  - Real-time data display in table
  - Data saving to Excel and CSV files
- **Real-time Logging**: Operation logs output in real-time

## Technical Features

- Uses tkinter to build an intuitive GUI interface
- Uses pyvisa library for device communication
- Uses openpyxl library for Excel file operations
- Uses multi-threading for device communication to avoid UI blocking
- Has good error handling and logging mechanisms
- Supports multiple device command formats to improve compatibility

## Project Structure

```
smartInstrument/
├── src/                    # Source code directory
│   ├── smart_instrument/   # Main package directory
│   │   ├── __init__.py     # Package initialization file
│   │   ├── main.py         # Main entry file, containing GUI interface and main business logic
│   │   ├── config.py       # Configuration file, storing default configuration parameters
│   │   ├── device/         # Device-related modules
│   │   │   ├── __init__.py
│   │   │   └── controller.py  # Device control module, responsible for device communication
│   │   ├── data/           # Data-related modules
│   │   │   ├── __init__.py
│   │   │   └── manager.py     # Data management module, responsible for data recording and file export
│   │   └── gui/            # GUI-related modules
│   │       └── __init__.py
├── README.md               # Project description document (Chinese)
├── README.en.md            # Project description document (English)
├── run.py                  # Startup script
├── pyproject.toml          # Project dependencies and configuration file
├── requirements.txt        # Dependency list file
└── .gitignore              # Git ignore file configuration
```

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

1. After starting the application, the system will automatically scan for available VISA devices
2. Select and connect IT8811 and DMM6500 devices
3. Set the resistance value of IT8811 (via input box or slider)
4. Control the output switch of IT8811
5. Click the "Manual Trigger Record" button to collect data
6. Data will be displayed in the table in real-time
7. Click the "Save Data to CSV" button to save data

## Device Requirements

- IT8811 electronic load device
- DMM6500 digital multimeter device
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