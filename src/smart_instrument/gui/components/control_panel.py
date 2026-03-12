import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

class ControlPanel(ttk.LabelFrame):
    def __init__(self, master, controller):
        super().__init__(master, text="IT8811控制", padding="10")
        self.controller = controller
        self.output_state = "OFF"
        self.current_mode = "CC" # 默认为 CC
        
        self.create_widgets()
        self.disable_controls()
        
    def create_widgets(self):
        # 数值调整 (默认电阻模式)
        value_frame = ttk.Frame(self)
        value_frame.pack(fill=tk.X, pady=5)
        
        self.value_label = ttk.Label(value_frame, text="电阻 (Ω):", width=15)
        self.value_label.pack(side=tk.LEFT, padx=5)
        
        self.value_entry = ttk.Entry(value_frame, width=15)
        self.value_entry.pack(side=tk.LEFT, padx=5)
        self.value_entry.insert(0, "7500")
        
        self.value_entry.bind("<KeyRelease>", self.on_entry_change)
        self.value_entry.bind("<Return>", lambda e: self.set_value())
        
        # 滑动条
        self.value_var = tk.DoubleVar(value=7500.0)
        self.value_scale = ttk.Scale(
            value_frame, 
            from_=0, 
            to=7500, 
            orient=tk.HORIZONTAL, 
            length=200,
            variable=self.value_var,
            command=self.update_entry_from_scale
        )
        self.value_scale.pack(side=tk.LEFT, padx=10)
        
        # 绑定事件：释放鼠标时发送指令
        self.value_scale.bind("<ButtonRelease-1>", lambda e: self.set_value())
        # 绑定滚轮：滚动时调整数值（但不立即发送指令，避免频繁通信）
        self.value_scale.bind("<MouseWheel>", self.on_mouse_wheel)
        
        ttk.Button(value_frame, text="设置电阻", command=self.set_value).pack(side=tk.LEFT, padx=5)
        
        # 开关控制
        switch_frame = ttk.Frame(self)
        switch_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(switch_frame, text="输入状态:", width=15).pack(side=tk.LEFT, padx=5)
        
        self.output_var = tk.BooleanVar(value=False)
        self.output_switch = ttk.Checkbutton(
            switch_frame, 
            text="OFF",
            width=10,
            variable=self.output_var,
            command=self.toggle_output,
            style="Switch.TCheckbutton"
        )
        self.output_switch.pack(side=tk.LEFT, padx=5)
        
    def enable_controls(self):
        self.value_entry.config(state=tk.NORMAL)
        self.value_scale.config(state=tk.NORMAL)
        self.output_switch.config(state=tk.NORMAL)
        
        # 切换到 CR 模式
        def init_mode():
            try:
                self.controller.set_load_mode("CR")
            except:
                pass
        threading.Thread(target=init_mode, daemon=True).start()

    def disable_controls(self):
        self.value_entry.config(state=tk.DISABLED)
        self.value_scale.config(state=tk.DISABLED)
        self.output_switch.config(state=tk.DISABLED)

    def on_mouse_wheel(self, event):
        if str(self.value_scale['state']) == 'disabled':
            return
            
        # 计算新的值，根据滚轮方向
        current = self.value_var.get()
        # event.delta 在 Windows 上通常是 120 的倍数
        # 基础步长改为 50
        step = 50 if event.delta > 0 else -50
        
        new_val = current + step
        new_val = max(0, min(7500, new_val))
        
        self.value_var.set(new_val)
        self.update_entry_from_scale(new_val)
        
        # 防抖发送指令 (100ms)
        if hasattr(self, '_debounce_timer') and self._debounce_timer:
            self.after_cancel(self._debounce_timer)
        self._debounce_timer = self.after(100, self.set_value)

    def on_entry_change(self, event):
        try:
            val = float(self.value_entry.get())
            if 0 <= val <= 7500:
                self.value_var.set(val)
        except ValueError:
            pass

    def update_entry_from_scale(self, value):
        val = float(value)
        self.value_entry.delete(0, tk.END)
        # 假设电阻显示整数即可
        self.value_entry.insert(0, f"{int(val)}")

    def set_value(self):
        try:
            val_str = self.value_entry.get()
            val = float(val_str)
            
            if not (0 <= val <= 7500):
                messagebox.showerror("错误", "电阻值必须在 0-7500Ω 之间")
                return

            def task():
                try:
                     # 直接设置电阻，不再每次都设置模式
                     success, msg = self.controller.set_resistance(val_str)
                     
                     self.after(0, lambda: logging.info(msg) if success else messagebox.showerror("错误", msg))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("错误", str(e)))
            
            threading.Thread(target=task, daemon=True).start()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    def toggle_output(self):
        # 注意：此时 output_var 已经被 Checkbutton 点击事件改变了
        # 如果之前是 False(OFF)，点击后变成 True(ON)，我们希望执行 ON 操作
        target_state = "ON" if self.output_var.get() else "OFF"
        
        # 更新按钮文本
        self.output_switch.config(text=target_state)
        
        def task():
            try:
                success, msg = self.controller.toggle_output(target_state)
                self.after(0, lambda: self._on_toggle_result(success, msg, target_state))
            except Exception as e:
                self.after(0, lambda: self._on_toggle_result(False, str(e), target_state))
        
        threading.Thread(target=task, daemon=True).start()

    def _on_toggle_result(self, success, msg, target_state):
        if success:
            self.output_state = target_state
            logging.info(msg)
            # 确保 UI 状态一致
            self.output_switch.config(text=target_state)
            self.output_var.set(target_state == "ON")
        else:
            # 回滚
            logging.error(msg)
            messagebox.showerror("错误", msg)
            revert_state = "OFF" if target_state == "ON" else "ON"
            self.output_state = revert_state
            self.output_switch.config(text=revert_state)
            self.output_var.set(revert_state == "ON")
