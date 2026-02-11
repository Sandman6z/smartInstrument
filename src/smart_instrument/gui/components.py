import tkinter as tk
from tkinter import ttk

class AutoScrollCombobox(ttk.Combobox):
    """自定义Combobox类，支持鼠标悬停自动调整宽度"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        # 保存原始宽度
        self.original_width = kwargs.get('width', 30)
        # 绑定鼠标悬停事件
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        # 确保下拉菜单可以滚动
        # 在tkinter中，ttk.Combobox的下拉菜单默认是可以滚动的
        # 但是我们需要确保在设置宽度时不会影响下拉菜单的滚动功能
    
    def on_enter(self, event):
        # 鼠标进入时检查文本宽度并调整
        self.adjust_width()
    
    def on_leave(self, event):
        # 鼠标离开时恢复原始宽度
        self.configure(width=self.original_width)
    
    def adjust_width(self):
        # 获取当前选中项
        value = self.get()
        if value:
            # 创建一个临时的Label来测量文本宽度
            temp_label = ttk.Label(self.master, text=value)
            text_width = temp_label.winfo_reqwidth()
            temp_label.destroy()
            # 计算需要的字符宽度
            # 注意：ttk.Combobox的宽度是基于字符数的，不是像素
            # 我们可以通过创建一个临时的Entry来测量字符宽度
            temp_entry = ttk.Entry(self.master)
            char_width = temp_entry.winfo_reqwidth() / 10  # 假设10个字符的宽度
            temp_entry.destroy()
            # 计算需要的字符宽度
            required_width = max(int(text_width / char_width) + 2, self.original_width)
            # 更新宽度
            self.configure(width=required_width)