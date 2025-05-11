import logging
import colorlog
import os

LOG_LEVEL = logging.DEBUG if os.getenv("DEV") == "true" else logging.INFO

def setup_logger(name: str = "Blockchain"):
    """设置并返回logger"""
    # 获取logger
    logger = logging.getLogger(name)
    
    # 如果logger已经有handlers，说明已经被设置过，直接返回
    if logger.handlers:
        return logger
        
    # 清除所有已存在的handlers
    logger.handlers = []
    
    # 设置日志级别
    logger.setLevel(LOG_LEVEL)
    
    # 阻止日志传递给父logger
    logger.propagate = False
    
    # 定义日志格式
    log_format = '%(asctime)s - [%(levelname)s] - [%(filename)s:%(lineno)d] - %(message)s'
    colored_formatter = colorlog.ColoredFormatter(
        fmt=f'%(log_color)s{log_format}',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        }
    )

    # 添加控制台handler
    ch = logging.StreamHandler()
    ch.setFormatter(colored_formatter)
    logger.addHandler(ch)

    return logger