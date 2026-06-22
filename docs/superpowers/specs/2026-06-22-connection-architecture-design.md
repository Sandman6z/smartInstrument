# 设备连接架构重构设计

日期: 2026-06-22
状态: 已批准

## 问题陈述

在启动时设备自动连接经常失败，表现为 `VI_ERROR_RSRC_NFOUND` 错误，需要反复重启应用才能成功连接所有设备（IT8811、DMM6500、Keysight 34461A）。

### 根因链

1. **VISA 幽灵设备**：VISA 驱动列出两个同款 IT8811 USB 设备（序列号 ...7007 和 ...7010），其中 ...7007 是已经不在线的残留条目。代码的 USB ID 匹配无法区分两者。
2. **并发 VISA 资源竞争**：扫描线程池（5 工人）和自动连接线程同时打开/关闭同一个 USB 资源的 VISA 会话，NI-VISA 后端对 USB 设备的并发访问不稳定。
3. **双重连接触发**：`_update_incremental` 在扫描中发现设备时触发连接，`final_update` 在扫描完成后又触发连接，两者通过易失的布尔标志协调，时序稍有偏差就竞态。
4. **阻塞式错误对话框**：`messagebox.showerror` 阻塞 tkinter 主循环，导致 `after(0)` 延迟回调在对话框关闭后爆发式执行，`final_update` 看到连接状态为 False 后发起第二波连接，大概率再次失败。
5. **不可修复的启动生死**：扫描只在启动时执行一次，无重新扫描按钮，失败只能重启。

## 架构设计

### 职责拆分

```
DeviceController（外观层）
├── 对外统一 API：connect/disconnect/measure
├── 委派扫描和连接给 ConnectionManager
├── 保留数据采集方法（get_all_measurements 等）

ConnectionManager（新增）
├── 设备扫描（从 DeviceController 提取）
├── 序列号去重过滤
├── 顺序/并发连接队列
├── 连接状态同步
└── 重新扫描功能
```

### 新增文件结构

```
src/smart_instrument/connection/
├── __init__.py
├── manager.py        ← ConnectionManager 实现
└── models.py         ← DeviceEntry 数据类
```

## 设备识别与去重

### 扫描流程

```python
# 每个 VISA 资源探测结果
@dataclass
class DeviceEntry:
    device_key: str          # 'it8811', 'dmm6500', 'keysight_34461a'
    display_name: str        # UI 显示名
    resource: str            # VISA 资源字符串
    connection_type: str     # 'USB' | 'LAN'
    serial_number: str       # 从 *IDN? 解析
    idn_response: str        # 完整 IDN 字符串
    is_ghost: bool = False   # 幽灵设备标记
```

### 去重规则

| 设备类型 | 识别 key | 策略 |
|---------|---------|------|
| USB 设备 | `USB_{VID_PID}_{serial}` | 相同 key 的多个 VISA entry → 保留一个 |
| LAN 设备 | `TCPIP_{IP}_{model}` | 相同 IP 的多个协议 entry → 保留一个 |
| 幽灵设备 | 探测时 `VI_ERROR_RSRC_NFOUND` | 标记为幽灵，从结果中剔除 |

扫描时对所有 IT8811 USB 设备的 IDN 响应解析序列号，自动过滤重复序列号的条目，不在 Config 中新增白名单配置。

## 连接流程

### 执行顺序

```
┌─────────────────────────────────────────────────┐
│  Phase 1: 扫描（线程池并发探测）                    │
│  - 并行探测所有 VISA 资源                           │
│  - 解析 IDN，序列号去重                             │
│  - 识别设备类型，标记幽灵                           │
│  - ❌ 不触发自动连接                                │
└──────────────────────┬────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│  Phase 2: 连接（统一决策，非阻塞）                   │
│                                                    │
│  Step 1: DMM6500 LAN（可并发）                     │
│  Step 2: Keysight 34461A LAN（可并发）             │
│  Step 3: IT8811 USB（单独顺序，消除 VISA 冲突）     │
│                                                    │
│  每个设备结果通过回调通知 GUI                        │
│  错误不弹对话框，只更新状态标签                      │
└─────────────────────────────────────────────────┘
```

