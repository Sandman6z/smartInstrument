"""设备连接管理器 - 负责扫描、识别、去重、自动连接"""
import pyvisa
import logging
import time
import threading
import concurrent.futures
from .models import DeviceEntry, ScanResult, ConnectResult
from ..config import Config
from ..device.load import IT8811
from ..device.multimeter import DMM6500, Keysight34461A


class ConnectionManager:
    """设备连接管理器

    职责：
    1. 扫描 VISA 资源并识别设备
    2. 序列号去重，过滤幽灵设备
    3. 按策略顺序/并发连接设备
    """

    # 设备配置（从 DeviceController 迁移而来）
    DEVICE_CONFIGS = {
        'it8811': {
            'keywords': ['IT8811'],
            'driver_class': IT8811,
            'attr_name': 'it8811',
            'display_name': 'ITECH IT8811',
            'connection_type': 'USB',
            'usb_id_check': lambda r: (
                Config.IT8811_USB_ID.split("::")[0] in r
                and Config.IT8811_USB_ID.split("::")[1] in r
            ),
            'probe_targets': [],
        },
        'dmm6500': {
            'keywords': ['DMM6500'],
            'driver_class': DMM6500,
            'attr_name': 'dmm6500',
            'display_name': 'KEITHLEY DMM6500',
            'connection_type': 'LAN',
            'lan_ip_check': lambda r: Config.DMM6500_IP in r,
            'probe_targets': [f"TCPIP0::{Config.DMM6500_IP}::inst0::INSTR"],
        },
        'keysight_34461a': {
            'keywords': ['34461A'],
            'driver_class': Keysight34461A,
            'attr_name': 'keysight_34461a',
            'display_name': 'KEYSIGHT 34461A',
            'connection_type': 'LAN',
            'probe_targets': [
                f"TCPIP0::{Config.KEYSIGHT_HOSTNAME}::inst0::INSTR",
                f"TCPIP0::{Config.KEYSIGHT_HOSTNAME}::hislip0::INSTR",
            ],
        },
    }

    def __init__(self, resource_manager):
        self.rm = resource_manager
        self._scan_lock = threading.Lock()

    def _get_idn(self, resource):
        """获取设备的 *IDN? 响应。修复了原版在异常时不关闭资源的问题。"""
        dev = None
        try:
            dev = self.rm.open_resource(resource)
            dev.timeout = Config.CONNECTION_TIMEOUT
            idn = None
            for i in range(3):
                try:
                    idn = dev.query("*IDN?").strip()
                    break
                except Exception:
                    time.sleep(0.5)
            return idn
        except Exception:
            return None
        finally:
            if dev:
                try:
                    dev.close()
                except Exception:
                    pass

    def _probe_device(self, resource, keywords):
        """探测指定地址是否为已知设备。修复了原版异常时泄漏资源的问题。"""
        dev = None
        try:
            dev = self.rm.open_resource(resource)
            dev.timeout = 2000
            idn = dev.query("*IDN?").strip()
            return any(kw in idn for kw in keywords)
        except Exception:
            return False
        finally:
            if dev:
                try:
                    dev.close()
                except Exception:
                    pass

    def scan_devices(self, on_device_found=None):
        """扫描 VISA 设备，序列号去重，返回结果。

        返回格式与原始 DeviceController.scan_devices 兼容：
        (device_list, device_info, it8811_dev, dmm6500_dev, keysight_dev)
        """
        if not self._scan_lock.acquire(blocking=False):
            logging.warning("扫描正在进行中，跳过重复请求")
            return [], {}, None, None, None

        try:
            resources = self.rm.list_resources()
            device_list = []
            device_info = {}
            identified_devices = {k: {'LAN': None, 'USB': None} for k in self.DEVICE_CONFIGS}
            device_entries = []

            def process_resource(resource):
                if resource.startswith("ASRL"):
                    return None

                logging.info(f"扫描设备: {resource}")
                idn = self._get_idn(resource)
                connection_type = "LAN" if "TCPIP" in resource else "USB"

                if not idn:
                    # 无 IDN 响应时，尝试用 USB ID / LAN IP 匹配
                    for key, config in self.DEVICE_CONFIGS.items():
                        if connection_type == "USB" and config.get('usb_id_check') and config['usb_id_check'](resource):
                            display_text = f"{config['display_name']} ({connection_type}: {resource.split('::')[0]})"
                            return DeviceEntry(
                                device_key=key, display_name=display_text,
                                resource=resource, connection_type=connection_type,
                                serial_number="", idn_response=""
                            ), key, display_text
                        if connection_type == "LAN" and config.get('lan_ip_check') and config['lan_ip_check'](resource):
                            display_text = f"{config['display_name']} ({connection_type}: {resource.split('::')[0]})"
                            return DeviceEntry(
                                device_key=key, display_name=display_text,
                                resource=resource, connection_type=connection_type,
                                serial_number="", idn_response=""
                            ), key, display_text
                    return None

                # 有 IDN 响应，解析
                parts = idn.split(',')
                manufacturer = parts[0].strip() if len(parts) > 0 else ""
                model = parts[1].strip() if len(parts) > 1 else idn
                serial = parts[2].strip() if len(parts) > 2 else ""

                matched_key = None
                for key, config in self.DEVICE_CONFIGS.items():
                    if any(kw in model or kw in idn for kw in config['keywords']):
                        matched_key = key
                        break

                if not matched_key:
                    display_text = f"Unknown Device ({connection_type}: {resource.split('::')[0]})"
                    return DeviceEntry(
                        device_key="unknown", display_name=display_text,
                        resource=resource, connection_type=connection_type,
                        serial_number=serial, idn_response=idn,
                        manufacturer=manufacturer, model=model
                    ), None, display_text

                config = self.DEVICE_CONFIGS[matched_key]
                display_text = f"{manufacturer} {model} ({connection_type}: {resource.split('::')[0]})"
                return DeviceEntry(
                    device_key=matched_key, display_name=display_text,
                    resource=resource, connection_type=connection_type,
                    serial_number=serial, idn_response=idn,
                    manufacturer=manufacturer, model=model
                ), matched_key, display_text

            # 线程池并发探测
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                scan_futures = [executor.submit(process_resource, res) for res in resources]

                # 主动探测任务
                for key, config in self.DEVICE_CONFIGS.items():
                    for target_addr in config.get('probe_targets', []):
                        if target_addr in resources:
                            continue
                        def make_probe(k, conf, addr):
                            if self._probe_device(addr, conf['keywords']):
                                entry = DeviceEntry(
                                    device_key=k,
                                    display_name=f"{conf['display_name']} (LAN: {addr.split('::')[1]})",
                                    resource=addr, connection_type="LAN",
                                    serial_number="", idn_response=""
                                )
                                return entry, k, entry.display_name
                            return None
                        scan_futures.append(
                            executor.submit(make_probe, key, config, target_addr)
                        )

                for future in concurrent.futures.as_completed(scan_futures):
                    try:
                        result = future.result()
                        if result is None:
                            continue
                        entry, matched_key, display_text = result

                        # 序列号去重：相同 device_key + serial_number → 只保留第一个
                        is_dup = False
                        for existing in device_entries:
                            if (existing.device_key == entry.device_key
                                    and existing.serial_number
                                    and existing.serial_number == entry.serial_number):
                                is_dup = True
                                logging.info(f"  去重: {entry.resource} 与 {existing.resource} 序列号相同，跳过")
                                break
                        if is_dup:
                            continue

                        device_entries.append(entry)

                        if display_text not in device_list:
                            device_list.append(display_text)
                            device_info[display_text] = entry.resource

                        if matched_key:
                            logging.info(f"  识别为 {matched_key} ({entry.connection_type}, SN: {entry.serial_number or 'N/A'})")
                            identified_devices[matched_key][entry.connection_type] = display_text
                        else:
                            logging.info(f"  未匹配已知设备: {display_text}")

                        if on_device_found:
                            on_device_found(display_text, entry.resource, matched_key)

                    except Exception as e:
                        logging.error(f"扫描任务异常: {e}")

            # 最终选择（优先 LAN）
            it8811_dev = identified_devices['it8811']['LAN'] or identified_devices['it8811']['USB']
            dmm_dev = identified_devices['dmm6500']['LAN'] or identified_devices['dmm6500']['USB']
            keysight_dev = identified_devices['keysight_34461a']['LAN'] or identified_devices['keysight_34461a']['USB']

            for key in self.DEVICE_CONFIGS:
                dev = identified_devices[key]['LAN'] or identified_devices[key]['USB']
                if dev:
                    logging.info(f"最终选择 {key}: {dev}")

            return device_list, device_info, it8811_dev, dmm_dev, keysight_dev

        except Exception as e:
            logging.error(f"扫描设备失败: {str(e)}")
            return [], {}, None, None, None
        finally:
            self._scan_lock.release()

    def auto_connect(self, scan_result, device_controller, on_connect=None):
        """自动连接所有已识别设备。

        Args:
            scan_result: scan_devices 返回的完整元组
            device_controller: DeviceController 实例
            on_connect: 回调函数 (device_key, success, message)
        """
        _, device_info, it8811_dev, dmm_dev, keysight_dev = scan_result
        results = []

        # Step 1: LAN 设备可并发连接（DMM6500 + Keysight）
        lan_tasks = []
        if dmm_dev:
            resource = device_info.get(dmm_dev, dmm_dev)
            lan_tasks.append(('dmm6500', resource))
        if keysight_dev:
            resource = device_info.get(keysight_dev, keysight_dev)
            lan_tasks.append(('keysight_34461a', resource))

        if lan_tasks:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as lan_executor:
                lan_futures = {}
                for key, resource in lan_tasks:
                    fut = lan_executor.submit(device_controller._connect_device, key, resource)
                    lan_futures[fut] = key

                for future in concurrent.futures.as_completed(lan_futures):
                    key = lan_futures[future]
                    try:
                        success, msg = future.result()
                        results.append((key, success, msg))
                        if on_connect:
                            on_connect(key, success, msg)
                    except Exception as e:
                        results.append((key, False, str(e)))
                        if on_connect:
                            on_connect(key, False, str(e))

        # Step 2: USB 设备顺序连接（IT8811 单独连接，消除 VISA 冲突）
        if it8811_dev:
            resource = device_info.get(it8811_dev, it8811_dev)
            try:
                success, msg = device_controller._connect_device('it8811', resource)
                results.append(('it8811', success, msg))
                if on_connect:
                    on_connect('it8811', success, msg)
            except Exception as e:
                results.append(('it8811', False, str(e)))
                if on_connect:
                    on_connect('it8811', False, str(e))

        return results
