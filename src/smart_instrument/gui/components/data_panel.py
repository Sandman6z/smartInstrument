import tkinter as tk
from tkinter import ttk, messagebox
import logging

class DataPanel(ttk.LabelFrame):
    def __init__(self, master, data_manager):
        super().__init__(master, text="数据记录", padding="10")
        self.data_manager = data_manager

        self.create_widgets()

    def create_widgets(self):
        self._setup_styles()

        # 容器
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        # ── 单个 Treeview ──
        self.tree = ttk.Treeview(
            container,
            height=3,
            show="tree headings",
            style="DataPanel.Treeview",
        )
        self.tree["columns"] = ("col1", "col2")

        # 设备列（#0 树列，固定宽度）
        self.tree.column("#0", width=200, minwidth=160, stretch=tk.NO)
        self.tree.heading("#0", text="设备")

        # 初始数据列（固定宽度，不拉伸）
        for col_name in ("col1", "col2"):
            self.tree.column(col_name, width=90, minwidth=80, stretch=tk.NO, anchor=tk.CENTER)
        self.tree.heading("col1", text="触发1")
        self.tree.heading("col2", text="触发2")

        # 添加设备行
        self.tree.insert("", tk.END, text="IT8811 (电阻)")
        self.tree.insert("", tk.END, text="DMM6500 (电压)")
        self.tree.insert("", tk.END, text="KEYSIGHT 34461A (电流)")

        # ── 水平滚动条（先 pack，固定在底部） ──
        scroll_row = ttk.Frame(container)
        scroll_row.pack(side=tk.BOTTOM, fill=tk.X)
        hscrollbar = ttk.Scrollbar(scroll_row, orient=tk.HORIZONTAL, command=self.tree.xview)
        hscrollbar.pack(fill=tk.X, expand=True)
        self.tree.configure(xscrollcommand=hscrollbar.set)

        # ── Treeview（后 pack，填满剩余空间） ──
        self.tree.pack(fill=tk.BOTH, expand=True)

        # ── 清除按钮 ──
        clear_frame = ttk.Frame(self)
        clear_frame.pack(fill=tk.X, pady=5)

        self.clear_data_button = ttk.Button(
            clear_frame,
            text="清除测试数据",
            command=self.confirm_clear_data,
        )
        self.clear_data_button.pack(side=tk.RIGHT, padx=5)

    def _setup_styles(self):
        """配置 Treeview 样式。"""
        style = ttk.Style()
        style.configure("DataPanel.Treeview",
            background="#ffffff",
            foreground="#999999",
            fieldbackground="#ffffff",
            borderwidth=0)
        style.configure("DataPanel.Treeview.Heading",
            background="#f8f8f8",
            foreground="#999999",
            borderwidth=0)
        style.map("DataPanel.Treeview", background=[("selected", "#f0f0f0")])
        style.map("DataPanel.Treeview.Heading", background=[("active", "#f0f0f0")])

    def add_data_column(self, col_index, resistance, voltage, current):
        col_name = f"col{col_index}"

        # 如果列不存在，添加新列
        if col_name not in self.tree["columns"]:
            self.tree["columns"] = self.tree["columns"] + (col_name,)
            self.tree.column(col_name, width=90, minwidth=80, stretch=tk.NO, anchor=tk.CENTER)
            self.tree.heading(col_name, text=f"触发{col_index}")

        # 更新三行数据
        try:
            children = self.tree.get_children()
            if len(children) >= 3:
                self.tree.set(children[0], col_name, resistance)
                self.tree.set(children[1], col_name, voltage)
                self.tree.set(children[2], col_name, current)
        except Exception as e:
            logging.error(f"更新表格失败: {e}")

    def confirm_clear_data(self):
        if not self.data_manager.data:
            messagebox.showinfo("提示", "表格中没有数据可清除")
            return

        if messagebox.askyesno("确认清除", "确定要清除所有测试数据吗？此操作不可撤销。", icon=messagebox.WARNING):
            self.clear_data()

    def clear_data(self):
        success, msg = self.data_manager.clear_data()
        if success:
            for item in self.tree.get_children():
                for col in list(self.tree["columns"]):
                    self.tree.set(item, col, "")
            logging.info(msg)
            messagebox.showinfo("成功", msg)
        else:
            messagebox.showerror("错误", msg)
