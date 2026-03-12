import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import os
from ..config import Config
from .components.connection_panel import ConnectionPanel
from .components.control_panel import ControlPanel
from .components.data_panel import DataPanel

class MainWindow:
    def __init__(self, root, device_controller, data_manager):
        self.root = root
        self.device_controller = device_controller
        self.data_manager = data_manager
        
        self.root.title(Config.WINDOW_TITLE)
        self.root.geometry(Config.WINDOW_GEOMETRY)
        
        self.is_collecting = False
        
        self.create_widgets()
        self.setup_menu()
        
        # 启动扫描
        threading.Thread(target=self.scan_devices, daemon=True).start()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 连接面板
        self.connection_panel = ConnectionPanel(
            main_frame, 
            self.device_controller,
            on_connect_status_change=self.on_device_status_change
        )
        self.connection_panel.pack(fill=tk.X, pady=5)
        
        # 2. 控制面板
        self.control_panel = ControlPanel(main_frame, self.device_controller)
        self.control_panel.pack(fill=tk.X, pady=5)
        
        # 3. 手动触发
        trigger_frame = ttk.LabelFrame(main_frame, text="手动触发", padding="10")
        trigger_frame.pack(fill=tk.X, pady=5)
        
        # 样式
        style = ttk.Style()
        style.configure("Trigger.TButton", font=(".SF NS Text", 12, "bold"), padding=(20, 10), background="#FF9800")
        
        self.trigger_button = ttk.Button(
            trigger_frame, 
            text="手动触发", 
            command=self.manual_trigger, 
            style="Trigger.TButton"
        )
        self.trigger_button.pack(pady=10)
        self.trigger_button.config(state=tk.DISABLED)
        
        # 4. 数据面板
        self.data_panel = DataPanel(main_frame, self.data_manager)
        self.data_panel.pack(fill=tk.BOTH, expand=True, pady=5)

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="保存数据到CSV", command=self.save_to_csv)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.on_closing)
        menubar.add_cascade(label="文件", menu=file_menu)
        self.root.config(menu=menubar)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def scan_devices(self):
        # 禁用 UI
        self.root.after(0, lambda: self.connection_panel.it8811_status.config(text="扫描中...", foreground="orange"))
        
        try:
            device_list, device_info, it8811, dmm, keysight = self.device_controller.scan_devices()
            
            def update_ui():
                self.connection_panel.update_device_list(device_list, device_info, it8811, dmm, keysight)
                # 重置状态显示，具体状态由连接结果决定
                self.connection_panel.it8811_status.config(text="未连接", foreground="red") 
                self.connection_panel.dmm6500_status.config(text="未连接", foreground="red")
                self.connection_panel.keysight_status.config(text="未连接", foreground="red")
                
                # 自动连接逻辑
                if it8811: self.connection_panel.connect_it8811()
                if dmm: self.connection_panel.connect_dmm6500()
                if keysight: self.connection_panel.connect_keysight()
                
            self.root.after(0, update_ui)
        except Exception as e:
            logging.error(f"扫描失败: {e}")

    def on_device_status_change(self, device_type, connected):
        # 检查是否所有设备都连接，启用触发按钮
        all_connected = (
            self.device_controller.it8811_connected and
            self.device_controller.dmm6500_connected and
            self.device_controller.keysight_34461a_connected
        )
        if all_connected:
            self.trigger_button.config(state=tk.NORMAL)
        else:
            self.trigger_button.config(state=tk.DISABLED)
            
        # IT8811 连接状态影响控制面板
        if device_type == 'it8811':
            if connected:
                self.control_panel.enable_controls()
            else:
                self.control_panel.disable_controls()

    def manual_trigger(self):
        if self.is_collecting:
            return
        self.is_collecting = True
        
        def task():
            try:
                # 1. 获取电阻
                res_success, resistance = self.device_controller.get_resistance()
                if not res_success: resistance = self.control_panel.resistance_entry.get()
                
                # 2. 获取电压
                volt_success, voltage = self.device_controller.get_voltage()
                if not volt_success: 
                    self.root.after(0, lambda: messagebox.showerror("错误", voltage))
                    return

                # 3. 获取电流
                curr_success, current = self.device_controller.get_current()
                if not curr_success: current = ""
                else:
                    # 格式化电流
                    try:
                        val = float(current) * 1e6
                        current = f"{val:.6f}"
                    except: pass
                
                # 格式化电压
                try:
                    val = float(voltage)
                    voltage = f"{val:.4f}"
                except: pass
                
                # 4. 记录数据
                success, count = self.data_manager.record_data(resistance, voltage, current)
                if success:
                    self.root.after(0, lambda: self.data_panel.add_data_column(count, resistance, voltage, current))
                    logging.info(f"采集成功: R={resistance}, V={voltage}, I={current}")
                else:
                    logging.error(f"记录失败: {count}")

            except Exception as e:
                logging.error(f"触发失败: {e}")
            finally:
                self.is_collecting = False
        
        threading.Thread(target=task, daemon=True).start()

    def save_to_csv(self):
        success, msg, filename = self.data_manager.save_to_csv()
        if success:
            if messagebox.askyesno("保存成功", f"{msg}\n是否打开文件？"):
                try:
                    if os.name == 'nt':
                        os.startfile(filename)
                    else:
                        subprocess.call(['open', filename])
                except Exception as e:
                    messagebox.showerror("错误", str(e))
        else:
            messagebox.showerror("错误", msg)

    def on_closing(self):
        if self.data_manager.data:
            if messagebox.askyesno("退出", "是否保存数据？"):
                self.save_to_csv()
        self.root.destroy()
