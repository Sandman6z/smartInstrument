class Config:
    """应用配置类"""
    
    # IT8811默认配置
    IT8811_DEFAULT_RESISTANCE = "1000"  # 默认电阻值（Ω）
    IT8811_DEFAULT_OUTPUT = "OFF"  # 默认输出状态
    
    # DMM6500默认配置
    DMM6500_DEFAULT_MODE = "VOLT:DC"  # 默认测量模式
    
    # 连接配置
    CONNECTION_TIMEOUT = 5000  # 连接超时时间（毫秒）
    
    # GUI配置
    WINDOW_TITLE = "自动化测试工具"
    WINDOW_GEOMETRY = "1000x700"  # 窗口大小
    
    # 日志配置
    LOG_ENABLED = True
    LOG_LEVEL = "INFO"
