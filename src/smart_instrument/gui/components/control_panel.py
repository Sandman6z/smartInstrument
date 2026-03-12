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
        # 模式选择
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="工作模式:", width=15).pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value="CC")
        self.mode_combo = ttk.Combobox(
            mode_frame, 
            textvariable=self.mode_var, 
            values=["CC", "CV", "CR"], 
            state="readonly", 
            width=12
        )
        self.mode_combo.pack(side=tk.LEFT, padx=5)
        self.mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)

        # 数值调整
        value_frame = ttk.Frame(self)
        value_frame.pack(fill=tk.X, pady=5)
        
        self.value_label = ttk.Label(value_frame, text="电流 (A):", width=15)
        self.value_label.pack(side=tk.LEFT, padx=5)
        
        self.value_entry = ttk.Entry(value_frame, width=15)
        self.value_entry.pack(side=tk.LEFT, padx=5)
        self.value_entry.insert(0, "0.000")
        
        self.value_entry.bind("<KeyRelease>", self.on_entry_change)
        self.value_entry.bind("<Return>", lambda e: self.set_value())
        
        # 滑动条
        self.value_var = tk.DoubleVar(value=0.0)
        self.value_scale = ttk.Scale(
            value_frame, 
            from_=0, 
            to=30, 
            orient=tk.HORIZONTAL, 
            length=200,
            variable=self.value_var,
            command=self.update_entry_from_scale
        )
        self.value_scale.pack(side=tk.LEFT, padx=10)
        self.value_scale.bind("<ButtonRelease-1>", lambda e: self.set_value())
        
        ttk.Button(value_frame, text="设置参数", command=self.set_value).pack(side=tk.LEFT, padx=5)
        
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
        self.mode_combo.config(state="readonly")
        self.value_entry.config(state=tk.NORMAL)
        self.value_scale.config(state=tk.NORMAL)
        self.output_switch.config(state=tk.NORMAL)

    def disable_controls(self):
        self.mode_combo.config(state=tk.DISABLED)
        self.value_entry.config(state=tk.DISABLED)
        self.value_scale.config(state=tk.DISABLED)
        self.output_switch.config(state=tk.DISABLED)

    def on_mode_change(self, event):
        new_mode = self.mode_var.get()
        
        # 更新界面限制
        self.update_ui_for_mode(new_mode)
        
        # 发送命令
        def task():
            try:
                success, msg = self.controller.set_load_mode(new_mode)
                if success:
                    self.current_mode = new_mode
                    self.after(0, lambda: logging.info(msg))
                else:
                    self.after(0, lambda: messagebox.showerror("错误", msg))
                    # 回滚模式选择
                    self.after(0, lambda: self.mode_var.set(self.current_mode))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", str(e)))
        
        threading.Thread(target=task, daemon=True).start()

    def update_ui_for_mode(self, mode):
        if mode == "CC":
            self.value_label.config(text="电流 (A):")
            self.value_scale.config(from_=0, to=30)
            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, "0.000")
        elif mode == "CV":
            self.value_label.config(text="电压 (V):")
            self.value_scale.config(from_=0.1, to=120)
            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, "0.000")
        elif mode == "CR":
            self.value_label.config(text="电阻 (Ω):")
            self.value_scale.config(from_=0.05, to=7500)
            self.value_entry.delete(0, tk.END)
            self.value_entry.insert(0, "7500")
            
        self.value_var.set(float(self.value_entry.get()))

    def on_entry_change(self, event):
        try:
            val = float(self.value_entry.get())
            # 简单的范围检查
            mode = self.mode_var.get()
            if mode == "CC" and 0 <= val <= 30:
                self.value_var.set(val)
            elif mode == "CV" and 0 <= val <= 120:
                self.value_var.set(val)
            elif mode == "CR" and 0 <= val <= 7500:
                self.value_var.set(val)
        except ValueError:
            pass

    def update_entry_from_scale(self, value):
        val = float(value)
        self.value_entry.delete(0, tk.END)
        if self.mode_var.get() == "CR":
             self.value_entry.insert(0, f"{int(val)}")
        else:
             self.value_entry.insert(0, f"{val:.3f}")

    def set_value(self):
        try:
            val_str = self.value_entry.get()
            val = float(val_str)
            mode = self.mode_var.get()
            
            # 验证
            if mode == "CC" and not (0 <= val <= 30):
                messagebox.showerror("错误", "电流值必须在 0-30A 之间")
                return
            elif mode == "CV" and not (0 <= val <= 120):
                messagebox.showerror("错误", "电压值必须在 0-120V 之间")
                return
            elif mode == "CR" and not (0 <= val <= 7500):
                messagebox.showerror("错误", "电阻值必须在 0-7500Ω 之间")
                return

            def task():
                try:
                    success, msg = self.controller.set_load_value(mode, val_str)
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
