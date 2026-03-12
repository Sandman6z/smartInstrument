import pyvisa
import time
import logging
from ..config import Config
from .load import IT8811
from .multimeter import DMM6500, Keysight34461A

class DeviceController:
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
            
            # 存储设备地址和IDN信息的映射
            device_info = {}
            device_list = []
            
            # 存储找到的设备，按连接类型分类
            it8811_lan_device = None
            it8811_usb_device = None
            dmm6500_lan_device = None
            dmm6500_usb_device = None
            keysight_34461a_lan_device = None
            keysight_34461a_usb_device = None
            
            # 获取每个设备的IDN信息
            for resource in resources:
                # 跳过ASRL（串口）资源，防止扫描卡顿
                if resource.startswith("ASRL"):
                    logging.info(f"跳过串口设备: {resource}")
                    continue

                logging.info(f"开始扫描设备: {resource}")
                try:
                    dev = self.rm.open_resource(resource)
                    # 设置合理的超时时间，既不过长也不过短
                    dev.timeout = Config.CONNECTION_TIMEOUT
                    
                    # 尝试获取IDN信息，最多重试5次
                    idn = None
                    retry_count = 0
                    max_retries = 5
                    
                    while retry_count < max_retries and idn is None:
                        try:
                            logging.info(f"  尝试获取IDN (第{retry_count + 1}次)")
                            # 使用query方法代替单独的write-read操作，避免缓冲区同步问题
                            idn = dev.query("*IDN?").strip()
                            logging.info(f"  IDN获取成功: {idn}")
                        except Exception as e:
                            logging.info(f"  获取IDN失败: {str(e)}")
                            retry_count += 1
                            time.sleep(1.0)  # 增加延迟时间到1秒，给设备更多恢复时间
                    
                    dev.close()
                    
                    if idn:
                        # 解析IDN信息，提取制造商和型号
                        idn_parts = idn.split(',')
                        if len(idn_parts) >= 2:
                            manufacturer = idn_parts[0].strip()
                            model = idn_parts[1].strip()
                            # 构建更清晰的显示文本，包含连接类型
                            connection_type = "LAN" if "TCPIP" in resource else "USB"
                            display_text = f"{manufacturer} {model} ({connection_type}: {resource.split('::')[0]})"
                            
                            # 识别IT8811、DMM6500和KEYSIGHT 34461A设备，并按连接类型分类
                            logging.info(f"  制造商: {manufacturer}, 型号: {model}, 连接类型: {connection_type}")
                            if "IT8811" in model or "IT8811" in idn:
                                logging.info(f"  识别为IT8811设备")
                                if "TCPIP" in resource:
                                    it8811_lan_device = display_text
                                else:
                                    it8811_usb_device = display_text
                            elif "DMM6500" in model or "DMM6500" in idn:
                                logging.info(f"  识别为DMM6500设备")
                                if "TCPIP" in resource:
                                    dmm6500_lan_device = display_text
                                else:
                                    dmm6500_usb_device = display_text
                            elif "34461A" in model or "34461A" in idn:
                                logging.info(f"  识别为KEYSIGHT 34461A设备")
                                if "TCPIP" in resource:
                                    keysight_34461a_lan_device = display_text
                                else:
                                    keysight_34461a_usb_device = display_text
                        else:
                            # 如果IDN格式不正确，使用原始IDN
                            connection_type = "LAN" if "TCPIP" in resource else "USB"
                            display_text = f"{idn} ({connection_type}: {resource.split('::')[0]})"
                        
                        device_list.append(display_text)
                        device_info[display_text] = resource
                        logging.info(f"设备信息: {display_text}")
                    else:
                        # 如果无法获取IDN，尝试基于设备地址特征识别设备
                        connection_type = "LAN" if "TCPIP" in resource else "USB"
                        logging.info(f"无法获取设备IDN，只显示地址: {resource}")
                        
                        # 检查是否是IT8811设备（基于USB地址特征）
                        is_it8811 = False
                        usb_id_parts = Config.IT8811_USB_ID.split("::")
                        if "USB" in connection_type and usb_id_parts[0] in resource and usb_id_parts[1] in resource:
                            logging.info(f"  基于USB地址特征识别为IT8811设备")
                            is_it8811 = True
                        
                        # 检查是否是DMM6500设备（基于LAN地址特征）
                        is_dmm6500 = False
                        if "LAN" in connection_type and Config.DMM6500_IP in resource:
                            logging.info(f"  基于LAN地址特征识别为DMM6500设备")
                            is_dmm6500 = True
                        
                        if is_it8811:
                            display_text = f"ITECH IT8811 ({connection_type}: {resource.split('::')[0]})"
                            device_list.append(display_text)
                            device_info[display_text] = resource
                            # 更新IT8811设备变量
                            if "TCPIP" in resource:
                                it8811_lan_device = display_text
                            else:
                                it8811_usb_device = display_text
                        elif is_dmm6500:
                            display_text = f"KEITHLEY DMM6500 ({connection_type}: {resource.split('::')[0]})"
                            device_list.append(display_text)
                            device_info[display_text] = resource
                            # 更新DMM6500设备变量
                            if "TCPIP" in resource:
                                dmm6500_lan_device = display_text
                            else:
                                dmm6500_usb_device = display_text
                        else:
                            display_text = f"Unknown Device ({connection_type}: {resource.split('::')[0]})"
                            device_list.append(display_text)
                            device_info[display_text] = resource
                except Exception as e:
                    # 如果无法获取IDN，只显示地址
                    connection_type = "LAN" if "TCPIP" in resource else "USB"
                    logging.info(f"获取设备IDN失败 {resource}: {str(e)}")
                    
                    # 尝试基于设备地址特征识别DMM6500设备
                    is_dmm6500 = False
                    if "LAN" in connection_type and Config.DMM6500_IP in resource:
                        logging.info(f"  基于LAN地址特征识别为DMM6500设备")
                        is_dmm6500 = True
                    
                    if is_dmm6500:
                        display_text = f"KEITHLEY DMM6500 ({connection_type}: {resource.split('::')[0]})"
                        device_list.append(display_text)
                        device_info[display_text] = resource
                        # 更新DMM6500设备变量
                        if "TCPIP" in resource:
                            dmm6500_lan_device = display_text
                        else:
                            dmm6500_usb_device = display_text
                    else:
                        display_text = f"Unknown Device ({connection_type}: {resource.split('::')[0]})"
                        device_list.append(display_text)
                        device_info[display_text] = resource
            
            # ---------------------------------------------------------
            # 主动探测机制：防止 VISA 自动扫描漏掉网络设备
            # ---------------------------------------------------------
            
            # 1. 探测 Keysight 34461A (通过主机名)
            if not keysight_34461a_lan_device:
                logging.info("未扫描到 Keysight LAN 设备，尝试主动探测...")
                # 优先尝试 inst0 (兼容性更好)，也可以尝试 hislip0
                target_addrs = [
                    f"TCPIP0::{Config.KEYSIGHT_HOSTNAME}::inst0::INSTR",
                    f"TCPIP0::{Config.KEYSIGHT_HOSTNAME}::hislip0::INSTR"
                ]
                
                for addr in target_addrs:
                    # 检查是否已经扫描到了
                    if any(addr in res for res in device_info.values()):
                        continue
                        
                    try:
                        logging.info(f"  尝试连接: {addr}")
                        dev = self.rm.open_resource(addr)
                        dev.timeout = 2000  # 2秒超时
                        idn = dev.query("*IDN?").strip()
                        dev.close()
                        
                        if "34461A" in idn:
                            logging.info(f"  主动探测成功: {idn}")
                            display_text = f"KEYSIGHT 34461A (LAN: {addr.split('::')[1]})"
                            device_list.append(display_text)
                            device_info[display_text] = addr
                            keysight_34461a_lan_device = display_text
                            # 找到一个就够了
                            break
                    except Exception as e:
                        logging.info(f"  探测失败: {e}")

            # 2. 探测 DMM6500 (通过 IP)
            if not dmm6500_lan_device:
                logging.info("未扫描到 DMM6500 LAN 设备，尝试主动探测...")
                target_addr = f"TCPIP0::{Config.DMM6500_IP}::inst0::INSTR"
                
                if not any(target_addr in res for res in device_info.values()):
                    try:
                        logging.info(f"  尝试连接: {target_addr}")
                        dev = self.rm.open_resource(target_addr)
                        dev.timeout = 2000
                        idn = dev.query("*IDN?").strip()
                        dev.close()
                        
                        if "DMM6500" in idn:
                            logging.info(f"  主动探测成功: {idn}")
                            display_text = f"KEITHLEY DMM6500 (LAN: {Config.DMM6500_IP})"
                            device_list.append(display_text)
                            device_info[display_text] = target_addr
                            dmm6500_lan_device = display_text
                    except Exception as e:
                        logging.info(f"  探测失败: {e}")

            # 优先选择LAN连接的设备
            it8811_device = it8811_lan_device or it8811_usb_device
            dmm6500_device = dmm6500_lan_device or dmm6500_usb_device
            keysight_34461a_device = keysight_34461a_lan_device or keysight_34461a_usb_device
            
            logging.info(f"扫描完成，找到设备数量: {len(device_list)}")
            logging.info(f"找到的设备: {device_list}")
            logging.info(f"识别到的IT8811 (LAN): {it8811_lan_device}")
            logging.info(f"识别到的IT8811 (USB): {it8811_usb_device}")
            logging.info(f"识别到的DMM6500 (LAN): {dmm6500_lan_device}")
            logging.info(f"识别到的DMM6500 (USB): {dmm6500_usb_device}")
            logging.info(f"识别到的KEYSIGHT 34461A (LAN): {keysight_34461a_lan_device}")
            logging.info(f"识别到的KEYSIGHT 34461A (USB): {keysight_34461a_usb_device}")
            logging.info(f"最终选择的IT8811: {it8811_device}")
            logging.info(f"最终选择的DMM6500: {dmm6500_device}")
            logging.info(f"最终选择的KEYSIGHT 34461A: {keysight_34461a_device}")
            
            return device_list, device_info, it8811_device, dmm6500_device, keysight_34461a_device
        except Exception as e:
            logging.info(f"扫描设备失败: {str(e)}")
            return [], {}, None, None, None
    
    def connect_it8811(self, resource):
        self.it8811 = IT8811(self.rm, resource)
        return self.it8811.connect()

    def disconnect_it8811(self):
        if self.it8811:
            return self.it8811.disconnect()
        return True, "Already disconnected"

    def connect_dmm6500(self, resource):
        self.dmm6500 = DMM6500(self.rm, resource)
        return self.dmm6500.connect()

    def disconnect_dmm6500(self):
        if self.dmm6500:
            return self.dmm6500.disconnect()
        return True, "Already disconnected"

    def connect_keysight_34461a(self, resource):
        self.keysight_34461a = Keysight34461A(self.rm, resource)
        return self.keysight_34461a.connect()

    def disconnect_keysight_34461a(self):
        if self.keysight_34461a:
            return self.keysight_34461a.disconnect()
        return True, "Already disconnected"

    def set_resistance(self, value):
        if not self.it8811_connected: return False, "Not connected"
        return self.it8811.set_resistance(value)

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
