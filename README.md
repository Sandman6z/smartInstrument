[English](README.en.md) | 中文

# 自动化测试工具

通过 Tkinter 图形界面控制 ITECH IT8811 电子负载，使用 Keithley DMM6500 和 Keysight 34461A 采集电压和电流，并将测量结果导出为 CSV。

## 安装与启动

- 下载 Windows 可执行文件：见 [GitHub Releases](https://github.com/Sandman6z/smartInstrument/releases)。
- 从源码运行：需要带 Tkinter 的 Python；CI 使用 Windows 和 Python 3.11 检查普通安装。
- 无论用哪种方式运行，连接仪器的电脑都需要安装 VISA 后端，例如 [NI-VISA](https://www.ni.com/zh-cn/support/downloads/drivers/download.ni-visa.html) 或 Keysight IO Libraries。Windows EXE 不包含这些驱动。

在仓库根目录执行（二选一）：

```bash
# uv（按锁文件安装运行依赖）
uv sync --locked --no-dev
uv run --locked --no-dev smart_instrument
```

```bash
# pip（建议在已激活的虚拟环境中执行）
python -m pip install .
python -m smart_instrument
```

## 操作流程

1. 启动后，应用会扫描 VISA 资源并尝试连接识别到的设备；同一设备有多个连接方式时优先使用 LAN。未自动连接时，可从下拉列表选择地址后手动连接。
2. 在输入框或滑动条设置 IT8811 电阻（`100–7500 Ω`）。在滑动条上滚动鼠标滚轮时，每次调整 `100 Ω`。
3. 连接全部三台仪器并将电子负载的**输入状态**切到 `ON` 后，可点击「手动触发」采集一次，或点击「自动采集」按 `100 Ω` 档位向下采集。自动采集只在相邻有效测量的功率差超过 `20 W` 时记录，可手动停止；采集期间不要断开仪器。
4. 数据在「数据记录」表格内横向展开，可用水平滚动条查看。从「文件 → 保存数据到CSV」导出到当前工作目录。未导出的数据不会自动保留，清除数据或退出前请先保存。

## 打包与发布

在 Windows 的仓库根目录执行：

```bash
uv sync --locked --group dev
uv run --locked python scripts/build_nuitka.py  # dist_nuitka/SmartInstrument.exe
uv run --locked python scripts/build_exe.py     # dist/SmartInstrument.exe
```

正式发布使用 Nuitka。首次打包可能需要下载 C 编译工具。发布流程见 [RELEASE.md](RELEASE.md)，模块边界和维护检查见 [工程架构](docs/architecture.md)。

## 故障排除

- **设备未找到或连接失败**：确认 VISA 后端已安装、仪器在线、USB 或 LAN 连接可用。默认识别和探测配置见 [`config.py`](src/smart_instrument/config.py)。
- **无法采集**：检查三台仪器的连接状态以及 IT8811 输入状态。
- **无法导出**：确认启动时的工作目录可写。运行日志位于该目录下的 `logs/`。

## 许可证

[GNU GPL v3](LICENSE)。
