import pyvisa
import logging
import time
from abc import ABC, abstractmethod

class BaseInstrument(ABC):
    def __init__(self, resource_manager, resource_name, timeout=3000):
        self.rm = resource_manager
        self.resource_name = resource_name
        self.timeout = timeout
        self.instrument = None
        self.connected = False

    def connect(self):
        try:
            if self.instrument:
                self.close()
            
            self.instrument = self.rm.open_resource(self.resource_name)
            self.instrument.timeout = self.timeout
            self.configure_connection()
            
            idn = self.query("*IDN?")
            logging.info(f"{self.__class__.__name__} connected. IDN: {idn}")
            
            self.initialize_device()
            self.connected = True
            return True, f"{self.__class__.__name__} 连接成功"
        except Exception as e:
            logging.error(f"Failed to connect to {self.resource_name}: {e}")
            self.close()
            return False, f"连接失败: {str(e)}"

    def disconnect(self):
        self.close()
        self.connected = False
        return True, "断开连接成功"

    def close(self):
        if self.instrument:
            try:
                self.instrument.close()
            except:
                pass
            self.instrument = None

    def write(self, command):
        if self.instrument:
            self.instrument.write(command)

    def query(self, command):
        if self.instrument:
            return self.instrument.query(command).strip()
        raise Exception("Device not connected")

    def configure_connection(self):
        """配置连接参数，如终止符等"""
        pass

    @abstractmethod
    def initialize_device(self):
        """设备初始化逻辑"""
        pass
