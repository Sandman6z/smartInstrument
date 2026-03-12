import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging

class ControlPanel(ttk.LabelFrame):
    def __init__(self, master, controller):
        super().__init__(master, text="IT8811控制", padding="10")
        self.controller = controller
        self.output_state = "OFF"
        
        self.create_widgets()
        self.disable_controls()
        
    def create_widgets(self):
        # 电阻值调整
        resistance_frame = ttk.Frame(self)
        resistance_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(resistance_frame, text="电阻值 (Ω):", width=15).pack(side=tk.LEFT, padx=5)
        self.resistance_entry = ttk.Entry(resistance_frame, width=15)
        self.resistance_entry.pack(side=tk.LEFT, padx=5)
        self.resistance_entry.insert(0, "7500")
        
        # 绑定事件
        self.resistance_entry.bind("<KeyRelease>", self.on_resistance_entry_change)
        self.resistance_entry.bind("<Return>", lambda e: self.set_resistance())
        
        # 滑动条
        self.resistance_var = tk.DoubleVar(value=7500)
        self.resistance_scale = ttk.Scale(
            resistance_frame, 
            from_=10, 
            to=7500, 
            orient=tk.HORIZONTAL, 
            length=200,
            variable=self.resistance_var,
            command=self.update_resistance_entry
        )
        self.resistance_scale.pack(side=tk.LEFT, padx=10)
        self.resistance_scale.bind("<ButtonRelease-1>", lambda e: self.set_resistance())
        self.resistance_scale.bind("<MouseWheel>", self.on_mouse_wheel)
        
        ttk.Button(resistance_frame, text="设置电阻", command=self.set_resistance).pack(side=tk.LEFT, padx=5)
        
        # 开关控制
        switch_frame = ttk.Frame(self)
        switch_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(switch_frame, text="输出状态:", width=15).pack(side=tk.LEFT, padx=5)
        
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
        
    def enable_controls(self):
        self.resistance_entry.config(state=tk.NORMAL)
        self.resistance_scale.config(state=tk.NORMAL)
        self.output_switch.config(state=tk.NORMAL)

    def disable_controls(self):
        self.resistance_entry.config(state=tk.DISABLED)
        self.resistance_scale.config(state=tk.DISABLED)
        self.output_switch.config(state=tk.DISABLED)

    def on_resistance_entry_change(self, event):
        try:
            resistance = float(self.resistance_entry.get())
            if 10 <= resistance <= 7500:
                self.resistance_var.set(resistance)
        except ValueError:
            pass

    def update_resistance_entry(self, value):
        resistance = int(float(value))
        self.resistance_entry.delete(0, tk.END)
        self.resistance_entry.insert(0, str(resistance))

    def on_mouse_wheel(self, event):
        if str(self.resistance_scale['state']) == 'disabled':
            return
        current_value = self.resistance_var.get()
        if event.delta > 0:
            new_value = min(current_value + 10, 7500)
        else:
            new_value = max(current_value - 10, 10)
        self.resistance_var.set(new_value)
        self.update_resistance_entry(new_value)
        self.set_resistance()

    def set_resistance(self):
        try:
            resistance = self.resistance_entry.get()
            # 验证
            try:
                val = float(resistance)
                if not (10 <= val <= 7500):
                    messagebox.showerror("错误", "电阻值必须在 10-7500 之间")
                    return
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
                return

            def task():
                try:
                    success, msg = self.controller.set_resistance(resistance)
                    self.after(0, lambda: logging.info(msg) if success else messagebox.showerror("错误", msg))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("错误", str(e)))
            
            threading.Thread(target=task, daemon=True).start()
        except Exception as e:
            logging.error(f"Set resistance error: {e}")

    def toggle_output(self):
        new_state = "ON" if self.output_state == "OFF" else "OFF"
        # 乐观更新
        self.output_var.set(new_state == "ON")
        
        def task():
            try:
                success, msg = self.controller.toggle_output(new_state)
                self.after(0, lambda: self._on_toggle_result(success, msg, new_state))
            except Exception as e:
                self.after(0, lambda: self._on_toggle_result(False, str(e), new_state))
        
        threading.Thread(target=task, daemon=True).start()

    def _on_toggle_result(self, success, msg, target_state):
        if success:
            self.output_state = target_state
            logging.info(msg)
        else:
            # 回滚
            self.output_var.set(self.output_state == "ON")
            messagebox.showerror("错误", msg)
            logging.error(msg)
