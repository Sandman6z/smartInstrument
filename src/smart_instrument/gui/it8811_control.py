import tkinter as tk
from tkinter import messagebox
import threading

class IT8811Control:
    """IT8811控制相关的方法"""
    def __init__(self, app):
        self.app = app
        # 添加节流控制变量
        self.last_wheel_time = 0
        self.wheel_cooldown = 500  # 500毫秒节流
    
    def set_resistance(self):
        """设置IT8811的电阻值（非阻塞式）"""
        try:
            resistance = self.app.resistance_entry.get()
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
                    success, msg = self.app.device_controller.set_resistance(resistance)
                    if success:
                        # 在主线程中更新UI
                        self.app.root.after(0, lambda: self.app.log(msg))
                    else:
                        # 在主线程中更新UI
                        self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                        self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
                except Exception as e:
                    error_msg = f"设置电阻值失败: {str(e)}"
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
            
            # 启动后台线程
            thread = threading.Thread(target=set_resistance_thread)
            thread.daemon = True
            thread.start()
        except Exception as e:
            error_msg = f"设置电阻值失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            self.app.log(error_msg, level="ERROR")
    
    def update_resistance(self, value):
        """更新电阻值"""
        # 同步滑动条值到输入框
        resistance = int(float(value))
        self.app.resistance_entry.delete(0, tk.END)
        self.app.resistance_entry.insert(0, str(resistance))
    
    def on_resistance_release(self, event):
        """滑动条释放时设置电阻值"""
        # 获取当前滑动条值
        resistance = int(self.app.resistance_var.get())
        # 更新输入框
        self.app.resistance_entry.delete(0, tk.END)
        self.app.resistance_entry.insert(0, str(resistance))
        # 调用设置电阻方法
        self.set_resistance()
    
    def on_mouse_wheel(self, event):
        """鼠标滚轮调节电阻值"""
        import time
        # 获取当前时间
        current_time = time.time() * 1000  # 转换为毫秒
        
        # 检查是否在冷却期内
        if current_time - self.last_wheel_time < self.wheel_cooldown:
            # 只更新UI，不发送命令
            # 获取当前值
            current_value = self.app.resistance_var.get()
            # 计算新值（每次滚动调整10Ω）
            if event.delta > 0:  # 向上滚动
                new_value = min(current_value + 10, 7500)
            else:  # 向下滚动
                new_value = max(current_value - 10, 10)
            # 更新滑动条值
            self.app.resistance_var.set(new_value)
            # 更新输入框
            resistance = int(new_value)
            self.app.resistance_entry.delete(0, tk.END)
            self.app.resistance_entry.insert(0, str(resistance))
            return
        
        # 冷却期已过，更新时间戳
        self.last_wheel_time = current_time
        
        # 获取当前值
        current_value = self.app.resistance_var.get()
        # 计算新值（每次滚动调整10Ω）
        if event.delta > 0:  # 向上滚动
            new_value = min(current_value + 10, 7500)
        else:  # 向下滚动
            new_value = max(current_value - 10, 10)
        # 更新滑动条值
        self.app.resistance_var.set(new_value)
        # 更新输入框
        resistance = int(new_value)
        self.app.resistance_entry.delete(0, tk.END)
        self.app.resistance_entry.insert(0, str(resistance))
        # 即刻生效，设置电阻值
        self.set_resistance()
    
    def toggle_output(self):
        """控制IT8811的输出开关（非阻塞式）"""
        # 获取当前状态并切换
        new_state = "ON" if self.app.output_state == "OFF" else "OFF"
        
        # 临时更新按钮状态，稍后根据实际结果再调整
        self.app.output_var.set(new_state == "ON")
        
        # 创建后台线程执行输出控制操作
        def toggle_thread():
            try:
                # 使用device_controller控制输出
                success, msg = self.app.device_controller.toggle_output(new_state)
                if success:
                    # 更新实际状态
                    self.app.output_state = new_state
                    # 在主线程中更新UI
                    self.app.root.after(0, lambda: self.app.log(msg))
                else:
                    # 恢复按钮状态
                    self.app.root.after(0, lambda: self.app.output_var.set(self.app.output_state == "ON"))
                    self.app.root.after(0, lambda: messagebox.showerror("错误", msg))
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                # 恢复按钮状态
                self.app.root.after(0, lambda: self.app.output_var.set(self.app.output_state == "ON"))
                error_msg = f"控制输出失败: {str(e)}"
                self.app.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=toggle_thread)
        thread.daemon = True
        thread.start()