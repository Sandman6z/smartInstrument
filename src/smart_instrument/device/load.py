from .base import BaseInstrument
import logging
import time

class IT8811(BaseInstrument):
    def __init__(self, resource_manager, resource_name, timeout=3000):
        super().__init__(resource_manager, resource_name, timeout)

    def initialize_device(self):
        """配置为 CR 模式"""
        try:
            self.write("MODE CR")
            logging.info("IT8811 switched to CR mode")
        except Exception as e:
            logging.error(f"Failed to switch to CR mode: {e}")

    def configure_connection(self):
        if self.instrument:
            self.instrument.chunk_size = 1024
            self.instrument.read_termination = '\n'
            self.instrument.write_termination = '\n'

    def get_resistance(self):
        try:
            res = self.query("RES?")
            return True, res
        except Exception as e:
            return False, str(e)

    def set_resistance(self, value):
        try:
            self.write(f"RES {value}")
            return True, f"电阻值设置为 {value} Ω"
        except Exception as e:
            return False, f"设置电阻值失败: {str(e)}"

    def toggle_output(self, state):
        try:
            cmd = "OUT 1" if state == "ON" else "OUT 0"
            self.write(cmd)
            # 验证
            time.sleep(0.3)
            out = self.query("OUT?")
            return True, f"输出已{'开启' if '1' in out else '关闭'}"
        except Exception as e:
            return False, f"控制输出失败: {str(e)}"
