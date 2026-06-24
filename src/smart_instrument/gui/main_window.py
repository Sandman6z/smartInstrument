import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import os
import time
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
        self._stop_collecting = False

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
        self.control_panel.set_auto_collect_callback(self.auto_collect)
        self.control_panel.set_stop_collect_callback(self.stop_auto_collect)
        self.control_panel.set_output_state_callback(self.on_output_state_changed)
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
        # 初始状态提示：让用户知道正在扫描
        self.root.after(0, lambda: self.connection_panel.status_label.config(
            text="正在扫描设备...", foreground="orange"
        ))

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

                def do_auto_connect():
                    """在后台线程执行连接，避免阻塞主线程 UI"""
                    self.connection_manager.auto_connect(
                        scan_result, self.device_controller, on_connect=on_connect
                    )

                    # 检查最终状态（在后台线程计算，在主线程更新 UI）
                    connected_count = sum([
                        self.device_controller.it8811_connected,
                        self.device_controller.dmm6500_connected,
                        self.device_controller.keysight_34461a_connected,
                    ])
                    total = sum([1 for d in [it8811, dmm, keysight] if d])

                    def report_status():
                        if connected_count == total:
                            msg = f"所有设备已连接 ({connected_count}/{total})"
                            self.connection_panel.on_scan_complete(True, msg)
                        elif connected_count > 0:
                            msg = f"部分设备已连接 ({connected_count}/{total})"
                            self.connection_panel.on_scan_complete(True, msg)
                        else:
                            msg = "设备连接失败，请检查后重新扫描"
                            self.connection_panel.on_scan_complete(False, msg)

                    self.root.after(0, report_status)

                threading.Thread(target=do_auto_connect, daemon=True).start()

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

                def do_reconnect():
                    """在后台线程执行连接，避免阻塞主线程 UI"""
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

                    def report_status():
                        if connected == total:
                            self.connection_panel.on_scan_complete(True, f"所有设备已连接 ({connected}/{total})")
                        elif connected > 0:
                            self.connection_panel.on_scan_complete(True, f"部分设备已连接 ({connected}/{total})")
                        else:
                            self.connection_panel.on_scan_complete(False, "设备连接失败")

                    self.root.after(0, report_status)

                threading.Thread(target=do_reconnect, daemon=True).start()

            self.root.after(0, reconnect)

        except Exception as e:
            logging.error(f"重新扫描失败: {e}")
            self.root.after(0, lambda: self.connection_panel.on_scan_complete(
                False, f"重新扫描失败: {str(e)}"
            ))

    def on_output_state_changed(self, is_on: bool):
        """输出状态变化回调（来自 ControlPanel）"""
        self._sync_trigger_button()
        # 输出 OFF 时同步禁用自动采集
        if not is_on:
            self.control_panel.disable_auto_collect()
        else:
            # 输出 ON 时，如果全部设备已连接才启用
            all_connected = (
                self.device_controller.it8811_connected and
                self.device_controller.dmm6500_connected and
                self.device_controller.keysight_34461a_connected
            )
            if all_connected:
                self.control_panel.enable_auto_collect()

    def _sync_trigger_button(self):
        """手动触发按钮状态：全部设备已连接 + 输出 ON 才可点击"""
        all_connected = (
            self.device_controller.it8811_connected and
            self.device_controller.dmm6500_connected and
            self.device_controller.keysight_34461a_connected
        )
        output_on = self.control_panel.output_state == "ON"
        if all_connected and output_on:
            self.trigger_button.config(state=tk.NORMAL)
        else:
            self.trigger_button.config(state=tk.DISABLED)

    def on_device_status_change(self, device_type, connected):
        """设备连接状态变化"""
        # IT8811 连接状态影响控制面板
        if device_type == 'it8811':
            if connected:
                self.control_panel.enable_controls()
            else:
                self.control_panel.disable_controls()

        # 手动触发按钮同时受连接状态和输出状态影响
        self._sync_trigger_button()

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
        self.control_panel.disable_auto_collect()
        
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
                self.root.after(0, lambda: self.control_panel.enable_auto_collect())
        
        # 使用持久化的线程池或单独线程（这里暂时保持单独线程，因为 threading.Thread 开销相对 VISA I/O 较小）
        # 如果频繁触发，建议在 MainWindow __init__ 中 self.executor = ThreadPoolExecutor(max_workers=1)
        threading.Thread(target=task, daemon=True).start()

    def stop_auto_collect(self):
        """请求停止自动采集"""
        self._stop_collecting = True
        logging.info("用户请求停止自动采集")

    def auto_collect(self):
        """自动采集：从当前电阻开始，每次减50Ω，间隔1s，测量V×I，差值>20时记录"""
        if self.is_collecting:
            return
        self.is_collecting = True
        self._stop_collecting = False

        # 检查设备是否全部连接
        if not (self.device_controller.it8811_connected and
                self.device_controller.dmm6500_connected and
                self.device_controller.keysight_34461a_connected):
            messagebox.showerror("错误", "请先连接所有设备")
            self.is_collecting = False
            return

        # 禁用触发按钮，切换自动采集按钮为停止状态
        self.trigger_button.config(state=tk.DISABLED)
        self.control_panel.disable_controls()
        self.control_panel.set_collecting_state(True)
        self.control_panel.enable_auto_collect()  # 确保停止按钮可点击

        def task():
            try:
                # 读取当前电阻值作为起点
                try:
                    current_res = float(self.control_panel.value_entry.get())
                except (ValueError, AttributeError):
                    current_res = 7500.0

                # 如果当前值已经小于100，报错返回
                if current_res < 100:
                    self.root.after(0, lambda: messagebox.showwarning("提示", "当前电阻已低于 100Ω，无法自动采集"))
                    return

                # 向下取整到最近的50的倍数，确保从完整档位开始
                current_res = int(current_res // 50 * 50)
                if current_res < 100:
                    current_res = 100

                prev_power = None
                all_connected = True

                while current_res >= 100 and all_connected:
                    # 检查是否被用户手动停止
                    if self._stop_collecting:
                        self.root.after(0, lambda: logging.info("自动采集已被用户手动停止"))
                        break

                    # 设置电阻
                    success, msg = self.device_controller.set_resistance(str(int(current_res)))
                    if not success:
                        self.root.after(0, lambda m=msg: logging.error(f"设置电阻失败: {m}"))
                        break

                    # 更新 UI 显示当前电阻值
                    self.root.after(0, lambda r=current_res: self.control_panel.update_value_display(r))

                    # 等待 1 秒（每0.2s检查一次停止标志，提升响应速度）
                    for _ in range(5):
                        if self._stop_collecting:
                            break
                        time.sleep(0.2)
                    if self._stop_collecting:
                        self.root.after(0, lambda: logging.info("自动采集已被用户手动停止"))
                        break

                    # 测量数据
                    measurements = self.device_controller.get_all_measurements(
                        default_resistance=str(int(current_res))
                    )

                    volt_success, voltage_str = measurements['voltage']
                    curr_success, current_str = measurements['current']

                    if not volt_success:
                        logging.error(f"获取电压失败: {voltage_str}")
                        # 这里可能设备已断开，检查一下
                        if not self.device_controller.dmm6500_connected:
                            all_connected = False
                            self.root.after(0, lambda: messagebox.showerror("错误", "DMM6500 连接已断开，自动采集终止"))
                            break
                        # 单次电压读取失败但设备还在，继续下一步
                        current_res -= 50
                        continue

                    # 解析数值用于计算功率
                    try:
                        voltage_val = float(voltage_str)
                    except (ValueError, TypeError):
                        current_res -= 50
                        continue

                    try:
                        current_val = float(current_str) if curr_success else 0.0
                    except (ValueError, TypeError):
                        current_val = 0.0

                    # 计算功率 P = V × I (W)
                    power = voltage_val * current_val

                    # 格式化显示值
                    if curr_success:
                        try:
                            display_current = f"{float(current_str) * 1e6:.6f}"
                        except:
                            display_current = ""
                    else:
                        display_current = ""

                    try:
                        display_voltage = f"{voltage_val:.4f}"
                    except:
                        display_voltage = str(voltage_str)

                    # 判断是否记录（与上一次的差值 > 20）
                    should_record = False
                    if prev_power is not None:
                        power_diff = abs(power - prev_power)
                        if power_diff > 20:
                            should_record = True

                    if should_record:
                        res_str = str(int(current_res))
                        success, count = self.data_manager.record_data(
                            res_str, display_voltage, display_current
                        )
                        if success:
                            self.root.after(0, lambda c=count, r=res_str, v=display_voltage, i=display_current:
                                self.data_panel.add_data_column(c, r, v, i))
                            logging.info(f"自动采集记录: R={int(current_res)}, V={display_voltage}, I={display_current}, P={power:.4f}")
                        else:
                            logging.error(f"自动采集记录失败: {count}")
                    else:
                        logging.info(f"自动采集跳过: R={int(current_res)}, P={power:.4f}, ΔP={power - prev_power if prev_power else 0:.4f}")

                    # 更新前一次功率值
                    prev_power = power

                    # 减少 50Ω
                    current_res -= 50

                # 循环结束
                if current_res < 100 or not all_connected:
                    self.root.after(0, lambda: logging.info("自动采集已完成"))

            except Exception as e:
                logging.error(f"自动采集异常: {e}")
                self.root.after(0, lambda: messagebox.showerror("错误", f"自动采集异常: {str(e)}"))
            finally:
                self.is_collecting = False
                self._stop_collecting = False
                self.root.after(0, lambda: self.trigger_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.control_panel.set_collecting_state(False))
                self.root.after(0, lambda: self.control_panel.enable_controls())

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
