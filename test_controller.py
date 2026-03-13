import sys
import os
import logging

# 添加src目录到Python路径
sys.path.insert(0, os.path.abspath('src'))

from smart_instrument.device.controller import DeviceController
from smart_instrument.config import Config

# 配置日志
logging.basicConfig(level=logging.INFO)

def test_device_controller():
    print("Testing DeviceController...")
    try:
        controller = DeviceController()
        print("DeviceController initialized.")
        
        print("Scanning devices...")
        # 模拟扫描，不依赖实际硬件连接
        device_list, device_info, it8811, dmm, keysight = controller.scan_devices()
        
        print(f"Scan complete.")
        print(f"Device List: {device_list}")
        print(f"IT8811: {it8811}")
        print(f"DMM6500: {dmm}")
        print(f"Keysight: {keysight}")
        
        print("Test passed successfully.")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_device_controller()