### 线程安全

`DeviceController` 内部添加 `threading.Lock`（`_connecting_lock`），在 `_connect_device` 和 `_disconnect_device` 入口加锁，确保同一时刻只有一个连接操作在执行。

## 用户通知

### 三层次通知系统

1. **状态栏**（主窗口底部）：`扫描中...` → `发现 3 个设备` → `连接完成 (2/3 成功)`
2. **设备标签**：灰色=未连接 / 橙色=连接中 / 绿色=已连接 / 红色=失败
3. **日志**：所有操作和错误写入 logging

### 约束

- [强制] 扫描和自动连接过程中不得弹出 `messagebox.showerror`
- [允许] 用户主动操作（手动点击连接按钮）失败时，仍然弹窗提示
- [允许] `messagebox.showwarning` 用于非关键用户操作（如 CSV 保存）

## GUI 变更

### 连接面板

- 添加"重新扫描"按钮（调用 `ConnectionManager.rescan()`）
- 扫描时禁用连接按钮
- 连接状态标签支持 tooltip 悬停显示最后错误详情
- 主窗口底部添加状态栏

### MainWindow 变更

- `scan_devices()` 简化为只调用一次 `ConnectionManager.scan_and_connect()`
- 删除 `_update_incremental` 中的自动连接触发
- 添加 `rescan_devices()` 方法绑定重新扫描按钮

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/smart_instrument/connection/__init__.py` | 新建 | 包初始化 |
| `src/smart_instrument/connection/models.py` | 新建 | `DeviceEntry` 数据类 |
| `src/smart_instrument/connection/manager.py` | 新建 | `ConnectionManager` 实现 |
| `src/smart_instrument/device/controller.py` | 修改 | 提取扫描连接逻辑，保留外观层 |
| `src/smart_instrument/gui/main_window.py` | 修改 | 注入 ConnectionManager，简化流程，加状态栏 |
| `src/smart_instrument/gui/components/connection_panel.py` | 修改 | 加 tooltip，移除阻塞弹窗，加重新扫描按钮 |
| `src/smart_instrument/config.py` | 不变 | 无需新增配置 |
| `src/smart_instrument/device/base.py` | 不变 | |
| `src/smart_instrument/device/load.py` | 不变 | |
| `src/smart_instrument/device/multimeter.py` | 不变 | |
| `src/smart_instrument/gui/components/control_panel.py` | 不变 | |
| `src/smart_instrument/gui/components/data_panel.py` | 不变 | |

## 边界情况和错误处理

| 场景 | 行为 |
|------|------|
| 所有设备连接成功 | 绿色标签，状态栏显示"所有设备已连接" |
| 部分设备连接失败 | 失败设备红色标签+悬停提示错误信息，状态栏显示"部分设备未连接" |
| 未找到任何设备 | 所有标签灰色，状态栏显示"未找到设备"，请检查连接和 VISA 驱动 |
| 扫描过程中用户点击重新扫描 | 忽略"重新扫描"按钮，等扫描完成后再响应 |
| 扫描过程中设备断开 | 连接阶段会失败，显示红色标签 |
| VISA ResourceManager 初始化失败 | 启动时捕获异常，GUI 显示"VISA 驱动未安装" |
| 重新扫描后设备不复存在 | 自动断开状态更新，UI 标签切为灰色 |

## 测试策略

1. **幽灵设备场景**：模拟两个同名 IT8811 USB entry，验证去重逻辑只连接正确的
2. **连接竞态**：模拟扫描完成和连接回调之间的时序，验证单一决策点无双重触发
3. **VISA 资源泄漏**：`_probe_device` 失败路径验证 `dev.close()` 被调用
4. **错误通知**：验证连接失败时不弹阻塞对话框

## 自审记录

- [x] 无 TBD/TODO/占位符
- [x] 架构描述与功能描述一致
- [x] 范围聚焦于连接问题，未引入无关功能
- [x] 所有需求明确无歧义
- [x] 新增 2 文件，修改 3 文件，其余 8 文件不变
