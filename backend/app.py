from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.smart_instrument.device.controller import DeviceController
from src.smart_instrument.data.manager import DataManager

app = Flask(__name__)
CORS(app)  # 允许跨域请求
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化设备控制器和数据管理器
device_controller = DeviceController()
data_manager = DataManager()

# 设备扫描API
@app.route('/api/devices/scan', methods=['GET'])
def scan_devices():
    try:
        device_list, device_info, it8811_device, dmm6500_device, keysight_device = device_controller.scan_devices()
        return jsonify({
            "success": True,
            "devices": device_list,
            "device_info": device_info,
            "auto_selected": {
                "it8811": it8811_device,
                "dmm6500": dmm6500_device,
                "keysight": keysight_device
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 设备连接API
@app.route('/api/devices/connect', methods=['POST'])
def connect_device():
    data = request.json
    device_type = data.get('type')  # 'it8811', 'dmm6500', 'keysight'
    resource = data.get('resource')
    action = data.get('action', 'connect')  # 'connect' or 'disconnect'
    
    try:
        if action == 'connect':
            if device_type == 'it8811':
                success, msg = device_controller.connect_it8811(resource)
            elif device_type == 'dmm6500':
                success, msg = device_controller.connect_dmm6500(resource)
            elif device_type == 'keysight':
                success, msg = device_controller.connect_keysight_34461a(resource)
            else:
                return jsonify({"success": False, "message": "Invalid device type"})
        else:  # disconnect
            if device_type == 'it8811':
                success, msg = device_controller.disconnect_it8811()
            elif device_type == 'dmm6500':
                success, msg = device_controller.disconnect_dmm6500()
            elif device_type == 'keysight':
                success, msg = device_controller.disconnect_keysight_34461a()
            else:
                return jsonify({"success": False, "message": "Invalid device type"})
        
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 电阻设置API
@app.route('/api/it8811/resistance', methods=['POST'])
def set_resistance():
    data = request.json
    resistance = data.get('resistance')
    
    try:
        success, msg = device_controller.set_resistance(resistance)
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 输出控制API
@app.route('/api/it8811/output', methods=['POST'])
def toggle_output():
    data = request.json
    state = data.get('state')  # 'ON' or 'OFF'
    
    try:
        success, msg = device_controller.toggle_output(state)
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 手动触发API
@app.route('/api/data/trigger', methods=['POST'])
def manual_trigger():
    try:
        # 获取电阻值
        res_success, resistance = device_controller.get_resistance()
        if not res_success:
            resistance = "N/A"
        
        # 获取电压值
        volt_success, voltage = device_controller.get_voltage()
        if not volt_success:
            voltage = "N/A"
        
        # 获取电流值
        curr_success, current = device_controller.get_current()
        if not curr_success:
            current = "N/A"
        
        # 记录数据
        success, msg = data_manager.record_data(resistance, voltage, current)
        
        # 发送实时数据到前端
        socketio.emit('data_updated', {
            "resistance": resistance,
            "voltage": voltage,
            "current": current
        })
        
        return jsonify({"success": success, "data": {"resistance": resistance, "voltage": voltage, "current": current}})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 保存数据API
@app.route('/api/data/save', methods=['POST'])
def save_data():
    try:
        success, msg = data_manager.save_to_csv()
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 清除数据API
@app.route('/api/data/clear', methods=['POST'])
def clear_data():
    try:
        success, msg = data_manager.clear_data()
        return jsonify({"success": success, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 获取设备状态API
@app.route('/api/devices/status', methods=['GET'])
def get_device_status():
    try:
        status = {
            "it8811": {
                "connected": device_controller.it8811_connected,
                "info": device_controller.it8811_info if hasattr(device_controller, 'it8811_info') else {}
            },
            "dmm6500": {
                "connected": device_controller.dmm6500_connected,
                "info": device_controller.dmm6500_info if hasattr(device_controller, 'dmm6500_info') else {}
            },
            "keysight": {
                "connected": device_controller.keysight_34461a_connected,
                "info": device_controller.keysight_34461a_info if hasattr(device_controller, 'keysight_34461a_info') else {}
            }
        }
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# 启动SocketIO服务器
if __name__ == '__main__':
    socketio.run(app, host='localhost', port=5000, debug=False)
