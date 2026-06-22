"""设备连接相关的数据模型"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeviceEntry:
    """单个 VISA 资源探测结果"""
    device_key: str           # 'it8811', 'dmm6500', 'keysight_34461a'
    display_name: str         # UI 显示名
    resource: str             # VISA 资源字符串
    connection_type: str      # 'USB' | 'LAN'
    serial_number: str        # 从 *IDN? 解析的序列号
    idn_response: str         # 完整 *IDN? 响应
    manufacturer: str = ""    # 厂商名
    model: str = ""           # 型号
    is_ghost: bool = False    # 是否为幽灵设备（探测成功但后续连接失败）


@dataclass
class ScanResult:
    """一次完整的扫描结果"""
    device_list: list = field(default_factory=list)
    device_info: dict = field(default_factory=dict)
    device_entries: list = field(default_factory=list)
    it8811_dev: Optional[str] = None
    dmm6500_dev: Optional[str] = None
    keysight_dev: Optional[str] = None
    identified: dict = field(default_factory=dict)


@dataclass
class ConnectResult:
    """连接结果"""
    device_key: str
    success: bool
    message: str
    display_name: str = ""
