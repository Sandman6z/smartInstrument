import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

class ConnectionPanel(ttk.LabelFrame):
    def __init__(self, master, controller, on_connect_status_change=None):
        super().__init__(master, text="设备连接", padding="10")
        self.controller = controller
        self.on_connect_status_change = on_connect_status_change
        
        self.device_info = {}
        
        # 连接锁状态
        self.connecting_status = {
            'it8811': False,
            'dmm6500': False,
            'keysight': False
        }
        
        self.create_widgets()
    
    def _set_connecting(self, device_key, is_connecting):
        """设置连接中状态"""
        self.connecting_status[device_key] = is_connecting
        # 可以根据需要在界面上禁用按钮等

    def create_widgets(self):
        # IT8811
        self.it8811_frame = ttk.Frame(self)
        self.it8811_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.it8811_frame, text="IT8811资源:", width=15).pack(side=tk.LEFT, padx=5)
        self.it8811_resource = ttk.Combobox(self.it8811_frame, width=30)
        self.it8811_resource.pack(side=tk.LEFT, padx=5)
        self.it8811_button = ttk.Button(self.it8811_frame, text="连接", command=self.connect_it8811)
        self.it8811_button.pack(side=tk.LEFT, padx=5)
        self.it8811_status = ttk.Label(self.it8811_frame, text="未连接", foreground="red")
        self.it8811_status.pack(side=tk.LEFT, padx=5)

        # DMM6500
        self.dmm6500_frame = ttk.Frame(self)
        self.dmm6500_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.dmm6500_frame, text="DMM6500资源:", width=15).pack(side=tk.LEFT, padx=5)
        self.dmm6500_resource = ttk.Combobox(self.dmm6500_frame, width=30)
        self.dmm6500_resource.pack(side=tk.LEFT, padx=5)
        self.dmm6500_button = ttk.Button(self.dmm6500_frame, text="连接", command=self.connect_dmm6500)
        self.dmm6500_button.pack(side=tk.LEFT, padx=5)
        self.dmm6500_status = ttk.Label(self.dmm6500_frame, text="未连接", foreground="red")
        self.dmm6500_status.pack(side=tk.LEFT, padx=5)

        # KEYSIGHT 34461A
        self.keysight_frame = ttk.Frame(self)
        self.keysight_frame.pack(fill=tk.X, pady=5)
        ttk.Label(self.keysight_frame, text="KEYSIGHT资源:", width=15).pack(side=tk.LEFT, padx=5)
        self.keysight_resource = ttk.Combobox(self.keysight_frame, width=30)
        self.keysight_resource.pack(side=tk.LEFT, padx=5)
        self.keysight_button = ttk.Button(self.keysight_frame, text="连接", command=self.connect_keysight)
        self.keysight_button.pack(side=tk.LEFT, padx=5)
        self.keysight_status = ttk.Label(self.keysight_frame, text="未连接", foreground="red")
        self.keysight_status.pack(side=tk.LEFT, padx=5)

    def update_device_list(self, device_list, device_info, it8811_dev, dmm_dev, keysight_dev):
        self.device_info = device_info
        
        self.it8811_resource['values'] = device_list
        self.dmm6500_resource['values'] = device_list
        self.keysight_resource['values'] = device_list
        
        if it8811_dev: self.it8811_resource.set(it8811_dev)
        if dmm_dev: self.dmm6500_resource.set(dmm_dev)
        if keysight_dev: self.keysight_resource.set(keysight_dev)

    def connect_it8811(self):
        """连接IT8811（非阻塞式）"""
        if self.controller.it8811_connected:
             self.disconnect_it8811()
             return

        if self.connecting_status['it8811']:
            logging.info("IT8811 正在连接中，跳过重复请求")
            return
            
        selected_text = self.it8811_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择IT8811资源")
            return
        
        resource = self.device_info.get(selected_text, selected_text)
        
        self._set_connecting('it8811', True)
        self.it8811_status.config(text="连接中...", foreground="orange")
        self.it8811_button.config(state=tk.DISABLED)
        
        def task():
            try:
                success, msg = self.controller.connect_it8811(resource)
                self.after(0, lambda: self._on_it8811_connect_result(success, msg))
            except Exception as e:
                self.after(0, lambda: self._on_it8811_connect_result(False, str(e)))
        
        threading.Thread(target=task, daemon=True).start()

    def _on_it8811_connect_result(self, success, msg):
        self._set_connecting('it8811', False)
        self.it8811_button.config(state=tk.NORMAL)
        
        if success:
            self.it8811_status.config(text="已连接", foreground="green")
            self.it8811_button.config(text="断开")
            logging.info(msg)
        else:
            self.it8811_status.config(text="未连接", foreground="red")
            messagebox.showerror("错误", msg)
            logging.error(msg)
        
        if self.on_connect_status_change:
            self.on_connect_status_change('it8811', success)

    def disconnect_it8811(self):
        self.it8811_status.config(text="断开中...", foreground="orange")
        def task():
            try:
                success, msg = self.controller.disconnect_it8811()
                self.after(0, lambda: self._on_it8811_disconnect_result(success, msg))
            except Exception as e:
                self.after(0, lambda: self._on_it8811_disconnect_result(False, str(e)))
        threading.Thread(target=task, daemon=True).start()

    def _on_it8811_disconnect_result(self, success, msg):
        if success:
            self.it8811_status.config(text="未连接", foreground="red")
            self.it8811_button.config(text="连接")
            logging.info(msg)
        else:
            self.it8811_status.config(text="已连接", foreground="green")
            messagebox.showerror("错误", msg)
            logging.error(msg)
            
        if self.on_connect_status_change:
            self.on_connect_status_change('it8811', not success)

    def connect_dmm6500(self):
        if self.controller.dmm6500_connected:
             self.disconnect_dmm6500()
             return

        if self.connecting_status['dmm6500']:
            logging.info("DMM6500 正在连接中，跳过重复请求")
            return

        selected_text = self.dmm6500_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择DMM6500资源")
            return
        
        resource = self.device_info.get(selected_text, selected_text)
        
        self._set_connecting('dmm6500', True)
        self.dmm6500_status.config(text="连接中...", foreground="orange")
        self.dmm6500_button.config(state=tk.DISABLED)
        
        def task():
            try:
                success, msg = self.controller.connect_dmm6500(resource)
                self.after(0, lambda: self._on_dmm_connect_result(success, msg))
            except Exception as e:
                self.after(0, lambda: self._on_dmm_connect_result(False, str(e)))
        
        threading.Thread(target=task, daemon=True).start()

    def _on_dmm_connect_result(self, success, msg):
        self._set_connecting('dmm6500', False)
        self.dmm6500_button.config(state=tk.NORMAL)
        
        if success:
            self.dmm6500_status.config(text="已连接", foreground="green")
            self.dmm6500_button.config(text="断开")
            logging.info(msg)
        else:
            self.dmm6500_status.config(text="未连接", foreground="red")
            messagebox.showerror("错误", msg)
            logging.error(msg)
        
        if self.on_connect_status_change:
            self.on_connect_status_change('dmm6500', success)

    def disconnect_dmm6500(self):
        self.dmm6500_status.config(text="断开中...", foreground="orange")
        def task():
            try:
                success, msg = self.controller.disconnect_dmm6500()
                self.after(0, lambda: self._on_dmm_disconnect_result(success, msg))
            except Exception as e:
                self.after(0, lambda: self._on_dmm_disconnect_result(False, str(e)))
        threading.Thread(target=task, daemon=True).start()

    def _on_dmm_disconnect_result(self, success, msg):
        if success:
            self.dmm6500_status.config(text="未连接", foreground="red")
            self.dmm6500_button.config(text="连接")
            logging.info(msg)
        else:
            self.dmm6500_status.config(text="已连接", foreground="green")
            messagebox.showerror("错误", msg)
            logging.error(msg)
            
        if self.on_connect_status_change:
            self.on_connect_status_change('dmm6500', not success)

    def connect_keysight(self):
        if self.controller.keysight_34461a_connected:
             self.disconnect_keysight()
             return

        if self.connecting_status['keysight']:
            logging.info("KEYSIGHT 正在连接中，跳过重复请求")
            return

        selected_text = self.keysight_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择KEYSIGHT资源")
            return
        
        resource = self.device_info.get(selected_text, selected_text)
        
        self._set_connecting('keysight', True)
        self.keysight_status.config(text="连接中...", foreground="orange")
        self.keysight_button.config(state=tk.DISABLED)
        
        def task():
            try:
                success, msg = self.controller.connect_keysight_34461a(resource)
                self.after(0, lambda: self._on_keysight_connect_result(success, msg))
            except Exception as e:
                self.after(0, lambda: self._on_keysight_connect_result(False, str(e)))
        
        threading.Thread(target=task, daemon=True).start()

    def _on_keysight_connect_result(self, success, msg):
        self._set_connecting('keysight', False)
        self.keysight_button.config(state=tk.NORMAL)
        
        if success:
            self.keysight_status.config(text="已连接", foreground="green")
            self.keysight_button.config(text="断开")
            logging.info(msg)
        else:
            self.keysight_status.config(text="未连接", foreground="red")
            messagebox.showerror("错误", msg)
            logging.error(msg)
        
        if self.on_connect_status_change:
            self.on_connect_status_change('keysight', success)

    def disconnect_keysight(self):
        self.keysight_status.config(text="断开中...", foreground="orange")
        def task():
            try:
                success, msg = self.controller.disconnect_keysight_34461a()
                self.after(0, lambda: self._on_keysight_disconnect_result(success, msg))
            except Exception as e:
                self.after(0, lambda: self._on_keysight_disconnect_result(False, str(e)))
        threading.Thread(target=task, daemon=True).start()

    def _on_keysight_disconnect_result(self, success, msg):
        if success:
            self.keysight_status.config(text="未连接", foreground="red")
            self.keysight_button.config(text="连接")
            logging.info(msg)
        else:
            self.keysight_status.config(text="已连接", foreground="green")
            messagebox.showerror("错误", msg)
            logging.error(msg)
            
        if self.on_connect_status_change:
            self.on_connect_status_change('keysight', not success)
