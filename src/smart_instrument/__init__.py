"""智能仪器自动化测试工具包"""

__version__ = "0.1.0"

import logging
import os
from datetime import datetime

def setup_logging(log_level=logging.INFO):
    """配置全局日志"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"smart_instrument_{timestamp}.log")
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info(f"日志已初始化，文件路径: {log_file}")
