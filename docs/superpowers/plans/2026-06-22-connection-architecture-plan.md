# 设备连接架构重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构设备连接架构，消除 VISA 幽灵设备、线程竞态和阻塞对话框导致的"反复重启才能连上"问题

**Architecture:** 新增 `ConnectionManager` 组件负责设备扫描/序列号去重/自动连接；`DeviceController` 简化为外观层；GUI 添加状态栏和重新扫描按钮，移除阻塞式错误对话框

**Tech Stack:** Python 3, pyvisa, tkinter, threading

---

## 文件结构总览

```
新增:
  src/smart_instrument/connection/__init__.py   (包初始化)
  src/smart_instrument/connection/models.py     (DeviceEntry 等数据类)
  src/smart_instrument/connection/manager.py    (ConnectionManager 实现)

修改:
  src/smart_instrument/device/controller.py     (提取扫描连接逻辑)
  src/smart_instrument/gui/main_window.py       (简化扫描流程，加状态栏)
  src/smart_instrument/gui/components/connection_panel.py (加重新扫描按钮、tooltip)

不变:
  src/smart_instrument/device/base.py
  src/smart_instrument/device/load.py
  src/smart_instrument/device/multimeter.py
  src/smart_instrument/config.py
  src/smart_instrument/gui/components/control_panel.py
  src/smart_instrument/gui/components/data_panel.py
  src/smart_instrument/main.py
```

---

### Task 1: 创建连接管理目录和 models.py

**Files:**
- Create: `src/smart_instrument/connection/__init__.py`
- Create: `src/smart_instrument/connection/models.py`

- [ ] **Step 1: 创建 connection 包目录**

```bash
mkdir -p src/smart_instrument/connection
```

- [ ] **Step 2: 创建 `__init__.py`**

```python
"""设备连接管理模块"""
from .manager import ConnectionManager
from .models import DeviceEntry, ScanResult, ConnectResult

__all__ = ['ConnectionManager', 'DeviceEntry', 'ScanResult', 'ConnectResult']
```

- [ ] **Step 3: 创建 `models.py`（数据类定义）**

```python
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
    device_list: list = field(default_factory=list)      # [display_text, ...]
    device_info: dict = field(default_factory=dict)      # {display_text: resource}
    device_entries: list = field(default_factory=list)    # [DeviceEntry, ...]
    it8811_dev: Optional[str] = None                     # 最终选择的 IT8811
    dmm6500_dev: Optional[str] = None                    # 最终选择的 DMM6500
    keysight_dev: Optional[str] = None                   # 最终选择的 Keysight
    identified: dict = field(default_factory=dict)        # {device_key: [DeviceEntry, ...]}

@dataclass
class ConnectResult:
    """连接结果"""
    device_key: str
    success: bool
    message: str
    display_name: str = ""
```

- [ ] **Step 4: 提交**

```bash
git add src/smart_instrument/connection/
git commit -m "feat(connection): 添加连接管理模块基础结构和数据模型"
```

---

### Task 2: 创建 ConnectionManager（核心变更）

**Files:**
- Create: `src/smart_instrument/connection/manager.py`

此文件实现了扫描、序列号去重、自动连接三大核心功能。

- [ ] **Step 1: 编写 `ConnectionManager` 类框架（初始化+配置）**

```python
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
        self._scanning = False
```

- [ ] **Step 2: 添加 `_get_idn()` 和 `_probe_device()`（修复资源泄漏）**

```python
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
```

- [ ] **Step 3: 添加 `scan_devices()` 方法（使用序列号去重）**

```python
    def scan_devices(self, on_device_found=None):
        """扫描 VISA 设备，序列号去重，返回结果。

        返回格式与原始 DeviceController.scan_devices 兼容：
        (device_list, device_info, it8811_dev, dmm6500_dev, keysight_dev)
        """
        if self._scanning:
            logging.warning("扫描正在进行中，跳过重复请求")
            return [], {}, None, None, None

        self._scanning = True
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

            # 记录扫描结果
            for key in self.DEVICE_CONFIGS:
                dev = identified_devices[key]['LAN'] or identified_devices[key]['USB']
                if dev:
                    logging.info(f"最终选择 {key}: {dev}")

            return device_list, device_info, it8811_dev, dmm_dev, keysight_dev

        except Exception as e:
            logging.error(f"扫描设备失败: {str(e)}")
            return [], {}, None, None, None
        finally:
            self._scanning = False
```

- [ ] **Step 4: 添加 `auto_connect()` 方法（LAN 并发 + USB 顺序）**

