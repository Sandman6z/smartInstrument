import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime

from smart_instrument.device.controller import DeviceController
from smart_instrument.data.manager import DataManager
from smart_instrument.config import Config
from smart_instrument.gui.components import AutoScrollCombobox
from smart_instrument.gui.device_operations import DeviceOperations
from smart_instrument.gui.it8811_control import IT8811Control
from smart_instrument.gui.data_operations import DataOperations

class AutoTestTool:
    def __init__(self, root):
        self.root = root
        self.root.title(Config.WINDOW_TITLE)
        self.root.geometry(Config.WINDOW_GEOMETRY)
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化控制器
        self.device_controller = DeviceController()
        self.data_manager = DataManager()
        
        # 设备信息映射
        self.device_info = {}
        
        # 输出状态
        self.output_state = "OFF"
        
        # 数据存储
        self.data = []
        
        # 初始化操作模块
        self.device_ops = DeviceOperations(self)
        self.it8811_ctrl = IT8811Control(self)
        self.data_ops = DataOperations(self)
        
        # 创建GUI
        self.create_widgets()
        
        # 立即显示设备扫描状态
        self.show_scan_status()
        
        # 延迟扫描设备，确保UI先加载完成
        # 使用root.after()方法在UI加载完成后执行设备扫描
        self.root.after(100, self.device_ops.scan_devices)
    
    def create_widgets(self):
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="保存数据到CSV", command=self.data_ops.save_to_csv)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        menubar.add_cascade(label="文件", menu=file_menu)
        
        # 设置菜单栏
        self.root.config(menu=menubar)
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设备连接部分
        device_frame = ttk.LabelFrame(main_frame, text="设备连接", padding="10")
        device_frame.pack(fill=tk.X, pady=5)
        
        # 创建设备配置的通用方法
        def create_device_config(parent_frame, device_name, resource_var_name, button_var_name, status_var_name, connect_command):
            # 创建设备框架
            device_frame = ttk.Frame(parent_frame)
            device_frame.pack(fill=tk.X, pady=5)
            
            # 创建标签
            ttk.Label(device_frame, text=f"{device_name}资源:", width=15).pack(side=tk.LEFT, padx=5)
            
            # 创建资源下拉框
            resource_var = AutoScrollCombobox(device_frame, width=38)  # 增加四分之一宽度
            resource_var.pack(side=tk.LEFT, padx=5)
            
            # 创建连接按钮
            button_var = ttk.Button(device_frame, text="连接", command=connect_command)
            button_var.pack(side=tk.LEFT, padx=5)
            
            # 创建状态标签
            status_var = ttk.Label(device_frame, text="未连接", foreground="red")
            status_var.pack(side=tk.LEFT, padx=5)
            
            # 将创建的变量保存到实例中
            setattr(self, resource_var_name, resource_var)
            setattr(self, button_var_name, button_var)
            setattr(self, status_var_name, status_var)
        
        # 创建各个设备的配置
        create_device_config(device_frame, "IT8811", "it8811_resource", "it8811_button", "it8811_status", self.device_ops.connect_it8811)
        create_device_config(device_frame, "DMM6500", "dmm6500_resource", "dmm6500_button", "dmm6500_status", self.device_ops.connect_dmm6500)
        create_device_config(device_frame, "KEYSIGHT", "keysight_resource", "keysight_button", "keysight_status", self.device_ops.connect_keysight_34461a)
        
        # IT8811控制部分
        it8811_control_frame = ttk.LabelFrame(main_frame, text="IT8811控制", padding="10")
        it8811_control_frame.pack(fill=tk.X, pady=5)
        
        # 电阻值调整
        resistance_frame = ttk.Frame(it8811_control_frame)
        resistance_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(resistance_frame, text="电阻值 (Ω):", width=15).pack(side=tk.LEFT, padx=5)
        self.resistance_entry = ttk.Entry(resistance_frame, width=15)
        self.resistance_entry.pack(side=tk.LEFT, padx=5)
        self.resistance_entry.insert(0, "7500")  # 默认值7500Ω
        
        # 添加输入框事件处理
        # 当输入框内容变化时，更新滑动条位置
        def on_resistance_entry_change(event):
            try:
                resistance = float(self.resistance_entry.get())
                if 10 <= resistance <= 7500:
                    self.resistance_var.set(resistance)
            except ValueError:
                pass
        
        # 当按下回车键时，设置电阻值
        def on_resistance_entry_return(event):
            self.it8811_ctrl.set_resistance()
        
        # 绑定事件
        self.resistance_entry.bind("<KeyRelease>", on_resistance_entry_change)
        self.resistance_entry.bind("<Return>", on_resistance_entry_return)
        
        # 添加滑动条
        self.resistance_var = tk.DoubleVar(value=7500)  # 默认值设置为7500
        self.resistance_scale = ttk.Scale(
            resistance_frame, 
            from_=10, 
            to=7500, 
            orient=tk.HORIZONTAL, 
            length=200,
            variable=self.resistance_var,
            command=self.it8811_ctrl.update_resistance
        )
        self.resistance_scale.pack(side=tk.LEFT, padx=10)
        
        # 绑定滑动条释放事件
        self.resistance_scale.bind("<ButtonRelease-1>", self.it8811_ctrl.on_resistance_release)
        # 绑定鼠标滚轮事件
        self.resistance_scale.bind("<MouseWheel>", self.it8811_ctrl.on_mouse_wheel)
        
        ttk.Button(resistance_frame, text="设置电阻", command=self.it8811_ctrl.set_resistance).pack(side=tk.LEFT, padx=5)
        
        # 开关控制（滑动切换按钮）
        switch_frame = ttk.Frame(it8811_control_frame)
        switch_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(switch_frame, text="输出状态:", width=15).pack(side=tk.LEFT, padx=5)
        
        # 创建滑动切换按钮
        self.output_var = tk.BooleanVar(value=False)
        self.output_switch = ttk.Checkbutton(
            switch_frame, 
            text="",
            width=10,
            variable=self.output_var,
            command=self.it8811_ctrl.toggle_output,
            style="Switch.TCheckbutton"
        )
        self.output_switch.pack(side=tk.LEFT, padx=5)
        
        # 设置按钮样式
        style = ttk.Style()
        # 创建自定义开关样式
        style.configure("Switch.TCheckbutton", 
                       indicatoron=False,
                       width=10,
                       padding=4,
                       relief="flat",
                       background="#f44336",
                       foreground="white"
                      )
        style.map("Switch.TCheckbutton", 
                 background=[("selected", "#4CAF50"), ("!selected", "#f44336")],
                 foreground=[("selected", "white"), ("!selected", "white")]
                )
        
        # 设置初始状态为OFF
        self.output_state = "OFF"
        self.output_var.set(False)
        
        # 手动触发部分
        trigger_frame = ttk.LabelFrame(main_frame, text="手动触发", padding="10")
        trigger_frame.pack(fill=tk.X, pady=5)
        
        # 触发按钮
        self.trigger_button = ttk.Button(trigger_frame, text="手动触发记录", command=self.data_ops.manual_trigger, style="TButton")
        self.trigger_button.pack(pady=10)
        
        # 设置按钮样式
        style = ttk.Style()
        style.configure("TButton", font=(".SF NS Text", 12))
        
        # 数据显示
        data_frame = ttk.LabelFrame(main_frame, text="数据记录", padding="10")
        # 调整pack参数，不使用expand=True，限制表格高度
        data_frame.pack(fill=tk.X, pady=5, ipady=5)
        
        # 数据操作按钮
        button_frame = ttk.Frame(data_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # 清除测试数据按钮
        ttk.Button(button_frame, text="清除测试数据", command=self.data_ops.clear_test_data).pack(side=tk.RIGHT, padx=5)
        
        # 创建表格和滚动条的容器
        tree_frame = ttk.Frame(data_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建水平滚动条
        hscrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建表格，关联滚动条，并设置高度
        self.tree = ttk.Treeview(tree_frame, xscrollcommand=hscrollbar.set, height=3)
        # 配置滚动条
        hscrollbar.config(command=self.tree.xview)
        
        self.tree["columns"] = ("col1", "col2")
        self.tree.column("#0", width=150, minwidth=120, stretch=tk.NO)
        self.tree.column("col1", width=180, minwidth=150, stretch=tk.YES)
        self.tree.column("col2", width=180, minwidth=150, stretch=tk.YES)
        
        self.tree.heading("#0", text="设备")
        self.tree.heading("col1", text="触发1")
        self.tree.heading("col2", text="触发2")
        
        # 添加设备行
        self.tree.insert("", tk.END, text="IT8811 (电阻)")
        self.tree.insert("", tk.END, text="DMM6500 (电压)")
        self.tree.insert("", tk.END, text="KEYSIGHT 34461A (电流)")
        
        # 打包表格
        self.tree.pack(fill=tk.BOTH, expand=True)
    
    def log(self, message, level="INFO"):
        """输出实时日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
    
    def show_scan_status(self):
        """显示设备扫描状态"""
        # 更新设备状态为扫描中
        if hasattr(self, 'it8811_status'):
            self.it8811_status.config(text="扫描中...", foreground="orange")
        if hasattr(self, 'dmm6500_status'):
            self.dmm6500_status.config(text="扫描中...", foreground="orange")
        if hasattr(self, 'keysight_status'):
            self.keysight_status.config(text="扫描中...", foreground="orange")
        
        # 禁用设备操作按钮，防止用户在扫描过程中点击
        if hasattr(self, 'it8811_button'):
            self.it8811_button.config(state="disabled")
        if hasattr(self, 'dmm6500_button'):
            self.dmm6500_button.config(state="disabled")
        if hasattr(self, 'keysight_button'):
            self.keysight_button.config(state="disabled")
        
        # 显示系统提示
        self.log("正在扫描设备，请稍候...")
    
    def on_closing(self):
        """关闭窗口前的处理"""
        # 检查是否有数据需要保存
        if self.data_manager.data:
            # 显示确认对话框
            result = messagebox.askyesnocancel(
                "保存数据",
                "是否保存表格数据到CSV文件？",
                icon=messagebox.QUESTION
            )
            
            if result is None:
                # 取消关闭
                return
            elif result:
                # 保存数据
                self.data_ops.save_to_csv()
        
        # 关闭窗口
        self.root.destroy()
