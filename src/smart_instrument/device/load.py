from .base import BaseInstrument
import logging
import time

class IT8811(BaseInstrument):
    def __init__(self, resource_manager, resource_name, timeout=3000):
        super().__init__(resource_manager, resource_name, timeout)

    def initialize_device(self):
        """初始化设备"""
        try:
            # 默认设置为 CC 模式，安全起见
            self.write("MODE CC")
            logging.info("IT8811 initialized to CC mode")
        except Exception as e:
            logging.error(f"Failed to initialize IT8811: {e}")

    def configure_connection(self):
        if self.instrument:
            self.instrument.chunk_size = 1024
            self.instrument.read_termination = '\n'
            self.instrument.write_termination = '\n'

    def get_mode(self):
        try:
            mode = self.query("MODE?")
            return True, mode.strip()
        except Exception as e:
            return False, str(e)

    def set_mode(self, mode):
        try:
            mode = mode.upper()
            if mode not in ["CC", "CV", "CR", "CW"]:
                return False, f"不支持的模式: {mode}"
            self.write(f"MODE {mode}")
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
            
            val = self.query(cmd_map[mode])
            return True, val
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
            # IT8811 通常使用 INPUT 命令控制输入状态（电子负载是输入设备）
            # 尝试使用 INP 命令，如果不行可以回退到 OUT
            cmd = "INP 1" if state == "ON" else "INP 0"
            self.write(cmd)
            # 验证
            time.sleep(0.3)
            # 有些设备可能需要查询 INPUT?
            out = self.query("INP?")
            is_on = '1' in out or 'ON' in out.upper()
            return True, f"输入已{'开启' if is_on else '关闭'}"
        except Exception as e:
            # 如果 INP 失败，尝试 OUT (作为备选，虽然不太可能是 OUT)
            try:
                logging.warning(f"INP command failed, trying OUT: {e}")
                cmd = "OUT 1" if state == "ON" else "OUT 0"
                self.write(cmd)
                time.sleep(0.3)
                out = self.query("OUT?")
                is_on = '1' in out or 'ON' in out.upper()
                return True, f"输出已{'开启' if is_on else '关闭'}"
            except Exception as e2:
                return False, f"控制开关失败: {str(e2)}"