```python
    def auto_connect(self, scan_result, device_controller, on_connect=None):
        """自动连接所有已识别设备。

        Args:
            scan_result: scan_devices 返回的完整元组 (device_list, device_info, it8811, dmm, keysight)
            device_controller: DeviceController 实例，用于执行实际连接
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
```

- [ ] **Step 5: 提交**

```bash
git add src/smart_instrument/connection/manager.py
git commit -m "feat(connection): 实现 ConnectionManager 扫描/去重/自动连接
- 序列号去重过滤幽灵设备
- _get_idn / _probe_device 修复资源泄漏（finally 确保关闭）
- auto_connect LAN 并发 + USB 顺序
- 扫描加锁防止重入"
```

---

### Task 3: 重构 DeviceController（提取扫描，保留外观）

**Files:**
- Modify: `src/smart_instrument/device/controller.py`

- [ ] **Step 1: 修改 controller.py 的 import 和 __init__**

```python
import pyvisa
import time
import logging
import threading
from ..config import Config
from ..connection import ConnectionManager
from .load import IT8811
from .multimeter import DMM6500, Keysight34461A
```

__init__ 方法变更：添加 ConnectionManager 和线程锁

```python
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.connection_manager = ConnectionManager(self.rm)
        self.it8811 = None
        self.dmm6500 = None
        self.keysight_34461a = None
        self._connecting_lock = threading.Lock()
```

- [ ] **Step 2: 替换 scan_devices 为委托调用**

将原始的 scan_devices 整个方法替换为：

```python
    def scan_devices(self, on_device_found=None):
        """委托 ConnectionManager 执行扫描"""
        return self.connection_manager.scan_devices(on_device_found)
```

- [ ] **Step 3: 删除 `_get_idn()` 和 `_probe_device()` 方法**

这两个方法已迁移到 ConnectionManager，删除整个方法体。

- [ ] **Step 4: 在 `_connect_device` 和 `_disconnect_device` 中添加线程锁**

```python
    def _connect_device(self, device_key, resource):
        """通用连接方法（带线程锁）"""
        with self._connecting_lock:
            config = self.DEVICE_CONFIGS.get(device_key)
            if not config:
                return False, f"未知设备类型: {device_key}"

            try:
                driver = config['driver_class'](self.rm, resource)
                success, msg = driver.connect()

                if success:
                    setattr(self, config['attr_name'], driver)

                return success, msg
            except Exception as e:
                return False, f"连接失败: {str(e)}"

    def _disconnect_device(self, device_key):
        """通用断开方法（带线程锁）"""
        with self._connecting_lock:
            config = self.DEVICE_CONFIGS.get(device_key)
            if not config:
                return True, "未知设备"

            driver = getattr(self, config['attr_name'], None)
            if driver:
                result = driver.disconnect()
                return result
            return True, "Already disconnected"
```

- [ ] **Step 5: 精简 DEVICE_CONFIGS（ConnectionManager 中已有，但 DeviceController 仍需用于驱动映射）**

由于 `_connect_device` 需要知道 `driver_class` 和 `attr_name`，DEVICE_CONFIGS 仍需保留。但可以移除只用于扫描的字段（`usb_id_check`, `lan_ip_check`, `probe_targets`），不过为保持向后兼容可以保留原样。

无需修改 DEVICE_CONFIGS 内容本身，因为 _connect_device 使用它来实例化驱动。

- [ ] **Step 6: 提交**

```bash
git add src/smart_instrument/device/controller.py
git commit -m "refactor(device): 简化 DeviceController，委托扫描给 ConnectionManager
- scan_devices 委托给 ConnectionManager
- _get_idn / _probe_device 迁移到 ConnectionManager
- _connect_device / _disconnect_device 添加线程锁防竞态"
```

---

### Task 4: 修改 ConnectionPanel（加重新扫描按钮、tooltip、移除阻塞弹窗）

**Files:**
- Modify: `src/smart_instrument/gui/components/connection_panel.py`

- [ ] **Step 1: 在 `__init__` 中添加 tooltip 支持和重新扫描回调**

```python
class ConnectionPanel(ttk.LabelFrame):
    def __init__(self, master, controller, on_connect_status_change=None, on_rescan=None):
        super().__init__(master, text="设备连接", padding="10")
        self.controller = controller
        self.on_connect_status_change = on_connect_status_change
        self.on_rescan = on_rescan  # 重新扫描回调

        self.device_info = {}

        self.connecting_status = {
            'it8811': False,
            'dmm6500': False,
            'keysight': False
        }

        self.create_widgets()
```

- [ ] **Step 2: 在 `create_widgets` 末尾添加重新扫描按钮和状态栏**

