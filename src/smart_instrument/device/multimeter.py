from .base import BaseInstrument
import logging
import time

class DMM6500(BaseInstrument):
    def __init__(self, resource_manager, resource_name, timeout=3000):
        super().__init__(resource_manager, resource_name, timeout)

    def initialize_device(self):
        """配置为 DCV 模式"""
        try:
            self.write("FUNCTION 'VOLTage:DC'")
            logging.info("DMM6500 switched to DCV mode")
        except Exception as e:
            logging.error(f"Failed to switch to DCV mode: {e}")

    def get_voltage(self):
        try:
            return True, self.query("MEAS:VOLT:DC?")
        except Exception as e:
            return False, str(e)

class Keysight34461A(BaseInstrument):
    def __init__(self, resource_manager, resource_name, timeout=3000):
        super().__init__(resource_manager, resource_name, timeout)

    def initialize_device(self):
        """配置为 DCI 模式"""
        try:
            self.write("FUNCTION 'CURRent:DC'")
            logging.info("Keysight 34461A switched to DCI mode")
        except Exception as e:
            logging.error(f"Failed to switch to DCI mode: {e}")

    def get_current(self):
        try:
            return True, self.query("MEAS:CURR:DC?")
        except Exception as e:
            return False, str(e)
