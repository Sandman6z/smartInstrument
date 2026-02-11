import sys
import os

# 确保可以直接运行此文件
if __name__ == "__main__":
    # 获取项目根目录
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # 添加src目录到Python路径
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
    # 现在使用绝对导入
    from smart_instrument.gui.app import AutoTestTool
else:
    # 作为模块导入时，使用相对导入
    from .gui.app import AutoTestTool

import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTestTool(root)
    root.mainloop()