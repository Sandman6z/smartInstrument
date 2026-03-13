import pyvisa
import time
import logging
from ..config import Config
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
        # 初始化VISA资源管理器
        self.rm = pyvisa.ResourceManager()
        # 设备对象
        self.it8811 = None
        self.dmm6500 = None
        self.keysight_34461a = None
    
    @property
    def it8811_connected(self):
        return self.it8811.connected if self.it8811 else False

    @property
    def dmm6500_connected(self):
        return self.dmm6500.connected if self.dmm6500 else False

    @property
    def keysight_34461a_connected(self):
        return self.keysight_34461a.connected if self.keysight_34461a else False

    def scan_devices(self):
        """扫描可用的VISA设备，优先识别LAN连接的设备"""
        try:
            resources = self.rm.list_resources()
            
            device_info = {} # display_text -> resource
            device_list = [] # [display_text]
            
            # 临时存储扫描到的设备资源，结构: { 'it8811': {'LAN': '...', 'USB': '...'}, ... }
            found_devices = {k: {'LAN': None, 'USB': None} for k in self.DEVICE_CONFIGS}
            
            # 1. 遍历扫描到的资源
            for resource in resources:
                if resource.startswith("ASRL"):
                    logging.info(f"跳过串口设备: {resource}")
                    continue

                logging.info(f"扫描设备: {resource}")
                idn = self._get_idn(resource)
                connection_type = "LAN" if "TCPIP" in resource else "USB"
                
                matched_key = None
                display_text = ""

                if idn:
                    # 基于 IDN 识别
                    manufacturer = idn.split(',')[0].strip() if ',' in idn else ""
                    model = idn.split(',')[1].strip() if ',' in idn and len(idn.split(',')) > 1 else idn
                    display_text = f"{manufacturer} {model} ({connection_type}: {resource.split('::')[0]})"
                    
                    for key, config in self.DEVICE_CONFIGS.items():
                        if any(kw in model or kw in idn for kw in config['keywords']):
                            matched_key = key
                            break
                else:
                    # 基于地址特征识别
                    display_text = f"Unknown Device ({connection_type}: {resource.split('::')[0]})"
                    for key, config in self.DEVICE_CONFIGS.items():
                        # 检查 USB ID
                        if connection_type == "USB" and 'usb_id_check' in config and config['usb_id_check'](resource):
                            matched_key = key
                            display_text = f"{config['display_name']} ({connection_type}: {resource.split('::')[0]})"
                            break
                        # 检查 LAN IP
                        if connection_type == "LAN" and 'lan_ip_check' in config and config['lan_ip_check'](resource):
                            matched_key = key
                            display_text = f"{config['display_name']} ({connection_type}: {resource.split('::')[0]})"
                            break

                # 记录设备
                device_list.append(display_text)
                device_info[display_text] = resource
                
                if matched_key:
                    logging.info(f"  识别为 {matched_key} ({connection_type})")
                    found_devices[matched_key][connection_type] = display_text
                else:
                    logging.info(f"  未匹配已知设备: {display_text}")

            # 2. 主动探测 (针对未扫描到的 LAN 设备)
            for key, config in self.DEVICE_CONFIGS.items():
                if not found_devices[key]['LAN'] and 'probe_targets' in config:
                    for target_addr in config['probe_targets']:
                        # 如果已经在扫描列表中，跳过
                        if any(target_addr in res for res in device_info.values()):
                            continue
                            
                        logging.info(f"尝试主动探测 {key}: {target_addr}")
                        if self._probe_device(target_addr, config['keywords']):
                            # 探测成功
                            display_text = f"{config['display_name']} (LAN: {target_addr.split('::')[1]})"
                            device_list.append(display_text)
                            device_info[display_text] = target_addr
                            found_devices[key]['LAN'] = display_text
                            break # 找到一个即可

            # 3. 汇总结果 (优先 LAN)
            final_devices = {}
            for key in self.DEVICE_CONFIGS:
                final_devices[key] = found_devices[key]['LAN'] or found_devices[key]['USB']
                if final_devices[key]:
                    logging.info(f"最终选择 {key}: {final_devices[key]}")

            return (
                device_list, 
                device_info, 
                final_devices['it8811'], 
                final_devices['dmm6500'], 
                final_devices['keysight_34461a']
            )

        except Exception as e:
            logging.error(f"扫描设备失败: {str(e)}")
            return [], {}, None, None, None

    def _get_idn(self, resource):
        """辅助方法：获取 IDN"""
        try:
            dev = self.rm.open_resource(resource)
            dev.timeout = Config.CONNECTION_TIMEOUT
            idn = None
            for i in range(3): # 重试3次
                try:
                    idn = dev.query("*IDN?").strip()
                    break
                except:
                    time.sleep(0.5)
            dev.close()
            return idn
        except:
            return None

    def _probe_device(self, resource, keywords):
        """辅助方法：探测特定设备"""
        try:
            dev = self.rm.open_resource(resource)
            dev.timeout = 2000
            idn = dev.query("*IDN?").strip()
            dev.close()
            return any(kw in idn for kw in keywords)
        except:
            return False

    def _connect_device(self, device_key, resource):
        """通用连接方法"""
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
