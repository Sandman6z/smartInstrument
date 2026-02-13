# 后端服务说明

## 安装依赖

使用uv管理Python依赖（推荐）：

```bash
# 在项目根目录运行
uv sync
```

或者使用pip：

```bash
# 在项目根目录运行
pip install -e .
```

## 运行服务

使用uv运行后端服务（推荐）：

```bash
# 在项目根目录运行
uv run .\backend\app.py
```

或者使用python：

```bash
# 在项目根目录运行
python backend/app.py
```

服务将在 http://localhost:5000 上运行，提供API接口和WebSocket服务。

## API接口说明

### 设备管理
- **GET /api/devices/scan** - 扫描可用设备
- **POST /api/devices/connect** - 连接/断开设备
- **GET /api/devices/status** - 获取设备状态

### IT8811控制
- **POST /api/it8811/resistance** - 设置电阻值
- **POST /api/it8811/output** - 控制输出开关

### 数据管理
- **POST /api/data/trigger** - 手动触发数据采集
- **POST /api/data/save** - 保存数据到CSV
- **POST /api/data/clear** - 清除测试数据

## 实时数据更新

服务使用WebSocket实现实时数据更新，前端可通过Socket.IO客户端连接获取以下事件:

- **data_updated**: 数据采集完成时触发
- **device_status_changed**: 设备状态变化时触发

## 注意事项

1. 确保已安装NI-VISA或Keysight VISA驱动
2. 运行前请确保设备已正确连接到计算机
3. 服务默认在本地运行，仅支持本地访问
