#!/usr/bin/env python3
"""启动脚本"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == '__main__':
    from smart_instrument.main import AutoTestTool
    import tkinter as tk
    
    root = tk.Tk()
    app = AutoTestTool(root)
    root.mainloop()
