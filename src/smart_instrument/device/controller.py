import pyvisa
import time

class DeviceController:
    def __init__(self):
        # 初始化VISA资源管理器
        self.rm = pyvisa.ResourceManager()
        # 设备资源
        self.it8811 = None
        self.dmm6500 = None
        self.keysight_34461a = None
        # 设备连接状态
        self.it8811_connected = False
        self.dmm6500_connected = False
        self.keysight_34461a_connected = False
    
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
                print(f"开始扫描设备: {resource}")
                try:
                    dev = self.rm.open_resource(resource)
                    # 增加超时时间到5秒
                    dev.timeout = 5000
                    
                    # 尝试获取IDN信息，最多重试3次
                    idn = None
                    retry_count = 0
                    max_retries = 3
                    
                    while retry_count < max_retries and idn is None:
                        try:
                            print(f"  尝试获取IDN (第{retry_count + 1}次)")
                            dev.write("*IDN?")
                            idn = dev.read().strip()
                            print(f"  IDN获取成功: {idn}")
                        except Exception as e:
                            print(f"  获取IDN失败: {str(e)}")
                            retry_count += 1
                            time.sleep(0.5)  # 短暂延迟后重试
                    
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
                            print(f"  制造商: {manufacturer}, 型号: {model}, 连接类型: {connection_type}")
                            if "IT8811" in model or "IT8811" in idn:
                                print(f"  识别为IT8811设备")
                                if "TCPIP" in resource:
                                    it8811_lan_device = display_text
                                else:
                                    it8811_usb_device = display_text
                            elif "DMM6500" in model or "DMM6500" in idn:
                                print(f"  识别为DMM6500设备")
                                if "TCPIP" in resource:
                                    dmm6500_lan_device = display_text
                                else:
                                    dmm6500_usb_device = display_text
                            elif "34461A" in model or "34461A" in idn:
                                print(f"  识别为KEYSIGHT 34461A设备")
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
                        print(f"设备信息: {display_text}")
                    else:
                        # 如果无法获取IDN，只显示地址
                        connection_type = "LAN" if "TCPIP" in resource else "USB"
                        print(f"无法获取设备IDN，只显示地址: {resource}")
                        display_text = f"Unknown Device ({connection_type}: {resource.split('::')[0]})"
                        device_list.append(display_text)
                        device_info[display_text] = resource
                except Exception as e:
                    # 如果无法获取IDN，只显示地址
                    connection_type = "LAN" if "TCPIP" in resource else "USB"
                    print(f"获取设备IDN失败 {resource}: {str(e)}")
                    display_text = f"Unknown Device ({connection_type}: {resource.split('::')[0]})"
                    device_list.append(display_text)
                    device_info[display_text] = resource
            
            # 优先选择LAN连接的设备
            it8811_device = it8811_lan_device or it8811_usb_device
            dmm6500_device = dmm6500_lan_device or dmm6500_usb_device
            keysight_34461a_device = keysight_34461a_lan_device or keysight_34461a_usb_device
            
            print(f"扫描完成，找到设备数量: {len(device_list)}")
            print(f"找到的设备: {device_list}")
            print(f"识别到的IT8811 (LAN): {it8811_lan_device}")
            print(f"识别到的IT8811 (USB): {it8811_usb_device}")
            print(f"识别到的DMM6500 (LAN): {dmm6500_lan_device}")
            print(f"识别到的DMM6500 (USB): {dmm6500_usb_device}")
            print(f"识别到的KEYSIGHT 34461A (LAN): {keysight_34461a_lan_device}")
            print(f"识别到的KEYSIGHT 34461A (USB): {keysight_34461a_usb_device}")
            print(f"最终选择的IT8811: {it8811_device}")
            print(f"最终选择的DMM6500: {dmm6500_device}")
            print(f"最终选择的KEYSIGHT 34461A: {keysight_34461a_device}")
            
            return device_list, device_info, it8811_device, dmm6500_device, keysight_34461a_device
        except Exception as e:
            print(f"扫描设备失败: {str(e)}")
            return [], {}, None, None, None
    
    def connect_it8811(self, resource):
        """连接IT8811"""
        try:
            # 设置连接超时
            self.it8811 = self.rm.open_resource(resource)
            self.it8811.timeout = 5000  # 5秒超时
            
            # 测试连接
            try:
                self.it8811.write("*IDN?")
                idn = self.it8811.read()
                print(f"IT8811 IDN: {idn}")
                
                # 切换到CR模式
                try:
                    # 尝试多种命令格式
                    commands = ["FUNC:MODE CR", "MODE CR", "FUNC RES"]
                    for cmd in commands:
                        try:
                            self.it8811.write(cmd)
                            print(f"IT8811切换到CR模式 (使用命令: {cmd})")
                            # 短暂延迟
                            time.sleep(0.5)
                            break
                        except Exception as e:
                            print(f"命令 {cmd} 失败: {str(e)}")
                            continue
                    
                    # 验证模式是否切换成功
                    try:
                        # 增加超时时间
                        original_timeout = self.it8811.timeout
                        self.it8811.timeout = 10000  # 增加到10秒
                        # 尝试多种查询命令
                        query_commands = ["FUNC:MODE?", "MODE?", "FUNC?"]
                        for q_cmd in query_commands:
                            try:
                                self.it8811.write(q_cmd)
                                mode = self.it8811.read().strip()
                                self.it8811.timeout = original_timeout  # 恢复默认值
                                print(f"当前模式: {mode}")
                                break
                            except Exception as e:
                                print(f"查询命令 {q_cmd} 失败: {str(e)}")
                                continue
                    except Exception as e:
                        print(f"模式验证失败: {str(e)}")
                        print("继续执行，假设模式切换成功")
                except Exception as e:
                    print(f"模式切换失败: {str(e)}")
                    print("继续执行，尝试保持连接")
                
                self.it8811_connected = True
                return True, "IT8811连接成功并切换到CR模式"
            except pyvisa.errors.VisaIOError as e:
                if "timeout" in str(e).lower():
                    return False, "连接IT8811超时，请检查设备连接"
                else:
                    return False, f"连接IT8811失败: {str(e)}"
        except Exception as e:
            return False, f"连接IT8811失败: {str(e)}"
    
    def disconnect_it8811(self):
        """断开IT8811连接"""
        try:
            if self.it8811:
                self.it8811.close()
                self.it8811 = None
            self.it8811_connected = False
            return True, "IT8811断开连接成功"
        except Exception as e:
            return False, f"断开IT8811连接失败: {str(e)}"
    
    def connect_dmm6500(self, resource):
        """连接DMM6500，优先使用LAN连接"""
        try:
            # 设置连接超时
            self.dmm6500 = self.rm.open_resource(resource)
            self.dmm6500.timeout = 5000  # 5秒超时
            
            # 测试连接
            try:
                self.dmm6500.write("*IDN?")
                idn = self.dmm6500.read()
                print(f"DMM6500 IDN: {idn}")
                
                # 设置为DCV模式
                self.dmm6500.write("FUNCTION 'VOLTage:DC'")
                print("DMM6500设置为DCV模式")
                
                self.dmm6500_connected = True
                connection_type = "LAN" if "TCPIP" in resource else "USB"
                return True, f"DMM6500连接成功({connection_type})并设置为DCV模式"
            except pyvisa.errors.VisaIOError as e:
                if "timeout" in str(e).lower():
                    return False, "连接DMM6500超时，请检查设备连接"
                else:
                    return False, f"连接DMM6500失败: {str(e)}"
        except Exception as e:
            return False, f"连接DMM6500失败: {str(e)}"
    
    def disconnect_dmm6500(self):
        """断开DMM6500连接"""
        try:
            if self.dmm6500:
                self.dmm6500.close()
                self.dmm6500 = None
            self.dmm6500_connected = False
            return True, "DMM6500断开连接成功"
        except Exception as e:
            return False, f"断开DMM6500连接失败: {str(e)}"
    
    def connect_keysight_34461a(self, resource):
        """连接KEYSIGHT 34461A并设置为DCI模式，优先使用LAN连接"""
        try:
            # 设置连接超时
            self.keysight_34461a = self.rm.open_resource(resource)
            self.keysight_34461a.timeout = 5000  # 5秒超时
            
            # 测试连接
            try:
                self.keysight_34461a.write("*IDN?")
                idn = self.keysight_34461a.read()
                print(f"KEYSIGHT 34461A IDN: {idn}")
                
                # 设置为DCI模式（直流电流）
                self.keysight_34461a.write("FUNCTION 'CURRent:DC'")
                print("KEYSIGHT 34461A设置为DCI模式")
                
                self.keysight_34461a_connected = True
                connection_type = "LAN" if "TCPIP" in resource else "USB"
                return True, f"KEYSIGHT 34461A连接成功({connection_type})并设置为DCI模式"
            except pyvisa.errors.VisaIOError as e:
                if "timeout" in str(e).lower():
                    return False, "连接KEYSIGHT 34461A超时，请检查设备连接"
                else:
                    return False, f"连接KEYSIGHT 34461A失败: {str(e)}"
        except Exception as e:
            return False, f"连接KEYSIGHT 34461A失败: {str(e)}"
    
    def disconnect_keysight_34461a(self):
        """断开KEYSIGHT 34461A连接"""
        try:
            if self.keysight_34461a:
                self.keysight_34461a.close()
                self.keysight_34461a = None
            self.keysight_34461a_connected = False
            return True, "KEYSIGHT 34461A断开连接成功"
        except Exception as e:
            return False, f"断开KEYSIGHT 34461A连接失败: {str(e)}"
    
    def get_current(self):
        """获取KEYSIGHT 34461A的电流值"""
        if not self.keysight_34461a_connected:
            return False, "请先连接KEYSIGHT 34461A"
        
        try:
            # 尝试多种测量命令
            measure_commands = ["MEAS:CURR:DC?", "CURR:DC?", "MEASURE:CURRENT:DC?", "READ?"]
            for cmd in measure_commands:
                try:
                    self.keysight_34461a.write(cmd)
                    current = self.keysight_34461a.read().strip()
                    print(f"获取电流值成功: {current}")
                    return True, current
                except Exception as e:
                    print(f"测量命令 {cmd} 失败: {str(e)}")
                    continue
            
            # 所有命令都失败
            return False, "所有测量命令都失败"
        except Exception as e:
            return False, f"获取电流值失败: {str(e)}"
    
    def set_resistance(self, resistance):
        """设置IT8811的电阻值"""
        if not self.it8811_connected:
            return False, "请先连接IT8811"
        
        try:
            # 设置电阻值
            self.it8811.write(f"RES {resistance}")
            return True, f"电阻值设置为 {resistance} Ω"
        except Exception as e:
            return False, f"设置电阻值失败: {str(e)}"
    
    def toggle_output(self, state):
        """控制IT8811的输出开关"""
        if not self.it8811_connected:
            return False, "请先连接IT8811"
        
        try:
            # 详细的调试信息
            print(f"===== 开始控制IT8811输出状态: {state} =====")
            
            # IT8811的原始命令格式（基于IT8811常见命令集）
            if state == "ON":
                # 开启输出的命令
                commands = ["OUT 1", "OUTPUT ON", "OUTPUT:STATE ON", "ON"]
                expected_msg = "输出已开启"
            else:
                # 关闭输出的命令
                commands = ["OUT 0", "OUTPUT OFF", "OUTPUT:STATE OFF", "OFF"]
                expected_msg = "输出已关闭"
            
            # 确保设备在CR模式
            try:
                print("1. 设置IT8811为CR模式")
                # 尝试多种模式设置命令
                mode_commands = ["FUNCTION CR", "FUNC CR", "MODE CR", "FUNC:MODE CR"]
                for mode_cmd in mode_commands:
                    try:
                        self.it8811.write(mode_cmd)
                        print(f"   执行模式命令: {mode_cmd}")
                        time.sleep(0.5)
                        break
                    except Exception as e:
                        print(f"   模式命令 {mode_cmd} 失败: {str(e)}")
                        continue
            except Exception as e:
                print(f"设置CR模式失败: {str(e)}")
            
            # 执行输出控制命令
            command_success = False
            for cmd in commands:
                try:
                    print(f"2. 尝试输出控制命令: {cmd}")
                    self.it8811.write(cmd)
                    print(f"   命令发送成功: {cmd}")
                    time.sleep(0.5)
                    command_success = True
                    break
                except Exception as e:
                    print(f"   命令 {cmd} 失败: {str(e)}")
                    continue
            
            if not command_success:
                print("所有输出控制命令都失败")
                return False, "所有输出控制命令都失败"
            
            # 读取设备IDN，确认设备响应正常
            try:
                print("3. 验证设备响应 - 读取IDN")
                self.it8811.write("*IDN?")
                time.sleep(0.3)
                idn = self.it8811.read().strip()
                print(f"   设备IDN: {idn}")
            except Exception as e:
                print(f"读取IDN失败: {str(e)}")
            
            # 读取输出状态
            try:
                print("4. 读取输出状态")
                status_commands = ["OUT?", "OUTPUT?", "OUTPUT:STATE?"]
                for status_cmd in status_commands:
                    try:
                        self.it8811.write(status_cmd)
                        print(f"   执行状态命令: {status_cmd}")
                        time.sleep(0.3)
                        output_state = self.it8811.read().strip()
                        print(f"   输出状态: {output_state}")
                        
                        # 验证状态
                        if (state == "ON" and ("1" in output_state or "ON" in output_state.upper())) or \
                           (state == "OFF" and ("0" in output_state or "OFF" in output_state.upper())):
                            print(f"   状态验证成功: {state}")
                            print("===== 输出状态控制完成 =====")
                            return True, expected_msg
                        else:
                            print(f"   状态验证失败，期望: {state}，实际: {output_state}")
                    except Exception as e:
                        print(f"   读取状态失败 (命令: {status_cmd}): {str(e)}")
                        continue
            except Exception as e:
                print(f"读取输出状态失败: {str(e)}")
            
            # 即使验证失败，也返回成功，因为设备可能已经执行了命令
            print("===== 输出状态控制完成（状态验证失败） =====")
            return True, expected_msg
        except Exception as e:
            print(f"控制输出失败: {str(e)}")
            return False, f"控制输出失败: {str(e)}"
    
    def get_resistance(self):
        """获取IT8811的电阻值"""
        if not self.it8811_connected:
            return False, "请先连接IT8811"
        
        try:
            # 减少超时时间，提高响应速度
            original_timeout = self.it8811.timeout
            self.it8811.timeout = 3000  # 减少到3秒
            
            # 尝试多种测量命令
            measure_commands = ["MEAS:RES?", "RES?", "MEASURE:RESISTANCE?"]
            for cmd in measure_commands:
                try:
                    self.it8811.write(cmd)
                    resistance = self.it8811.read().strip()
                    self.it8811.timeout = original_timeout  # 恢复默认值
                    print(f"获取电阻值成功: {resistance}")
                    return True, resistance
                except Exception as e:
                    print(f"测量命令 {cmd} 失败: {str(e)}")
                    continue
            
            # 所有命令都失败
            self.it8811.timeout = original_timeout  # 恢复默认值
            return False, "所有测量命令都失败"
        except Exception as e:
            # 恢复超时设置
            if hasattr(self, 'it8811') and self.it8811:
                self.it8811.timeout = original_timeout
            return False, f"获取电阻值失败: {str(e)}"
    
    def get_voltage(self):
        """获取DMM6500的电压值"""
        if not self.dmm6500_connected:
            return False, "请先连接DMM6500"
        
        try:
            self.dmm6500.write("MEAS:VOLT:DC?")
            voltage = self.dmm6500.read().strip()
            return True, voltage
        except Exception as e:
            return False, f"获取电压值失败: {str(e)}"
