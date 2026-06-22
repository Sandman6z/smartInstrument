import pyvisa
import time
import logging
import threading
from ..config import Config
from ..connection import ConnectionManager
from .load import IT8811
from .multimeter import DMM6500, Keysight34461A

class DeviceController:
    # 设备配置定义
    DEVICE_CONFIGS = {
        'it8811': {
            'keywords': ['IT8811'],
            'driver_class': IT8811,
            'attr_name': 'it8811', # 对应 self.it8811
            'display_name': 'ITECH IT8811',
            'usb_id_check': lambda r: Config.IT8811_USB_ID.split("::")[0] in r and Config.IT8811_USB_ID.split("::")[1] in r,
            'probe_targets': [] # IT8811 主要是 USB，暂无主动探测 IP
        },
        'dmm6500': {
            'keywords': ['DMM6500'],
            'driver_class': DMM6500,
            'attr_name': 'dmm6500',
            'display_name': 'KEITHLEY DMM6500',
            'lan_ip_check': lambda r: Config.DMM6500_IP in r,
            'probe_targets': [f"TCPIP0::{Config.DMM6500_IP}::inst0::INSTR"]
        },
        'keysight_34461a': {
            'keywords': ['34461A'],
            'driver_class': Keysight34461A,
            'attr_name': 'keysight_34461a',
            'display_name': 'KEYSIGHT 34461A',
            'probe_targets': [
                f"TCPIP0::{Config.KEYSIGHT_HOSTNAME}::inst0::INSTR",
                f"TCPIP0::{Config.KEYSIGHT_HOSTNAME}::hislip0::INSTR"
            ]
        }
    }

    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.connection_manager = ConnectionManager(self.rm)
        self.it8811 = None
        self.dmm6500 = None
        self.keysight_34461a = None
        self._connecting_lock = threading.Lock()
    
    @property
    def it8811_connected(self):
        return self.it8811.connected if self.it8811 else False

    @property
    def dmm6500_connected(self):
        return self.dmm6500.connected if self.dmm6500 else False

    @property
    def keysight_34461a_connected(self):
        return self.keysight_34461a.connected if self.keysight_34461a else False

    def scan_devices(self, on_device_found=None):
        """委托 ConnectionManager 执行扫描"""
        return self.connection_manager.scan_devices(on_device_found)

    def _connect_device(self, device_key, resource):
        """通用连接方法"""
        with self._connecting_lock:
            config = self.DEVICE_CONFIGS.get(device_key)
            if not config:
                return False, f"未知设备类型: {device_key}"

            try:
                # 实例化驱动类
                driver = config['driver_class'](self.rm, resource)
                success, msg = driver.connect()

                if success:
                    # 设置到对应的属性上 (self.it8811 等)
                    setattr(self, config['attr_name'], driver)

                return success, msg
            except Exception as e:
                return False, f"连接失败: {str(e)}"

    def _disconnect_device(self, device_key):
        """通用断开方法"""
        with self._connecting_lock:
            config = self.DEVICE_CONFIGS.get(device_key)
            if not config:
                return True, "未知设备"

            driver = getattr(self, config['attr_name'])
            if driver:
                result = driver.disconnect()
                # 断开后不置为 None，保持对象存在但 connected=False，或者根据需求处理
                # 这里参考原逻辑，原逻辑只是调用 disconnect，对象还在
                return result
            return True, "Already disconnected"

    # --- 具体设备的包装方法 (保持兼容性) ---

    def connect_it8811(self, resource):
        return self._connect_device('it8811', resource)

    def disconnect_it8811(self):
        return self._disconnect_device('it8811')

    def connect_dmm6500(self, resource):
        return self._connect_device('dmm6500', resource)

    def disconnect_dmm6500(self):
        return self._disconnect_device('dmm6500')

    def connect_keysight_34461a(self, resource):
        return self._connect_device('keysight_34461a', resource)

    def disconnect_keysight_34461a(self):
        return self._disconnect_device('keysight_34461a')

    # --- 控制方法 ---

    def set_resistance(self, value):
        if not self.it8811_connected: return False, "Not connected"
        return self.it8811.set_resistance(value)

    def set_load_mode(self, mode):
        if not self.it8811_connected: return False, "Not connected"
        return self.it8811.set_mode(mode)

    def set_load_value(self, mode, value):
        if not self.it8811_connected: return False, "Not connected"
        return self.it8811.set_value(mode, value)

    def toggle_output(self, state):
        if not self.it8811_connected: return False, "Not connected"
        return self.it8811.toggle_output(state)

    def get_resistance(self):
        if not self.it8811_connected: return False, "Not connected"
        return self.it8811.get_resistance()

    def get_voltage(self):
        if not self.dmm6500_connected: return False, "Not connected"
        return self.dmm6500.get_voltage()

    def get_current(self):
        if not self.keysight_34461a_connected: return False, "Not connected"
        return self.keysight_34461a.get_current()
        
    def get_all_measurements(self, default_resistance=None):
        """并行获取所有测量数据"""
        import concurrent.futures
        
        results = {
            'resistance': (False, default_resistance),
            'voltage': (False, "N/A"),
            'current': (False, "N/A")
        }
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_res = None
            future_volt = None
            future_curr = None
            
            # 提交任务
            if self.it8811_connected:
                future_res = executor.submit(self.it8811.get_resistance)
            
            if self.dmm6500_connected:
                future_volt = executor.submit(self.dmm6500.get_voltage)
                
            if self.keysight_34461a_connected:
                future_curr = executor.submit(self.keysight_34461a.get_current)
            
            # 获取结果
            if future_res:
                try:
                    results['resistance'] = future_res.result(timeout=2)
                except Exception as e:
                    logging.error(f"获取电阻超时或失败: {e}")
            
            if future_volt:
                try:
                    results['voltage'] = future_volt.result(timeout=2)
                except Exception as e:
                    logging.error(f"获取电压超时或失败: {e}")
                    
            if future_curr:
                try:
                    results['current'] = future_curr.result(timeout=2)
                except Exception as e:
                    logging.error(f"获取电流超时或失败: {e}")
                    
        return results
