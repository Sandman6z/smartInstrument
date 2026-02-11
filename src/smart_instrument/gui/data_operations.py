import tkinter as tk
from tkinter import messagebox
import threading

class DataOperations:
    """数据操作相关的方法"""
    def __init__(self, app):
        self.app = app
    
    def manual_trigger(self):
        """手动触发记录数据（非阻塞式）"""
        # 创建后台线程执行数据采集操作
        def trigger_thread():
            try:
                # 获取IT8811的电阻数据
                res_success, resistance = self.app.device_controller.get_resistance()
                if not res_success:
                    # 如果获取电阻值失败，使用输入框中的值
                    resistance = self.app.resistance_entry.get()
                    self.app.root.after(0, lambda: self.app.log(f"获取电阻值失败，使用输入框值: {resistance}Ω", level="WARNING"))
                
                # 获取DMM6500的电压数据
                volt_success, voltage = self.app.device_controller.get_voltage()
                if not volt_success:
                    # 如果获取电压值失败，使用默认值，并继续执行
                    voltage = "-"
                    self.app.root.after(0, lambda: self.app.log(f"获取电压值失败: {voltage}", level="WARNING"))
                else:
                    # 格式化电压值，保留小数点后四位，四舍五入，不使用科学计数法
                    try:
                        voltage_value = float(voltage)
                        formatted_voltage = f"{voltage_value:.4f}"
                        voltage = formatted_voltage
                    except ValueError:
                        # 如果电压值格式不正确，保持原样
                        pass
                
                # 获取KEYSIGHT 34461A的电流数据
                curr_success, current = self.app.device_controller.get_current()
                if not curr_success:
                    current = ""
                    self.app.root.after(0, lambda: self.app.log(f"获取电流值失败: {current}", level="WARNING"))
                else:
                    # 格式化电流值，从A转换为uA（乘以1,000,000），保持原有精度
                    try:
                        current_value = float(current)
                        # 从A转换为uA
                        current_value_uA = current_value * 1000000
                        # 保持原有精度，使用与原始值相同的小数位数
                        current_str = str(current)
                        if 'E' in current_str:
                            # 科学计数法，保持精度
                            formatted_current = f"{current_value_uA:.6f}"
                        else:
                            # 普通格式，保持精度
                            decimal_places = len(current_str.split('.')[1]) if '.' in current_str else 0
                            format_str = f"{{:.{decimal_places}f}}"
                            formatted_current = format_str.format(current_value_uA)
                        current = formatted_current
                    except ValueError:
                        # 如果电流值格式不正确，保持原样
                        pass
                
                # 记录数据
                success, msg = self.app.data_manager.record_data(resistance, voltage, current)
                if success:
                    # 更新表格
                    col_count = msg
                    col_name = f"col{col_count}"
                    
                    # 在主线程中更新UI
                    def update_tree():
                        # 更新表格
                        if col_name not in self.app.tree["columns"]:
                            self.app.tree["columns"] = self.app.tree["columns"] + (col_name,)
                            self.app.tree.column(col_name, width=150, minwidth=100, stretch=tk.YES)
                            self.app.tree.heading(col_name, text=f"触发{col_count}")
                        
                        # 插入数据
                        self.app.tree.set(self.app.tree.get_children()[0], col_name, resistance)
                        self.app.tree.set(self.app.tree.get_children()[1], col_name, voltage)
                        if len(self.app.tree.get_children()) > 2:
                            self.app.tree.set(self.app.tree.get_children()[2], col_name, current)
                        
                        log_message = f"数据采集成功: 电阻={resistance}Ω, 电压={voltage}V"
                        if current:
                            log_message += f", 电流={current}A"
                        self.app.log(log_message)
                    
                    self.app.root.after(0, update_tree)
                else:
                    self.app.root.after(0, lambda: self.app.log(msg, level="ERROR"))
            except Exception as e:
                error_msg = f"手动触发失败: {str(e)}"
                self.app.root.after(0, lambda: self.app.log(error_msg, level="ERROR"))
        
        # 启动后台线程
        thread = threading.Thread(target=trigger_thread)
        thread.daemon = True
        thread.start()
    
    def record_data(self):
        """记录数据"""
        try:
            # 获取IT8811的电阻数据
            try:
                self.app.it8811.write("MEAS:RES?")
                resistance = self.app.it8811.read().strip()
            except Exception as e:
                if "timeout" in str(e).lower():
                    messagebox.showerror("错误", "IT8811数据采集超时，请检查设备连接")
                    return
                else:
                    raise
            
            # 获取DMM6500的电压数据
            try:
                self.app.dmm6500.write("MEAS:VOLT:DC?")
                voltage = self.app.dmm6500.read().strip()
            except Exception as e:
                if "timeout" in str(e).lower():
                    messagebox.showerror("错误", "DMM6500数据采集超时，请检查设备连接")
                    return
                else:
                    raise
            
            # 更新列计数
            self.app.column_count += 1
            col_name = f"col{self.app.column_count}"
            
            # 更新表格
            if col_name not in self.app.tree["columns"]:
                self.app.tree["columns"] = self.app.tree["columns"] + (col_name,)
                self.app.tree.column(col_name, width=150, minwidth=100, stretch=tk.YES)
                self.app.tree.heading(col_name, text=f"触发{self.app.column_count}")
            
            # 插入数据
            self.app.tree.set(self.app.tree.get_children()[0], col_name, resistance)
            self.app.tree.set(self.app.tree.get_children()[1], col_name, voltage)
            
            # 保存到数据列表
            if len(self.app.data) < 2:
                self.app.data.append([])  # IT8811数据
                self.app.data.append([])  # DMM6500数据
            
            self.app.data[0].append(resistance)
            self.app.data[1].append(voltage)
            
        except Exception as e:
            messagebox.showerror("错误", f"记录数据失败: {str(e)}")
    
    def save_to_csv(self):
        """保存数据到CSV文件"""
        try:
            success, msg = self.app.data_manager.save_to_csv()
            if success:
                messagebox.showinfo("成功", msg)
                self.app.log(msg)
            else:
                messagebox.showerror("错误", msg)
                self.app.log(msg, level="ERROR")
        except Exception as e:
            error_msg = f"保存数据失败: {str(e)}"
            messagebox.showerror("错误", error_msg)
            self.app.log(error_msg, level="ERROR")
    
    def clear_test_data(self):
        """清除测试数据"""
        # 显示确认弹框
        result = messagebox.askyesno(
            "确认清除",
            "确定要清除所有测试数据吗？此操作不可恢复。",
            icon=messagebox.WARNING
        )
        
        if result:
            # 清除表格数据
            try:
                # 获取所有列
                columns = self.app.tree["columns"]
                # 保留前两列（触发1和触发2）
                if len(columns) > 2:
                    # 删除从第三列开始的所有列
                    for col in columns[2:]:
                        self.app.tree.delete(col)
                    # 重新设置列
                    self.app.tree["columns"] = ("col1", "col2")
                
                # 清除所有行的数据
                for item in self.app.tree.get_children():
                    for col in columns:
                        self.app.tree.set(item, col, "")
                
                # 清除DataManager中的数据
                self.app.data_manager.clear_data()
                
                # 显示成功消息
                messagebox.showinfo("成功", "测试数据已清除")
                self.app.log("测试数据已清除")
            except Exception as e:
                error_msg = f"清除数据失败: {str(e)}"
                messagebox.showerror("错误", error_msg)
                self.app.log(error_msg, level="ERROR")