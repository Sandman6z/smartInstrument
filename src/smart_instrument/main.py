import sys
import os
import tkinter as tk

# 确保可以直接运行此文件
if __name__ == "__main__":
    # 获取项目根目录
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # 添加src目录到Python路径
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
    # 现在使用绝对导入
    from smart_instrument.device.controller import DeviceController
    from smart_instrument.data.manager import DataManager
    from smart_instrument.config import Config
    from smart_instrument.gui.main_window import MainWindow
    from smart_instrument import setup_logging
else:
    # 作为模块导入时，使用相对导入
    from .device.controller import DeviceController
    from .data.manager import DataManager
    from .config import Config
    from .gui.main_window import MainWindow
    from . import setup_logging

def main():
    setup_logging()
    root = tk.Tk()
    
    # 初始化控制器和管理器
    device_controller = DeviceController()
    data_manager = DataManager()
    
    # 启动主窗口
    app = MainWindow(root, device_controller, data_manager)
    root.mainloop()

if __name__ == "__main__":
    main()