```python
    def create_widgets(self):
        # ...现有 IT8811/DMM6500/Keysight 三行代码不变...

        # 添加重新扫描按钮（放在底部）
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        self.rescan_button = ttk.Button(
            action_frame,
            text="重新扫描设备",
            command=self.rescan_devices
        )
        self.rescan_button.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(action_frame, text="就绪", foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=10)
```

- [ ] **Step 3: 添加 `rescan_devices` 方法**

```python
    def rescan_devices(self):
        """手动触发重新扫描"""
        if self.on_rescan:
            # 禁用按钮，防止重复点击
            self.rescan_button.config(state=tk.DISABLED)
            self.status_label.config(text="扫描中...", foreground="orange")
            # 重置设备状态
            for key in ['it8811', 'dmm6500', 'keysight']:
                status_label = getattr(self, f'{key}_status', None)
                if status_label:
                    status_label.config(text="扫描中...", foreground="orange")
            # 回调到 MainWindow
            self.on_rescan()
```

- [ ] **Step 4: 修改 `_on_xxx_connect_result` 方法，移除 `messagebox.showerror`**

对三个设备的连接回调（`_on_it8811_connect_result`, `_on_dmm_connect_result`, `_on_keysight_connect_result`）做同样的修改：

```python
    def _on_it8811_connect_result(self, success, msg):
        self._set_connecting('it8811', False)
        self.it8811_button.config(state=tk.NORMAL)

        if success:
            self.it8811_status.config(text="已连接", foreground="green")
            self.it8811_button.config(text="断开")
            logging.info(msg)
        else:
            # 不再弹出 messagebox.showerror，改为状态标签显示
            self.it8811_status.config(text="错误", foreground="red")
            # 为标签添加 tooltip 显示错误详情
            self._set_tooltip(self.it8811_status, msg)
            logging.error(msg)

        if self.on_connect_status_change:
            self.on_connect_status_change('it8811', success)
```

同样修改 `_on_dmm_connect_result`（`connection_panel.py:171-184`）和 `_on_keysight_connect_result`（`connection_panel.py:239-252`）。

- [ ] **Step 5: 添加 `_set_tooltip` 方法和 ToolTip 类**

```python
    def _set_tooltip(self, widget, text):
        """为 widget 设置悬停提示"""
        if hasattr(widget, '_tooltip') and widget._tooltip:
            widget._tooltip.text = text
        else:
            widget._tooltip = ToolTip(widget, text)


class ToolTip:
    """简单悬停提示组件"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.show, add='+')
        widget.bind('<Leave>', self.hide, add='+')
        widget.bind('<ButtonPress>', self.hide, add='+')

    def show(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID,
                         borderwidth=1, wraplength=300)
        label.pack()

    def hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
```

- [ ] **Step 6: 添加扫描完成状态更新方法**

```python
    def on_scan_complete(self, success=True, message="扫描完成"):
        """扫描完成后的 UI 更新"""
        self.rescan_button.config(state=tk.NORMAL)
        self.status_label.config(
            text=message,
            foreground="green" if success else "red"
        )
```

- [ ] **Step 7: 提交**

```bash
git add src/smart_instrument/gui/components/connection_panel.py
git commit -m "feat(gui): 连接面板添加重新扫描按钮和 tooltip
- 添加重新扫描按钮和状态栏
- 移除所有 messagebox.showerror（扫描/连接阶段）
- 错误信息改为状态标签+悬停 tooltip
- 添加 ToolTip 工具类"
```

---

### Task 5: 修改 MainWindow（简化扫描流程、注入 ConnectionManager）

**Files:**
- Modify: `src/smart_instrument/gui/main_window.py`

- [ ] **Step 1: 修改 `__init__` 传递 on_rescan 回调**

```python
class MainWindow:
    def __init__(self, root, device_controller, data_manager):
        self.root = root
        self.device_controller = device_controller
        self.data_manager = data_manager
        self.connection_manager = device_controller.connection_manager

        self.root.title(Config.WINDOW_TITLE)
        self.root.geometry(Config.WINDOW_GEOMETRY)

        self.is_collecting = False

        self.create_widgets()
        self.setup_menu()

        # 启动扫描
        threading.Thread(target=self.scan_devices, daemon=True).start()
```

- [ ] **Step 2: 在 `create_widgets` 中传递 on_rescan 回调**

```python
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.connection_panel = ConnectionPanel(
            main_frame,
            self.device_controller,
            on_connect_status_change=self.on_device_status_change,
            on_rescan=self.on_rescan_clicked  # 新增
        )
        self.connection_panel.pack(fill=tk.X, pady=5)

        # ... 其余代码不变 ...
```

