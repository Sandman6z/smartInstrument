import sys
import os

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
else:
    # 作为模块导入时，使用相对导入
    from .device.controller import DeviceController
    from .data.manager import DataManager
    from .config import Config

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pyvisa
import csv
from datetime import datetime
import threading

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
        
        # 采集状态标志，确保同一时间只有一个采集请求在处理
        self.is_collecting = False
        
        # 创建GUI
        self.create_widgets()
        
        # 在后台线程中扫描设备，确保UI先打开
        def scan_devices_thread():
            self.scan_devices()
        
        thread = threading.Thread(target=scan_devices_thread)
        thread.daemon = True
        thread.start()
    
    def create_widgets(self):
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="保存数据到CSV", command=self.save_to_csv)
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
        
        # IT8811连接
        it8811_frame = ttk.Frame(device_frame)
        it8811_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(it8811_frame, text="IT8811资源:", width=15).pack(side=tk.LEFT, padx=5)
        self.it8811_resource = ttk.Combobox(it8811_frame, width=30)
        self.it8811_resource.pack(side=tk.LEFT, padx=5)
        
        self.it8811_button = ttk.Button(it8811_frame, text="连接", command=self.connect_it8811)
        self.it8811_button.pack(side=tk.LEFT, padx=5)
        self.it8811_status = ttk.Label(it8811_frame, text="未连接", foreground="red")
        self.it8811_status.pack(side=tk.LEFT, padx=5)
        
        # DMM6500连接
        dmm6500_frame = ttk.Frame(device_frame)
        dmm6500_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dmm6500_frame, text="DMM6500资源:", width=15).pack(side=tk.LEFT, padx=5)
        self.dmm6500_resource = ttk.Combobox(dmm6500_frame, width=30)
        self.dmm6500_resource.pack(side=tk.LEFT, padx=5)
        
        self.dmm6500_button = ttk.Button(dmm6500_frame, text="连接", command=self.connect_dmm6500)
        self.dmm6500_button.pack(side=tk.LEFT, padx=5)
        self.dmm6500_status = ttk.Label(dmm6500_frame, text="未连接", foreground="red")
        self.dmm6500_status.pack(side=tk.LEFT, padx=5)
        
        # KEYSIGHT 34461A连接
        keysight_frame = ttk.Frame(device_frame)
        keysight_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(keysight_frame, text="KEYSIGHT资源:", width=15).pack(side=tk.LEFT, padx=5)
        self.keysight_resource = ttk.Combobox(keysight_frame, width=30)
        self.keysight_resource.pack(side=tk.LEFT, padx=5)
        
        self.keysight_button = ttk.Button(keysight_frame, text="连接", command=self.connect_keysight_34461a)
        self.keysight_button.pack(side=tk.LEFT, padx=5)
        self.keysight_status = ttk.Label(keysight_frame, text="未连接", foreground="red")
        self.keysight_status.pack(side=tk.LEFT, padx=5)
        
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
            self.set_resistance()
        
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
            command=self.update_resistance
        )
        self.resistance_scale.pack(side=tk.LEFT, padx=10)
        
        # 绑定滑动条释放事件
        self.resistance_scale.bind("<ButtonRelease-1>", self.on_resistance_release)
        # 绑定鼠标滚轮事件
        self.resistance_scale.bind("<MouseWheel>", self.on_mouse_wheel)
        
        ttk.Button(resistance_frame, text="设置电阻", command=self.set_resistance).pack(side=tk.LEFT, padx=5)
        
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
            command=self.toggle_output,
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
        self.trigger_button = ttk.Button(trigger_frame, text="手动触发记录", command=self.manual_trigger, style="TButton")
        self.trigger_button.pack(pady=10)
        self.trigger_button.config(state=tk.DISABLED)  # 默认禁用
        
        # 设置按钮样式
        style = ttk.Style()
        style.configure("TButton", font=(".SF NS Text", 12))
        
        # 禁用设备调节组件
        self.resistance_entry.config(state=tk.DISABLED)
        self.resistance_scale.config(state=tk.DISABLED)
        self.output_switch.config(state=tk.DISABLED)
        
        # 数据显示
        data_frame = ttk.LabelFrame(main_frame, text="数据记录", padding="10")
        # 调整pack参数，不使用expand=True，限制表格高度
        data_frame.pack(fill=tk.X, pady=5, ipady=5)
        
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
        
        # 添加清除测试数据按钮
        clear_frame = ttk.Frame(data_frame)
        clear_frame.pack(fill=tk.X, pady=5)
        
        self.clear_data_button = ttk.Button(
            clear_frame, 
            text="清除测试数据", 
            command=self.confirm_clear_data,
            style="TButton"
        )
        self.clear_data_button.pack(side=tk.RIGHT, padx=5)
    
    def scan_devices(self):
        """扫描可用的VISA设备"""
        # 更新状态为扫描中
        self.it8811_status.config(text="扫描中...", foreground="orange")
        self.dmm6500_status.config(text="扫描中...", foreground="orange")
        self.keysight_status.config(text="扫描中...", foreground="orange")
        
        # 禁用下拉框，避免用户在扫描过程中进行操作
        self.it8811_resource.config(state=tk.DISABLED)
        self.dmm6500_resource.config(state=tk.DISABLED)
        self.keysight_resource.config(state=tk.DISABLED)
        
        try:
            # 使用device_controller扫描设备
            device_list, self.device_info, it8811_device, dmm6500_device, keysight_34461a_device = self.device_controller.scan_devices()
            
            # 如果没有找到设备，显示提示
            if not device_list:
                messagebox.showinfo("提示", "未找到任何VISA设备")
                self.log("未找到任何VISA设备")
                # 更新状态为未连接
                self.it8811_status.config(text="未连接", foreground="red")
                self.dmm6500_status.config(text="未连接", foreground="red")
                self.keysight_status.config(text="未连接", foreground="red")
            else:
                msg = f"找到设备数量: {len(device_list)}"
                print(msg)
                self.log(msg)
                msg = f"设备列表: {device_list}"
                print(msg)
                self.log(msg)
            
            # 重新启用下拉框
            self.it8811_resource.config(state=tk.NORMAL)
            self.dmm6500_resource.config(state=tk.NORMAL)
            self.keysight_resource.config(state=tk.NORMAL)
            
            # 设置设备列表
            self.it8811_resource['values'] = device_list
            self.dmm6500_resource['values'] = device_list
            self.keysight_resource['values'] = device_list
            
            # 自动选择设备
            if it8811_device:
                self.it8811_resource.set(it8811_device)
                msg = f"自动选择IT8811设备: {it8811_device}"
                print(msg)
                self.log(msg)
            if dmm6500_device:
                self.dmm6500_resource.set(dmm6500_device)
                msg = f"自动选择DMM6500设备: {dmm6500_device}"
                print(msg)
                self.log(msg)
            if keysight_34461a_device:
                self.keysight_resource.set(keysight_34461a_device)
                msg = f"自动选择KEYSIGHT 34461A设备: {keysight_34461a_device}"
                print(msg)
                self.log(msg)
                
            # 如果找到设备，自动连接
            if it8811_device or dmm6500_device or keysight_34461a_device:
                found_devices = []
                if it8811_device:
                    found_devices.append("IT8811")
                    # 自动连接IT8811
                    self.auto_connect_it8811()
                if dmm6500_device:
                    found_devices.append("DMM6500")
                    # 自动连接DMM6500
                    self.auto_connect_dmm6500()
                if keysight_34461a_device:
                    found_devices.append("KEYSIGHT 34461A")
                    # 自动连接KEYSIGHT 34461A
                    self.auto_connect_keysight_34461a()
                msg = f"已自动识别并选择以下设备: {', '.join(found_devices)}"
                self.log(msg)
        except Exception as e:
            error_msg = f"扫描设备失败: {str(e)}"
            print(error_msg)
            self.log(error_msg, level="ERROR")
            messagebox.showerror("错误", error_msg)
        finally:
            # 无论扫描成功还是失败，都重新启用下拉框
            self.it8811_resource.config(state=tk.NORMAL)
            self.dmm6500_resource.config(state=tk.NORMAL)
            self.keysight_resource.config(state=tk.NORMAL)
    
    def connect_it8811(self):
        """连接IT8811（非阻塞式）"""
        selected_text = self.it8811_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择IT8811资源")
            return
        
        # 获取实际的设备地址
        resource = self.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.it8811_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.device_controller.connect_it8811(resource)
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.it8811_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: self.it8811_button.config(text="断开", command=self.disconnect_it8811))
                    self.root.after(0, lambda: self.log(msg))
                    # 启用IT8811调节组件
                    self.root.after(0, lambda: self.resistance_entry.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.resistance_scale.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.output_switch.config(state=tk.NORMAL))
                    # 检查是否所有设备都已连接，启用手动触发按钮
                    self.root.after(0, self.check_all_devices_connected)
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.it8811_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接IT8811失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.it8811_status.config(text="未连接", foreground="red"))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def disconnect_it8811(self):
        """断开IT8811连接（非阻塞式）"""
        # 显示断开中状态
        self.it8811_status.config(text="断开中...", foreground="orange")
        
        # 创建后台线程执行断开操作
        def disconnect_thread():
            try:
                # 使用device_controller断开连接
                success, msg = self.device_controller.disconnect_it8811()
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.it8811_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: self.it8811_button.config(text="连接", command=self.connect_it8811))
                    self.root.after(0, lambda: self.log(msg))
                    # 禁用IT8811调节组件
                    self.root.after(0, lambda: self.resistance_entry.config(state=tk.DISABLED))
                    self.root.after(0, lambda: self.resistance_scale.config(state=tk.DISABLED))
                    self.root.after(0, lambda: self.output_switch.config(state=tk.DISABLED))
                    # 检查是否所有设备都已连接，禁用手动触发按钮
                    self.root.after(0, self.check_all_devices_connected)
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.it8811_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"断开IT8811连接失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.it8811_status.config(text="已连接", foreground="green"))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=disconnect_thread)
        thread.daemon = True
        thread.start()
    
    def auto_connect_it8811(self):
        """自动连接IT8811"""
        selected_text = self.it8811_resource.get()
        if not selected_text:
            return
        
        # 获取实际的设备地址
        resource = self.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.it8811_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.device_controller.connect_it8811(resource)
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.it8811_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: self.it8811_button.config(text="断开", command=self.disconnect_it8811))
                    self.root.after(0, lambda: self.log(msg))
                    # 启用IT8811调节组件
                    self.root.after(0, lambda: self.resistance_entry.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.resistance_scale.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.output_switch.config(state=tk.NORMAL))
                    # 检查是否所有设备都已连接，启用手动触发按钮
                    self.root.after(0, self.check_all_devices_connected)
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.it8811_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接IT8811失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.it8811_status.config(text="未连接", foreground="red"))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def auto_connect_dmm6500(self):
        """自动连接DMM6500"""
        selected_text = self.dmm6500_resource.get()
        if not selected_text:
            return
        
        # 获取实际的设备地址
        resource = self.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.dmm6500_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.device_controller.connect_dmm6500(resource)
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.dmm6500_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: self.dmm6500_button.config(text="断开", command=self.disconnect_dmm6500))
                    self.root.after(0, lambda: self.log(msg))
                    # 检查是否所有设备都已连接，启用手动触发按钮
                    self.root.after(0, self.check_all_devices_connected)
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.dmm6500_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接DMM6500失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.dmm6500_status.config(text="未连接", foreground="red"))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def auto_connect_keysight_34461a(self):
        """自动连接KEYSIGHT 34461A"""
        selected_text = self.keysight_resource.get()
        if not selected_text:
            return
        
        # 获取实际的设备地址
        resource = self.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.keysight_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.device_controller.connect_keysight_34461a(resource)
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.keysight_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: self.keysight_button.config(text="断开", command=self.disconnect_keysight_34461a))
                    self.root.after(0, lambda: self.log(msg))
                    # 检查是否所有设备都已连接，启用手动触发按钮
                    self.root.after(0, self.check_all_devices_connected)
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.keysight_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接KEYSIGHT 34461A失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.keysight_status.config(text="未连接", foreground="red"))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def connect_dmm6500(self):
        """连接DMM6500（非阻塞式）"""
        selected_text = self.dmm6500_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择DMM6500资源")
            return
        
        # 获取实际的设备地址
        resource = self.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.dmm6500_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.device_controller.connect_dmm6500(resource)
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.dmm6500_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: self.dmm6500_button.config(text="断开", command=self.disconnect_dmm6500))
                    self.root.after(0, lambda: self.log(msg))
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.dmm6500_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接DMM6500失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.dmm6500_status.config(text="未连接", foreground="red"))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def connect_keysight_34461a(self):
        """连接KEYSIGHT 34461A（非阻塞式）"""
        selected_text = self.keysight_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择KEYSIGHT资源")
            return
        
        # 获取实际的设备地址
        resource = self.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.keysight_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.device_controller.connect_keysight_34461a(resource)
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.keysight_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: self.keysight_button.config(text="断开", command=self.disconnect_keysight_34461a))
                    self.root.after(0, lambda: self.log(msg))
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.keysight_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接KEYSIGHT 34461A失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.keysight_status.config(text="未连接", foreground="red"))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def disconnect_dmm6500(self):
        """断开DMM6500连接（非阻塞式）"""
        # 显示断开中状态
        self.dmm6500_status.config(text="断开中...", foreground="orange")
        
        # 创建后台线程执行断开操作
        def disconnect_thread():
            try:
                # 使用device_controller断开连接
                success, msg = self.device_controller.disconnect_dmm6500()
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.dmm6500_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: self.dmm6500_button.config(text="连接", command=self.connect_dmm6500))
                    self.root.after(0, lambda: self.log(msg))
                    # 检查是否所有设备都已连接，禁用手动触发按钮
                    self.root.after(0, self.check_all_devices_connected)
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.dmm6500_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"断开DMM6500连接失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.dmm6500_status.config(text="已连接", foreground="green"))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=disconnect_thread)
        thread.daemon = True
        thread.start()
    
    def disconnect_keysight_34461a(self):
        """断开KEYSIGHT 34461A连接（非阻塞式）"""
        # 显示断开中状态
        self.keysight_status.config(text="断开中...", foreground="orange")
        
        # 创建后台线程执行断开操作
        def disconnect_thread():
            try:
                # 使用device_controller断开连接
                success, msg = self.device_controller.disconnect_keysight_34461a()
                if success:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.keysight_status.config(text="未连接", foreground="red"))
                    self.root.after(0, lambda: self.keysight_button.config(text="连接", command=self.connect_keysight_34461a))
                    self.root.after(0, lambda: self.log(msg))
                    # 检查是否所有设备都已连接，禁用手动触发按钮
                    self.root.after(0, self.check_all_devices_connected)
                else:
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.keysight_status.config(text="已连接", foreground="green"))
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"断开KEYSIGHT 34461A连接失败: {str(e)}"
                # 在主线程中更新UI
                self.root.after(0, lambda: self.keysight_status.config(text="已连接", foreground="green"))
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=disconnect_thread)
        thread.daemon = True
        thread.start()
    
    def set_resistance(self):
        """设置IT8811的电阻值（非阻塞式）"""
        try:
            resistance = self.resistance_entry.get()
            # 验证输入是否为数字
            try:
                float(resistance)
            except ValueError:
                messagebox.showerror("错误", "请输入有效的电阻值")
                return
            
            # 验证电阻值是否在有效范围内
            try:
                resistance_value = float(resistance)
                if resistance_value < 10:
                    messagebox.showerror("错误", "电阻值不能小于10Ω")
                    return
                if resistance_value > 7500:
                    messagebox.showerror("错误", "电阻值不能超过7500Ω")
                    return
            except ValueError:
                messagebox.showerror("错误", "请输入有效的电阻值")
                return
            
            # 创建后台线程执行设置电阻操作
            def set_resistance_thread():
                try:
                    # 使用device_controller设置电阻值
                    success, msg = self.device_controller.set_resistance(resistance)
                    if success:
                        # 在主线程中更新UI
                        self.root.after(0, lambda: self.log(msg))
                    else:
                        # 在主线程中更新UI
                        self.root.after(0, lambda: messagebox.showerror("错误", msg))
                        self.root.after(0, lambda: self.log(msg, level="ERROR"))
                except Exception as e:
                    error_msg = f"设置电阻值失败: {str(e)}"
                    # 在主线程中更新UI
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
            
            # 启动后台线程
            thread = threading.Thread(target=set_resistance_thread)
            thread.daemon = True
            thread.start()
        except Exception as e:
            error_msg = f"设置电阻值失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            self.log(error_msg, level="ERROR")
    
    def update_resistance(self, value):
        """更新电阻值"""
        # 同步滑动条值到输入框
        resistance = int(float(value))
        self.resistance_entry.delete(0, tk.END)
        self.resistance_entry.insert(0, str(resistance))
    
    def on_resistance_release(self, event):
        """滑动条释放时设置电阻值"""
        # 获取当前滑动条值
        resistance = int(self.resistance_var.get())
        # 更新输入框
        self.resistance_entry.delete(0, tk.END)
        self.resistance_entry.insert(0, str(resistance))
        # 调用设置电阻方法
        self.set_resistance()
    
    def on_mouse_wheel(self, event):
        """鼠标滚轮调节电阻值"""
        # 获取当前值
        current_value = self.resistance_var.get()
        # 计算新值（每次滚动调整10Ω）
        if event.delta > 0:  # 向上滚动
            new_value = min(current_value + 10, 7500)
        else:  # 向下滚动
            new_value = max(current_value - 10, 10)
        # 更新滑动条值
        self.resistance_var.set(new_value)
        # 更新输入框
        resistance = int(new_value)
        self.resistance_entry.delete(0, tk.END)
        self.resistance_entry.insert(0, str(resistance))
        # 即刻生效，设置电阻值
        self.set_resistance()
    
    def toggle_output(self):
        """控制IT8811的输出开关（非阻塞式）"""
        # 获取当前状态并切换
        new_state = "ON" if self.output_state == "OFF" else "OFF"
        
        # 临时更新按钮状态，稍后根据实际结果再调整
        self.output_var.set(new_state == "ON")
        
        # 创建后台线程执行输出控制操作
        def toggle_thread():
            try:
                # 使用device_controller控制输出
                success, msg = self.device_controller.toggle_output(new_state)
                if success:
                    # 更新实际状态
                    self.output_state = new_state
                    # 在主线程中更新UI
                    self.root.after(0, lambda: self.log(msg))
                else:
                    # 恢复按钮状态
                    self.root.after(0, lambda: self.output_var.set(self.output_state == "ON"))
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                # 恢复按钮状态
                self.root.after(0, lambda: self.output_var.set(self.output_state == "ON"))
                error_msg = f"控制输出失败: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=toggle_thread)
        thread.daemon = True
        thread.start()
    
    def manual_trigger(self):
        """手动触发记录数据（非阻塞式）"""
        # 检查是否正在采集数据，如果是则拒绝新的采集请求
        if self.is_collecting:
            self.log("正在采集数据，请稍后再试", level="WARNING")
            return
        
        # 设置采集状态标志为True
        self.is_collecting = True
        
        # 创建后台线程执行数据采集操作
        def trigger_thread():
            try:
                # 获取IT8811的电阻数据
                res_success, resistance = self.device_controller.get_resistance()
                if not res_success:
                    # 如果获取电阻值失败，使用输入框中的值
                    resistance = self.resistance_entry.get()
                    self.root.after(0, lambda: self.log(f"获取电阻值失败，使用输入框值: {resistance}Ω", level="WARNING"))
                
                # 获取DMM6500的电压数据
                volt_success, voltage = self.device_controller.get_voltage()
                if not volt_success:
                    self.root.after(0, lambda: messagebox.showerror("错误", voltage))
                    self.root.after(0, lambda: self.log(voltage, level="ERROR"))
                    return
                
                # 格式化电压值，保留小数点后四位，四舍五入，不使用科学计数法
                try:
                    voltage_value = float(voltage)
                    formatted_voltage = f"{voltage_value:.4f}"
                    voltage = formatted_voltage
                except ValueError:
                    # 如果电压值格式不正确，保持原样
                    pass
                
                # 获取KEYSIGHT 34461A的电流数据
                curr_success, current = self.device_controller.get_current()
                if not curr_success:
                    current = ""
                    self.root.after(0, lambda: self.log(f"获取电流值失败: {current}", level="WARNING"))
                else:
                    # 格式化电流值，从A转换为uA（乘以1,000,000），保持原有精度
                    try:
                        current_value = float(current)
                        # 从A转换为uA
                        current_value_uA = current_value * 1000000
                        # 保持原有精度，使用与原始值相同的小数位数
                        current_str = str(current)
                        if 'E' in current_str:
                            # 科学计数法，保持精度
                            formatted_current = f"{current_value_uA:.6f}"
                        else:
                            # 普通格式，保持精度
                            decimal_places = len(current_str.split('.')[1]) if '.' in current_str else 0
                            format_str = f"{{:.{decimal_places}f}}"
                            formatted_current = format_str.format(current_value_uA)
                        current = formatted_current
                    except ValueError:
                        # 如果电流值格式不正确，保持原样
                        pass
                
                # 记录数据
                success, msg = self.data_manager.record_data(resistance, voltage, current)
                if success:
                    # 更新表格
                    col_count = msg
                    col_name = f"col{col_count}"
                    
                    # 在主线程中更新UI
                    def update_tree():
                        # 更新表格
                        if col_name not in self.tree["columns"]:
                            self.tree["columns"] = self.tree["columns"] + (col_name,)
                            self.tree.column(col_name, width=150, minwidth=100, stretch=tk.YES)
                            self.tree.heading(col_name, text=f"触发{col_count}")
                        
                        # 插入数据
                        self.tree.set(self.tree.get_children()[0], col_name, resistance)
                        self.tree.set(self.tree.get_children()[1], col_name, voltage)
                        if len(self.tree.get_children()) > 2:
                            self.tree.set(self.tree.get_children()[2], col_name, current)
                        
                        log_message = f"数据采集成功: 电阻={resistance}Ω, 电压={voltage}V"
                        if current:
                            log_message += f", 电流={current}A"
                        self.log(log_message)
                    
                    self.root.after(0, update_tree)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.root.after(0, lambda: self.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"手动触发失败: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.root.after(0, lambda: self.log(error_msg, level="ERROR"))
            finally:
                # 无论采集成功与否，都将采集状态标志设置为False
                self.is_collecting = False
        
        # 启动后台线程
        thread = threading.Thread(target=trigger_thread)
        thread.daemon = True
        thread.start()
    
    def record_data(self):
        """记录数据"""
        try:
            # 检查设备是否连接
            if not hasattr(self, 'device_controller') or not self.device_controller.it8811_connected:
                messagebox.showerror("错误", "请先连接IT8811设备")
                return
            
            if not hasattr(self, 'device_controller') or not self.device_controller.dmm6500_connected:
                messagebox.showerror("错误", "请先连接DMM6500设备")
                return
            
            # 获取IT8811的电阻数据
            res_success, resistance = self.device_controller.get_resistance()
            if not res_success:
                # 如果获取电阻值失败，使用输入框中的值
                resistance = self.resistance_entry.get()
                self.log(f"获取电阻值失败，使用输入框值: {resistance}Ω", level="WARNING")
            
            # 获取DMM6500的电压数据
            volt_success, voltage = self.device_controller.get_voltage()
            if not volt_success:
                messagebox.showerror("错误", voltage)
                self.log(voltage, level="ERROR")
                return
            
            # 格式化电压值，保留小数点后四位，四舍五入，不使用科学计数法
            try:
                voltage_value = float(voltage)
                formatted_voltage = f"{voltage_value:.4f}"
                voltage = formatted_voltage
            except ValueError:
                # 如果电压值格式不正确，保持原样
                pass
            
            # 记录数据
            success, msg = self.data_manager.record_data(resistance, voltage, "")
            if success:
                # 更新表格
                col_count = msg
                col_name = f"col{col_count}"
                
                # 在主线程中更新UI
                def update_tree():
                    # 更新表格
                    if col_name not in self.tree["columns"]:
                        self.tree["columns"] = self.tree["columns"] + (col_name,)
                        self.tree.column(col_name, width=150, minwidth=100, stretch=tk.YES)
                        self.tree.heading(col_name, text=f"触发{col_count}")
                    
                    # 插入数据
                    try:
                        self.tree.set(self.tree.get_children()[0], col_name, resistance)
                        self.tree.set(self.tree.get_children()[1], col_name, voltage)
                    except Exception as e:
                        self.log(f"更新表格失败: {str(e)}", level="ERROR")
                    
                    log_message = f"数据采集成功: 电阻={resistance}Ω, 电压={voltage}V"
                    self.log(log_message)
                
                self.root.after(0, update_tree)
            else:
                messagebox.showerror("错误", msg)
                self.log(msg, level="ERROR")
        except Exception as e:
            error_msg = f"记录数据失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            self.log(error_msg, level="ERROR")
    
    def save_to_csv(self):
        """保存数据到CSV文件"""
        try:
            success, msg, filename = self.data_manager.save_to_csv()
            if success:
                # 创建自定义对话框
                dialog = tk.Toplevel(self.root)
                dialog.title("保存成功")
                dialog.geometry("300x120")
                dialog.transient(self.root)
                dialog.grab_set()
                
                # 计算并设置对话框位置到屏幕中心
                dialog.update_idletasks()
                width = dialog.winfo_width()
                height = dialog.winfo_height()
                x = (dialog.winfo_screenwidth() // 2) - (width // 2)
                y = (dialog.winfo_screenheight() // 2) - (height // 2)
                dialog.geometry(f"{width}x{height}+{x}+{y}")
                
                # 显示消息
                label = ttk.Label(dialog, text=msg, padding=10)
                label.pack(fill=tk.X, pady=10)
                
                # 创建按钮框架
                button_frame = ttk.Frame(dialog)
                button_frame.pack(fill=tk.X, pady=5)
                
                # 打开按钮
                def open_csv():
                    import os
                    import subprocess
                    try:
                        # 打开CSV文件
                        if os.name == 'nt':  # Windows
                            os.startfile(filename)
                        elif os.name == 'posix':  # macOS/Linux
                            subprocess.call(['open', filename])
                        dialog.destroy()
                    except Exception as e:
                        messagebox.showerror("错误", f"打开文件失败: {str(e)}")
                
                open_button = ttk.Button(button_frame, text="打开", command=open_csv)
                open_button.pack(side=tk.RIGHT, padx=5)
                
                # 确定按钮
                ok_button = ttk.Button(button_frame, text="确定", command=dialog.destroy)
                ok_button.pack(side=tk.RIGHT, padx=5)
                
                self.log(msg)
            else:
                messagebox.showerror("错误", msg)
                self.log(msg, level="ERROR")
        except Exception as e:
            error_msg = f"保存数据失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            self.log(error_msg, level="ERROR")
    
    def __del__(self):
        """清理资源"""
        # 资源由device_controller管理，不需要在这里清理
        pass
    
    def log(self, message, level="INFO"):
        """输出实时日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
    
    def confirm_clear_data(self):
        """确认清除测试数据"""
        # 检查是否有数据需要清除
        if not self.data_manager.data:
            messagebox.showinfo("提示", "表格中没有数据可清除")
            return
        
        # 显示确认对话框
        result = messagebox.askyesno(
            "确认清除",
            "确定要清除所有测试数据吗？此操作不可撤销。",
            icon=messagebox.WARNING
        )
        
        if result:
            # 用户确认，执行清除操作
            self.clear_test_data()
    
    def clear_test_data(self):
        """清除测试数据"""
        try:
            # 调用DataManager的clear_data方法清空数据
            success, msg = self.data_manager.clear_data()
            if success:
                # 重置表格结构
                # 清除所有设备行的数据
                for item in self.tree.get_children():
                    # 清除所有列的数据
                    columns = list(self.tree["columns"])
                    for col in columns:
                        self.tree.set(item, col, "")
                
                # 显示成功消息
                messagebox.showinfo("成功", msg)
                self.log(msg)
            else:
                messagebox.showerror("错误", msg)
                self.log(msg, level="ERROR")
        except Exception as e:
            error_msg = f"清除测试数据失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            self.log(error_msg, level="ERROR")
    
    def check_all_devices_connected(self):
        """检查所有设备是否已连接，启用手动触发按钮"""
        # 检查设备连接状态
        if (hasattr(self.device_controller, 'it8811_connected') and self.device_controller.it8811_connected and
            hasattr(self.device_controller, 'dmm6500_connected') and self.device_controller.dmm6500_connected and
            hasattr(self.device_controller, 'keysight_34461a_connected') and self.device_controller.keysight_34461a_connected):
            # 启用手动触发按钮
            self.trigger_button.config(state=tk.NORMAL)
        else:
            # 禁用手动触发按钮
            self.trigger_button.config(state=tk.DISABLED)
    
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
                success, msg, filename = self.data_manager.save_to_csv()
                if success:
                    self.log(msg)
                else:
                    self.log(msg, level="ERROR")
        
        # 关闭窗口
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTestTool(root)
    root.mainloop()
