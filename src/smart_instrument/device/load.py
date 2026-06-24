from .base import BaseInstrument
import logging
import time

class IT8811(BaseInstrument):
    # FUNC 命令和 UI 模式名的映射关系
    # IT8811 使用 FUNC 命令切换模式：FUNC RES / FUNC CURR / FUNC VOLT / FUNC POW
    FUNC_MAP = {
        "CR": "RES",
        "CC": "CURR",
        "CV": "VOLT",
        "CW": "POW",
    }
    # 反向映射（UI 显示用）
    MODE_FROM_FUNC = {v: k for k, v in FUNC_MAP.items()}

    def __init__(self, resource_manager, resource_name, timeout=3000):
        super().__init__(resource_manager, resource_name, timeout)

    def initialize_device(self):
        """初始化设备：连接后自动切换到 CR (恒阻) 模式"""
        try:
            # IT8811 使用 FUNC RES 切换到恒阻模式
            # （注意：FUNC 命令参数是 RES/CURR/VOLT/POW，不是 CR/CC/CV/CW）
            self.write("FUNC RES")
            time.sleep(0.3)
            logging.info("IT8811 initialized to CR mode (FUNC RES)")
        except Exception as e:
            logging.error(f"Failed to initialize IT8811: {e}")

    def configure_connection(self):
        if self.instrument:
            self.instrument.chunk_size = 1024
            self.instrument.read_termination = '\n'
            self.instrument.write_termination = '\n'

    def get_mode(self):
        # IT8811 不支持 MODE? / FUNC? 等查询命令，无法获取当前模式
        return False, "IT8811 does not support mode query"

    def set_mode(self, mode):
        try:
            mode = mode.upper()
            func_param = self.FUNC_MAP.get(mode)
            if not func_param:
                return False, f"不支持的模式: {mode}"

            # IT8811 使用 FUNC 命令切换模式
            # FUNC RES = CR, FUNC CURR = CC, FUNC VOLT = CV, FUNC POW = CW
            self.write(f"FUNC {func_param}")
            time.sleep(0.3)

            return True, f"模式已切换为 {mode}"
        except Exception as e:
            return False, f"设置模式失败: {str(e)}"

    def get_value(self, mode):
        try:
            cmd_map = {
                "CC": "CURR?",
                "CV": "VOLT?",
                "CR": "RES?",
                "CW": "POW?"
            }
            if mode not in cmd_map:
                return False, "未知模式"

            # IT8811 查询命令可能会超时，这里改为先设置短超时再尝试
            try:
                self.instrument.timeout = 1000  # 1秒超时
                val = self.query(cmd_map[mode])
                return True, val
            finally:
                self.instrument.timeout = self.timeout  # 恢复原超时
        except Exception as e:
            return False, str(e)

    def set_value(self, mode, value):
        try:
            cmd_map = {
                "CC": "CURR",
                "CV": "VOLT",
                "CR": "RES",
                "CW": "POW"
            }
            if mode not in cmd_map:
                return False, "未知模式"
                
            self.write(f"{cmd_map[mode]} {value}")
            return True, f"设置成功: {value}"
        except Exception as e:
            return False, f"设置失败: {str(e)}"

    # 保留旧方法以兼容，但建议使用 set_value
    def get_resistance(self):
        return self.get_value("CR")

    def set_resistance(self, value):
        return self.set_value("CR", value)

    def toggle_output(self, state):
        try:
            # IT8811 使用 INP 命令控制输入状态（电子负载输入）
            cmd = "INP 1" if state == "ON" else "INP 0"
            self.write(cmd)
            time.sleep(0.3)

            # 尝试查询输入状态（IT8811 可能不支持 INP? 查询，超时不视为错误）
            try:
                self.instrument.timeout = 500  # 500ms 超时，避免卡死
                self.query("INP?")
            except Exception:
                pass  # 查询超时或失败不影响，写命令已成功
            finally:
                self.instrument.timeout = self.timeout

            return True, f"输入已{'开启' if state == 'ON' else '关闭'}"
        except Exception as e:
            return False, f"控制开关失败: {str(e)}"