- [ ] **Step 3: 重写 `scan_devices()` 方法（单一决策点流程）**

```python
    def scan_devices(self):
        """新流程：扫描 → 自动连接（单一决策点，无双重触发）"""
        self.root.after(0, lambda: self.connection_panel.it8811_status.config(text="扫描中...", foreground="orange"))

        def on_device_found(display_text, resource, device_key):
            self.root.after(0, lambda: _update_list(display_text, resource, device_key))

        def _update_list(display_text, resource, device_key):
            if display_text not in current_list:
                current_list.append(display_text)
                current_info[display_text] = resource
                self.connection_panel.update_device_list(
                    current_list, current_info, None, None, None
                )

        current_list = []
        current_info = {}

        try:
            # Phase 1: 仅扫描（不触发连接）
            scan_result = self.device_controller.scan_devices(
                on_device_found=on_device_found
            )
            device_list, device_info, it8811, dmm, keysight = scan_result

            def phase2_connect():
                """Phase 2: 扫描完成后统一自动连接"""
                # 更新最终列表
                self.connection_panel.update_device_list(
                    device_list, device_info, it8811, dmm, keysight
                )

                # 如果没有找到任何设备
                if not any([it8811, dmm, keysight]):
                    self.connection_panel.on_scan_complete(False, "未找到设备")
                    logging.warning("扫描完成，未找到任何已知设备")
                    return

                self.connection_panel.status_label.config(
                    text="正在连接设备...", foreground="orange"
                )

                # 连接结果回调（在主线程执行 UI 更新）
                # 使用 Step 5 中提取的 _update_device_status 共用方法
                def on_connect(device_key, success, msg):
                    self.root.after(0, lambda: self._update_device_status(
                        device_key, success, msg
                    ))

                # 执行自动连接
                self.connection_manager.auto_connect(
                    scan_result, self.device_controller, on_connect=on_connect
                )

                # 检查最终状态
                connected_count = sum([
                    self.device_controller.it8811_connected,
                    self.device_controller.dmm6500_connected,
                    self.device_controller.keysight_34461a_connected,
                ])
                total = sum([1 for d in [it8811, dmm, keysight] if d])
                if connected_count == total:
                    msg = f"所有设备已连接 ({connected_count}/{total})"
                    self.connection_panel.on_scan_complete(True, msg)
                elif connected_count > 0:
                    msg = f"部分设备已连接 ({connected_count}/{total})"
                    self.connection_panel.on_scan_complete(True, msg)
                else:
                    msg = "设备连接失败，请检查后重新扫描"
                    self.connection_panel.on_scan_complete(False, msg)

            self.root.after(0, phase2_connect)

        except Exception as e:
            logging.error(f"扫描失败: {e}")
            self.root.after(0, lambda: self.connection_panel.on_scan_complete(
                False, f"扫描失败: {str(e)}"
            ))
```

- [ ] **Step 4: 添加 `on_rescan_clicked` 和 `rescan_devices` 方法**

```python
    def on_rescan_clicked(self):
        """用户点击重新扫描按钮"""
        threading.Thread(target=self.rescan_devices, daemon=True).start()

    def rescan_devices(self):
        """重新扫描并连接（与 scan_devices 共享逻辑）"""
        def on_device_found(display_text, resource, device_key):
            self.root.after(0, lambda: _update_list(display_text, resource, device_key))

        def _update_list(display_text, resource, device_key):
            if display_text not in current_list:
                current_list.append(display_text)
                current_info[display_text] = resource
                self.connection_panel.update_device_list(
                    current_list, current_info, None, None, None
                )

        current_list = []
        current_info = {}

        # 先断开所有已连接设备
        if self.device_controller.dmm6500_connected:
            self.device_controller.disconnect_dmm6500()
        if self.device_controller.keysight_34461a_connected:
            self.device_controller.disconnect_keysight_34461a()
        if self.device_controller.it8811_connected:
            self.device_controller.disconnect_it8811()

        try:
            scan_result = self.device_controller.scan_devices(
                on_device_found=on_device_found
            )

            def reconnect():
                self.connection_panel.update_device_list(
                    scan_result[0], scan_result[1],
                    scan_result[2], scan_result[3], scan_result[4]
                )

                if not any([scan_result[2], scan_result[3], scan_result[4]]):
                    self.connection_panel.on_scan_complete(False, "未找到设备")
                    return

                self.connection_panel.status_label.config(
                    text="正在连接设备...", foreground="orange"
                )

                def on_connect(device_key, success, msg):
                    self.root.after(0, lambda: self._update_device_status(
                        device_key, success, msg
                    ))

                self.connection_manager.auto_connect(
                    scan_result, self.device_controller, on_connect=on_connect
                )

                # 最终状态
                connected = sum([
                    self.device_controller.it8811_connected,
                    self.device_controller.dmm6500_connected,
                    self.device_controller.keysight_34461a_connected,
                ])
                total = sum([1 for d in [
                    scan_result[2], scan_result[3], scan_result[4]
                ] if d])
                if connected == total:
                    self.connection_panel.on_scan_complete(True, f"所有设备已连接 ({connected}/{total})")
                elif connected > 0:
                    self.connection_panel.on_scan_complete(True, f"部分设备已连接 ({connected}/{total})")
                else:
                    self.connection_panel.on_scan_complete(False, "设备连接失败")

            self.root.after(0, reconnect)

        except Exception as e:
            logging.error(f"重新扫描失败: {e}")
            self.root.after(0, lambda: self.connection_panel.on_scan_complete(
                False, f"重新扫描失败: {str(e)}"
            ))
```

