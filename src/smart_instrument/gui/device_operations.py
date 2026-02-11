import tkinter as tk
from tkinter import messagebox
import threading
from datetime import datetime

class DeviceOperations:
    """设备操作相关的方法"""
    def __init__(self, app):
        self.app = app
    
    def scan_devices(self):
        """扫描可用的VISA设备（非阻塞式）"""
        # 创建后台线程执行设备扫描
        def scan_thread():
            try:
                # 使用device_controller扫描设备
                device_list, device_info, it8811_device, dmm6500_device, keysight_34461a_device = self.app.device_controller.scan_devices()
                
                # 在主线程中更新UI
                def update_ui():
                    # 保存设备信息
                    self.app.device_info = device_info
                    
                    # 如果没有找到设备，显示提示
                    if not device_list:
                        messagebox.showinfo("提示", "未找到任何VISA设备")
                        self.app.log("未找到任何VISA设备")
                        # 更新设备状态为未连接
                        if hasattr(self.app, 'it8811_status'):
                            self.app.it8811_status.config(text="未连接", foreground="red")
                        if hasattr(self.app, 'dmm6500_status'):
                            self.app.dmm6500_status.config(text="未连接", foreground="red")
                        if hasattr(self.app, 'keysight_status'):
                            self.app.keysight_status.config(text="未连接", foreground="red")
                    else:
                        msg = f"找到设备数量: {len(device_list)}"
                        print(msg)
                        self.app.log(msg)
                        msg = f"设备列表: {device_list}"
                        print(msg)
                        self.app.log(msg)
                    
                    # 设置设备列表
                    self.app.it8811_resource['values'] = device_list
                    self.app.dmm6500_resource['values'] = device_list
                    self.app.keysight_resource['values'] = device_list
                    
                    # 自动选择设备
                    if it8811_device:
                        self.app.it8811_resource.set(it8811_device)
                        msg = f"自动选择IT8811设备: {it8811_device}"
                        print(msg)
                        self.app.log(msg)
                    if dmm6500_device:
                        self.app.dmm6500_resource.set(dmm6500_device)
                        msg = f"自动选择DMM6500设备: {dmm6500_device}"
                        print(msg)
                        self.app.log(msg)
                    if keysight_34461a_device:
                        self.app.keysight_resource.set(keysight_34461a_device)
                        msg = f"自动选择KEYSIGHT 34461A设备: {keysight_34461a_device}"
                        print(msg)
                        self.app.log(msg)
                        
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
                        self.app.log(msg)
                    else:
                        # 启用设备操作按钮
                        if hasattr(self.app, 'it8811_button'):
                            self.app.it8811_button.config(state="normal")
                            self.app.it8811_status.config(text="未连接", foreground="red")
                        if hasattr(self.app, 'dmm6500_button'):
                            self.app.dmm6500_button.config(state="normal")
                            self.app.dmm6500_status.config(text="未连接", foreground="red")
                        if hasattr(self.app, 'keysight_button'):
                            self.app.keysight_button.config(state="normal")
                            self.app.keysight_status.config(text="未连接", foreground="red")
                    
                    # 显示扫描完成提示
                    self.app.log("设备扫描完成")
                
                # 在主线程中更新UI
                self.app.root.after(0, update_ui)
            except Exception as e:
                error_msg = f"扫描设备失败: {str(e)}"
                print(error_msg)
                self.app.log(error_msg, level="ERROR")
                # 在主线程中显示错误信息
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
        
        # 启动后台线程
        thread = threading.Thread(target=scan_thread)
        thread.daemon = True
        thread.start()
    
    def connect_it8811(self):
        """连接IT8811（非阻塞式）"""
        selected_text = self.app.it8811_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择IT8811资源")
            return
        
        # 获取实际的设备地址
        resource = self.app.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.app.it8811_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.app.device_controller.connect_it8811(resource)
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.it8811_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: self.app.it8811_button.config(text="断开", command=self.disconnect_it8811))
                    self.app.root.after(0, lambda: self.app.log(msg))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.it8811_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接IT8811失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.it8811_status.config(text="未连接", foreground="red"))
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def disconnect_it8811(self):
        """断开IT8811连接（非阻塞式）"""
        # 显示断开中状态
        self.app.it8811_status.config(text="断开中...", foreground="orange")
        
        # 创建后台线程执行断开操作
        def disconnect_thread():
            try:
                # 使用device_controller断开连接
                success, msg = self.app.device_controller.disconnect_it8811()
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.it8811_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: self.app.it8811_button.config(text="连接", command=self.connect_it8811))
                    self.app.root.after(0, lambda: self.app.log(msg))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.it8811_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"断开IT8811连接失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.it8811_status.config(text="已连接", foreground="green"))
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=disconnect_thread)
        thread.daemon = True
        thread.start()
    
    def auto_connect_it8811(self):
        """自动连接IT8811"""
        selected_text = self.app.it8811_resource.get()
        if not selected_text:
            return
        
        # 获取实际的设备地址
        resource = self.app.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.app.it8811_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.app.device_controller.connect_it8811(resource)
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.it8811_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: self.app.it8811_button.config(text="断开", command=self.disconnect_it8811, state="normal"))
                    self.app.root.after(0, lambda: self.app.log(msg))
                    # 启用其他设备按钮
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(state="normal"))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.it8811_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: self.app.it8811_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
                    # 启用其他设备按钮
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(state="normal"))
            except Exception as e:
                error_msg = f"连接IT8811失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.it8811_status.config(text="未连接", foreground="red"))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def auto_connect_dmm6500(self):
        """自动连接DMM6500"""
        selected_text = self.app.dmm6500_resource.get()
        if not selected_text:
            return
        
        # 获取实际的设备地址
        resource = self.app.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.app.dmm6500_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.app.device_controller.connect_dmm6500(resource)
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(text="断开", command=self.disconnect_dmm6500, state="normal"))
                    self.app.root.after(0, lambda: self.app.log(msg))
                    # 启用其他设备按钮
                    self.app.root.after(0, lambda: self.app.it8811_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(state="normal"))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
                    # 启用其他设备按钮
                    self.app.root.after(0, lambda: self.app.it8811_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(state="normal"))
            except Exception as e:
                error_msg = f"连接DMM6500失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="未连接", foreground="red"))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def auto_connect_keysight_34461a(self):
        """自动连接KEYSIGHT 34461A"""
        selected_text = self.app.keysight_resource.get()
        if not selected_text:
            return
        
        # 获取实际的设备地址
        resource = self.app.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.app.keysight_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.app.device_controller.connect_keysight_34461a(resource)
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.keysight_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(text="断开", command=self.disconnect_keysight_34461a, state="normal"))
                    self.app.root.after(0, lambda: self.app.log(msg))
                    # 启用其他设备按钮
                    self.app.root.after(0, lambda: self.app.it8811_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(state="normal"))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.keysight_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
                    # 启用其他设备按钮
                    self.app.root.after(0, lambda: self.app.it8811_button.config(state="normal"))
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(state="normal"))
            except Exception as e:
                error_msg = f"连接KEYSIGHT 34461A失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.keysight_status.config(text="未连接", foreground="red"))
                self.app.root.after(0, lambda: self.app.keysight_button.config(state="normal"))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
                # 启用其他设备按钮
                self.app.root.after(0, lambda: self.app.it8811_button.config(state="normal"))
                self.app.root.after(0, lambda: self.app.dmm6500_button.config(state="normal"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def connect_dmm6500(self):
        """连接DMM6500（非阻塞式）"""
        selected_text = self.app.dmm6500_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择DMM6500资源")
            return
        
        # 获取实际的设备地址
        resource = self.app.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.app.dmm6500_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.app.device_controller.connect_dmm6500(resource)
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(text="断开", command=self.disconnect_dmm6500))
                    self.app.root.after(0, lambda: self.app.log(msg))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接DMM6500失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="未连接", foreground="red"))
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def connect_keysight_34461a(self):
        """连接KEYSIGHT 34461A（非阻塞式）"""
        selected_text = self.app.keysight_resource.get()
        if not selected_text:
            messagebox.showwarning("警告", "请选择KEYSIGHT资源")
            return
        
        # 获取实际的设备地址
        resource = self.app.device_info.get(selected_text, selected_text)
        
        # 显示连接中状态
        self.app.keysight_status.config(text="连接中...", foreground="orange")
        
        # 创建后台线程执行连接操作
        def connect_thread():
            try:
                # 使用device_controller连接设备
                success, msg = self.app.device_controller.connect_keysight_34461a(resource)
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.keysight_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(text="断开", command=self.disconnect_keysight_34461a))
                    self.app.root.after(0, lambda: self.app.log(msg))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.keysight_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"连接KEYSIGHT 34461A失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.keysight_status.config(text="未连接", foreground="red"))
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=connect_thread)
        thread.daemon = True
        thread.start()
    
    def disconnect_dmm6500(self):
        """断开DMM6500连接（非阻塞式）"""
        # 显示断开中状态
        self.app.dmm6500_status.config(text="断开中...", foreground="orange")
        
        # 创建后台线程执行断开操作
        def disconnect_thread():
            try:
                # 使用device_controller断开连接
                success, msg = self.app.device_controller.disconnect_dmm6500()
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: self.app.dmm6500_button.config(text="连接", command=self.connect_dmm6500))
                    self.app.root.after(0, lambda: self.app.log(msg))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"断开DMM6500连接失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.dmm6500_status.config(text="已连接", foreground="green"))
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=disconnect_thread)
        thread.daemon = True
        thread.start()
    
    def disconnect_keysight_34461a(self):
        """断开KEYSIGHT 34461A连接（非阻塞式）"""
        # 显示断开中状态
        self.app.keysight_status.config(text="断开中...", foreground="orange")
        
        # 创建后台线程执行断开操作
        def disconnect_thread():
            try:
                # 使用device_controller断开连接
                success, msg = self.app.device_controller.disconnect_keysight_34461a()
                if success:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.keysight_status.config(text="未连接", foreground="red"))
                    self.app.root.after(0, lambda: self.app.keysight_button.config(text="连接", command=self.connect_keysight_34461a))
                    self.app.root.after(0, lambda: self.app.log(msg))
                else:
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.keysight_status.config(text="已连接", foreground="green"))
                    self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"断开KEYSIGHT 34461A连接失败: {str(e)}"
                # 在主线程中更新UI
                self.app.root.after(0, lambda: self.app.keysight_status.config(text="已连接", foreground="green"))
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=disconnect_thread)
        thread.daemon = True
        thread.start()
