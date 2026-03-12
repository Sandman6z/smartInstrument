class Config:
    """应用配置类"""
    
    # IT8811默认配置
    IT8811_DEFAULT_RESISTANCE = "1000"  # 默认电阻值（Ω）
    IT8811_DEFAULT_OUTPUT = "OFF"  # 默认输出状态
    
    # DMM6500默认配置
    DMM6500_DEFAULT_MODE = "VOLT:DC"  # 默认测量模式
    
    # 设备标识与地址配置
    IT8811_USB_ID = "0x2EC7::0x8800"
    DMM6500_IP = "192.168.1.89"
    KEYSIGHT_HOSTNAME = "K-34461A-15943.local"
    
    # 连接配置
    CONNECTION_TIMEOUT = 3000  # 连接超时时间（毫秒），设置为平衡响应速度和可靠性的中间值
    
    # GUI配置
    WINDOW_TITLE = "自动化测试工具"
    WINDOW_GEOMETRY = "1000x600"  # 窗口大小，减少纵向尺寸
    
    # 日志配置
    LOG_ENABLED = True
    LOG_LEVEL = "INFO"