- [ ] **Step 5: 提取公共的 `_update_device_status` 方法（消除重复代码）**

```python
    def _update_device_status(self, device_key, success, msg):
        """统一的设备状态更新（供 scan_devices 和 rescan_devices 共用）"""
        status_map = {
            'it8811': ('it8811_status', 'it8811_button'),
            'dmm6500': ('dmm6500_status', 'dmm6500_button'),
            'keysight_34461a': ('keysight_status', 'keysight_button'),
        }
        mapper = {
            'it8811': 'it8811',
            'dmm6500': 'dmm6500',
            'keysight_34461a': 'keysight',
        }

        config = status_map.get(device_key)
        if not config:
            return

        status_attr, button_attr = config
        panel = self.connection_panel
        status_label = getattr(panel, status_attr)
        button = getattr(panel, button_attr)

        if success:
            status_label.config(text="已连接", foreground="green")
            button.config(text="断开")
        else:
            status_label.config(text="错误", foreground="red")
            panel._set_tooltip(status_label, msg)

        panel._set_connecting(mapper.get(device_key, device_key), False)
        button.config(state=tk.NORMAL)
        self.on_device_status_change(device_key, success)
```

然后在 `scan_devices` 和 `rescan_devices` 中都使用这个方法。

- [ ] **Step 6: 提交**

```bash
git add src/smart_instrument/gui/main_window.py
git commit -m "refactor(gui): 简化 MainWindow 扫描连接流程
- Phase 1 扫描 → Phase 2 连接（单一决策点）
- 添加重新扫描功能（on_rescan_clicked + rescan_devices）
- 提取 _update_device_status 消除重复代码
- 连接结果非阻塞通知"
```

---

### Task 6: 最终集成验证

- [ ] **Step 1: 运行应用测试基本功能**

```bash
cd C:/Users/boe/Documents/EwinDT/smartInstrument
python entry_point.py
```

验证清单：
1. 启动后自动扫描 → 状态栏显示"扫描中..."
2. 设备列表正确显示（IT8811 应只有一条记录）
3. 自动连接顺序：DMM6500 + Keysight 并发 → IT8811 单独
4. 所有设备连接成功后状态栏显示"所有设备已连接"
5. 连接失败时不弹 `messagebox.showerror`，状态标签变红
6. 悬停红色标签显示错误详情
7. 点击"重新扫描设备"按钮 → 断开所有 → 重新扫描 → 重新连接
8. 手动触发数据采集正常

- [ ] **Step 2: 验证幽灵设备场景**

在 VISA 驱动存在幽灵设备的情况下启动应用：
1. 扫描应识别到两台 IT8811，但序列号去重后只保留一条
2. 自动连接只连接正确的设备
3. 日志应显示去重信息

- [ ] **Step 3: 验证多次重新扫描稳定性**

连续点击"重新扫描设备" 3-5 次：
1. 不应出现崩溃
2. 扫描中点击被忽略
3. 每次连接稳定

- [ ] **Step 4: 完成提交**

```bash
git add -A
git commit -m "refactor: 完成设备连接架构重构

- ConnectionManager 独立管理扫描/去重/自动连接
- 序列号去重过滤 VISA 幽灵设备
- LAN 并发连接 + USB 顺序连接消除竞态
- _on_it8811 等回调移除阻塞式 messagebox
- GUI 添加重新扫描按钮和状态栏
- _connect_device 添加线程锁防竞态
- _get_idn/_probe_device finally 确保资源释放
- 扫描/连接分离为 Phase 1 + Phase 2 单一决策点"
```
