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
        self.connection_manager = device_controller.connection_manager
        
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
            on_connect_status_change=self.on_device_status_change,
            on_rescan=self.on_rescan_clicked
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
        """新流程：扫描 → 自动连接（单一决策点，无双重触发）"""
        def on_device_found(display_text, resource, device_key):
            self.root.after(0, lambda: _update_list(display_text, resource, device_key))

        def _update_list(display_text, resource, device_key):
            if display_text not in current_list:
                current_list.append(display_text)
                current_info[display_text] = resource
                self.connection_panel.update_device_list(
                    current_list, current_info, None, None, None
                )

        current_list = []
        current_info = {}

        try:
            # Phase 1: 仅扫描（不触发连接）
            scan_result = self.device_controller.scan_devices(
                on_device_found=on_device_found
            )
            device_list, device_info, it8811, dmm, keysight = scan_result

            def phase2_connect():
                """Phase 2: 扫描完成后统一自动连接"""
                self.connection_panel.update_device_list(
                    device_list, device_info, it8811, dmm, keysight
                )

                if not any([it8811, dmm, keysight]):
                    self.connection_panel.on_scan_complete(False, "未找到设备")
                    logging.warning("扫描完成，未找到任何已知设备")
                    return

                self.connection_panel.status_label.config(
                    text="正在连接设备...", foreground="orange"
                )

                def on_connect(device_key, success, msg):
                    self.root.after(0, lambda: self._update_device_status(
                        device_key, success, msg
                    ))

                self.connection_manager.auto_connect(
                    scan_result, self.device_controller, on_connect=on_connect
                )

                # 检查最终状态
                connected_count = sum([
                    self.device_controller.it8811_connected,
                    self.device_controller.dmm6500_connected,
                    self.device_controller.keysight_34461a_connected,
                ])
                total = sum([1 for d in [it8811, dmm, keysight] if d])
                if connected_count == total:
                    msg = f"所有设备已连接 ({connected_count}/{total})"
                    self.connection_panel.on_scan_complete(True, msg)
                elif connected_count > 0:
                    msg = f"部分设备已连接 ({connected_count}/{total})"
                    self.connection_panel.on_scan_complete(True, msg)
                else:
                    msg = "设备连接失败，请检查后重新扫描"
                    self.connection_panel.on_scan_complete(False, msg)

            self.root.after(0, phase2_connect)

        except Exception as e:
            logging.error(f"扫描失败: {e}")
            self.root.after(0, lambda: self.connection_panel.on_scan_complete(
                False, f"扫描失败: {str(e)}"
            ))

    def on_rescan_clicked(self):
        """用户点击重新扫描按钮"""
        threading.Thread(target=self.rescan_devices, daemon=True).start()

    def rescan_devices(self):
        """重新扫描并连接（与 scan_devices 共享逻辑）"""
        def on_device_found(display_text, resource, device_key):
            self.root.after(0, lambda: _update_list(display_text, resource, device_key))

        def _update_list(display_text, resource, device_key):
            if display_text not in current_list:
                current_list.append(display_text)
                current_info[display_text] = resource
                self.connection_panel.update_device_list(
                    current_list, current_info, None, None, None
                )

        current_list = []
        current_info = {}

        # 先断开所有已连接设备
        if self.device_controller.dmm6500_connected:
            self.device_controller.disconnect_dmm6500()
        if self.device_controller.keysight_34461a_connected:
            self.device_controller.disconnect_keysight_34461a()
        if self.device_controller.it8811_connected:
            self.device_controller.disconnect_it8811()

        try:
            scan_result = self.device_controller.scan_devices(
                on_device_found=on_device_found
            )

            def reconnect():
                self.connection_panel.update_device_list(
                    scan_result[0], scan_result[1],
                    scan_result[2], scan_result[3], scan_result[4]
                )

                if not any([scan_result[2], scan_result[3], scan_result[4]]):
                    self.connection_panel.on_scan_complete(False, "未找到设备")
                    return

                self.connection_panel.status_label.config(
                    text="正在连接设备...", foreground="orange"
                )

                def on_connect(device_key, success, msg):
                    self.root.after(0, lambda: self._update_device_status(
                        device_key, success, msg
                    ))

                self.connection_manager.auto_connect(
                    scan_result, self.device_controller, on_connect=on_connect
                )

                connected = sum([
                    self.device_controller.it8811_connected,
                    self.device_controller.dmm6500_connected,
                    self.device_controller.keysight_34461a_connected,
                ])
                total = sum([1 for d in [
                    scan_result[2], scan_result[3], scan_result[4]
                ] if d])
                if connected == total:
                    self.connection_panel.on_scan_complete(True, f"所有设备已连接 ({connected}/{total})")
                elif connected > 0:
                    self.connection_panel.on_scan_complete(True, f"部分设备已连接 ({connected}/{total})")
                else:
                    self.connection_panel.on_scan_complete(False, "设备连接失败")

            self.root.after(0, reconnect)

        except Exception as e:
            logging.error(f"重新扫描失败: {e}")
            self.root.after(0, lambda: self.connection_panel.on_scan_complete(
                False, f"重新扫描失败: {str(e)}"
            ))

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

    def _update_device_status(self, device_key, success, msg):
        """统一的设备状态更新（供 scan_devices 和 rescan_devices 共用）"""
        status_map = {
            'it8811': ('it8811_status', 'it8811_button'),
            'dmm6500': ('dmm6500_status', 'dmm6500_button'),
            'keysight_34461a': ('keysight_status', 'keysight_button'),
        }
        mapper = {
            'it8811': 'it8811',
            'dmm6500': 'dmm6500',
            'keysight_34461a': 'keysight',
        }

        config = status_map.get(device_key)
        if not config:
            return

        status_attr, button_attr = config
        panel = self.connection_panel
        status_label = getattr(panel, status_attr)
        button = getattr(panel, button_attr)

        if success:
            status_label.config(text="已连接", foreground="green")
            button.config(text="断开")
        else:
            status_label.config(text="错误", foreground="red")
            panel._set_tooltip(status_label, msg)

        panel._set_connecting(mapper.get(device_key, device_key), False)
        button.config(state=tk.NORMAL)
        self.on_device_status_change(device_key, success)

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
