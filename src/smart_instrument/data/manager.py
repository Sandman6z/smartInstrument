import csv
from datetime import datetime
import os
import subprocess

class DataManager:
    def __init__(self):
        # 数据存储
        self.data = []
        self.column_count = 0
    
    def record_data(self, resistance, voltage, current=None):
        """记录数据"""
        try:
            # 更新列计数
            self.column_count += 1
            
            # 保存到数据列表
            if len(self.data) < 3:
                self.data.append([])  # IT8811数据
                self.data.append([])  # DMM6500数据
                self.data.append([])  # KEYSIGHT 34461A数据
            
            self.data[0].append(resistance)
            self.data[1].append(voltage)
            self.data[2].append(current if current else "")
            
            return True, self.column_count
        except Exception as e:
            return False, f"记录数据失败: {str(e)}"
    
    def save_to_csv(self):
        """保存数据到CSV文件"""
        if not self.data:
            return False, "没有数据可保存"
        
        try:
            # 生成带日期时间的文件名
            filename = f"test_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # 删除旧的CSV文件，只保留最新的一个
            import glob
            old_files = glob.glob("test_data_*.csv")
            for old_file in old_files:
                if old_file != filename:
                    try:
                        os.remove(old_file)
                        print(f"删除旧文件: {old_file}")
                    except Exception as e:
                        print(f"删除旧文件失败: {str(e)}")
            
            # 写入新的CSV文件
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入标题
                headers = ['设备']
                for i in range(1, self.column_count + 1):
                    headers.append(f'触发{i}')
                writer.writerow(headers)
                
                # 写入IT8811数据
                row1 = ['IT8811 (电阻)'] + self.data[0]
                writer.writerow(row1)
                
                # 写入DMM6500数据
                row2 = ['DMM6500 (电压)'] + self.data[1]
                writer.writerow(row2)
                
                # 写入KEYSIGHT 34461A数据
                row3 = ['KEYSIGHT 34461A (电流)'] + (self.data[2] if len(self.data) > 2 else [])
                writer.writerow(row3)
            
            return True, f"数据已保存到 {filename}"
        except Exception as e:
            return False, f"保存数据失败: {str(e)}"
    
    def clear_data(self):
        """清空数据"""
        self.data = []
        self.column_count = 0
        return True, "数据已清空"
