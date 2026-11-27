# 工程架构

Smart Instrument 是单机 Tkinter 应用，通过 PyVISA 连接电子负载和万用表。采集记录先存于内存，由用户手动导出 CSV；不依赖服务端或数据库。

| 位置 | 职责 |
| --- | --- |
| [`main.py`](../src/smart_instrument/main.py) | 组合应用：初始化日志、创建 Tk 窗口、设备控制器和数据管理器。控制台命令、`python -m smart_instrument` 和 EXE 的入口最终都调用 `main()`。 |
| [`gui/`](../src/smart_instrument/gui/) | 事件处理、界面状态和采集流程。`MainWindow` 协调扫描、连接和采集；三个面板分别负责连接、负载控制和数据展示。耗时操作通常在后台线程执行，结果调度回 Tk 界面。 |
| [`connection/`](../src/smart_instrument/connection/) | VISA 资源扫描、设备识别、去重与 LAN 优先选择，按扫描结果协调自动连接；不负责实例化驱动。 |
| [`device/`](../src/smart_instrument/device/) | `DeviceController` 持有 VISA ResourceManager、管理驱动实例，对界面提供连接和测量接口。具体驱动负责 VISA 会话和仪器命令。 |
| [`data/`](../src/smart_instrument/data/) | 保存内存中的测量结果、清空数据、导出 CSV；不直接控制设备或界面。 |
| [`config.py`](../src/smart_instrument/config.py) | 默认设备探测地址、通信超时、界面参数与电阻调节步长。 |

启动时，界面通过控制器扫描资源，识别结果用于更新连接列表和尝试自动连接。采集时，窗口通过控制器设置或读取负载并取回测量结果，再将选中的记录提交给数据管理器和表格。自动连接会协调连接顺序，驱动的实际创建由控制器统一处理。

## 维护检查

- 调整设备发现规则时，检查 `connection/manager.py` 和 `config.py`。调整驱动映射或测量接口时，检查 `device/controller.py` 及调用它的界面代码。
- [`Package Check`](../.github/workflows/package-check.yml) 对 PR 执行普通安装（非 editable），验证模块入口和所需子包能从安装环境导入，不启动 GUI 或访问仪器。仅验证源码或 editable 安装无法发现 wheel 遗漏子包的问题。
- [`test_controller.py`](../test_controller.py) 会创建 VISA ResourceManager 并扫描设备，不是无硬件单元测试。驱动行为或实机连接不在安装检查的覆盖范围内。
- [`superpowers/`](superpowers/) 下带日期的计划和设计是历史记录，可能包含未采用的方案。当前行为以源码和本页为准。
