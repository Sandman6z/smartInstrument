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
        # 初始化 UI 状态
        self.root.after(0, lambda: self.connection_panel.it8811_status.config(text="扫描中...", foreground="orange"))
        
        # 实时更新列表
        current_list = []
        current_info = {}
        
        def on_device_found(display_text, resource, device_key):
            self.root.after(0, lambda: _update_incremental(display_text, resource, device_key))

        def _update_incremental(display_text, resource, device_key):
            # 更新数据
            if display_text not in current_list:
                current_list.append(display_text)
                current_info[display_text] = resource
                
                # 更新 UI 下拉列表
                # 注意：这里需要传入所有参数，所以如果只更新列表，可能需要调整 update_device_list 方法
                # 或者在这里手动更新 Combobox
                self.connection_panel.update_device_list(current_list, current_info, None, None, None)
                
                # 尝试自动连接
                if device_key == 'it8811' and not self.device_controller.it8811_connected:
                    self.connection_panel.it8811_resource.set(display_text)
                    self.connection_panel.connect_it8811()
                    
                elif device_key == 'dmm6500' and not self.device_controller.dmm6500_connected:
                    self.connection_panel.dmm6500_resource.set(display_text)
                    self.connection_panel.connect_dmm6500()
                    
                elif device_key == 'keysight_34461a' and not self.device_controller.keysight_34461a_connected:
                    self.connection_panel.keysight_resource.set(display_text)
                    self.connection_panel.connect_keysight()

        try:
            # 执行扫描（阻塞直到完成，但期间会触发回调）
            device_list, device_info, it8811, dmm, keysight = self.device_controller.scan_devices(on_device_found=on_device_found)
            
            # 扫描完成后的最终状态确认（更新最终的选择，防止自动连接遗漏）
            def final_update():
                self.connection_panel.update_device_list(device_list, device_info, it8811, dmm, keysight)
                
                # 恢复未连接设备的状态显示
                if not self.device_controller.it8811_connected:
                    self.connection_panel.it8811_status.config(text="未连接", foreground="red")
                if not self.device_controller.dmm6500_connected:
                    self.connection_panel.dmm6500_status.config(text="未连接", foreground="red")
                if not self.device_controller.keysight_34461a_connected:
                    self.connection_panel.keysight_status.config(text="未连接", foreground="red")
                
                # 如果有更好的匹配（例如优先 LAN），且当前未连接，则连接
                # 注意：如果在 _update_incremental 中已经连接了 USB，这里扫描完发现了 LAN，
                # 是否要切换？目前逻辑是保持已连接状态。
                # 如果还未连接，尝试连接最终推荐的
                if it8811 and not self.device_controller.it8811_connected:
                    # 更新选择
                    self.connection_panel.it8811_resource.set(it8811)
                    self.connection_panel.connect_it8811()
                if dmm and not self.device_controller.dmm6500_connected:
                    self.connection_panel.dmm6500_resource.set(dmm)
                    self.connection_panel.connect_dmm6500()
                if keysight and not self.device_controller.keysight_34461a_connected:
                    self.connection_panel.keysight_resource.set(keysight)
                    self.connection_panel.connect_keysight()
                
            self.root.after(0, final_update)
            
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
        
        # 禁用按钮
        self.trigger_button.config(state=tk.DISABLED)
        
        def task():
            try:
                # 检查控件是否存在 (防止窗口关闭后触发)
                try:
                    default_res = self.control_panel.value_entry.get()
                except AttributeError:
                    default_res = "7500" # 默认值

                # 并行获取所有数据
                measurements = self.device_controller.get_all_measurements(
                    default_resistance=default_res
                )
                
                res_success, resistance = measurements['resistance']
                volt_success, voltage = measurements['voltage']
                curr_success, current = measurements['current']
                
                # 如果电阻获取失败，使用默认值
                if not res_success and not resistance:
                    resistance = default_res

                if not volt_success: 
                    self.root.after(0, lambda: messagebox.showerror("错误", f"获取电压失败: {voltage}"))
                    return

                # 格式化电流
                if curr_success:
                    try:
                        val = float(current) * 1e6
                        current = f"{val:.6f}"
                    except: pass
                else:
                    current = ""
                
                # 格式化电压
                try:
                    val = float(voltage)
                    voltage = f"{val:.4f}"
                except: pass
                
                # 记录数据
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
                self.root.after(0, lambda: self.trigger_button.config(state=tk.NORMAL))
        
        # 使用持久化的线程池或单独线程（这里暂时保持单独线程，因为 threading.Thread 开销相对 VISA I/O 较小）
        # 如果频繁触发，建议在 MainWindow __init__ 中 self.executor = ThreadPoolExecutor(max_workers=1)
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
        # 确保设备正确断开连接
        try:
            self.device_controller.disconnect_it8811()
            self.device_controller.disconnect_dmm6500()
            self.device_controller.disconnect_keysight_34461a()
        except:
            pass
            
        if self.data_manager.data:
            if messagebox.askyesno("退出", "是否保存数据？"):
                self.save_to_csv()
        self.root.destroy()
