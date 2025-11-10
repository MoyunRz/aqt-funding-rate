"""
全局日志配置模块
统一管理整个项目的日志输出和存储
"""

import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


class LoggerConfig:
    """
    全局日志配置类
    
    功能：
    - 统一配置日志格式
    - 支持控制台和文件双重输出
    - 日志文件自动轮转
    - 按日期分文件存储
    """
    
    # 日志存储目录
    LOG_DIR = "logs"
    
    # 日志格式
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # 日志级别
    LOG_LEVEL = logging.INFO
    
    # 是否已初始化
    _initialized = False
    
    @classmethod
    def init_logger(cls, 
                   log_dir: str = None, 
                   log_level: int = None,
                   console_output: bool = True,
                   file_output: bool = True):
        """
        初始化全局日志配置
        
        Args:
            log_dir: 日志文件存储目录，默认为 'logs'
            log_level: 日志级别，默认为 INFO
            console_output: 是否输出到控制台，默认 True
            file_output: 是否输出到文件，默认 True
        """
        if cls._initialized:
            logging.getLogger(__name__).warning("日志系统已经初始化，跳过重复初始化")
            return
        
        # 设置日志目录
        if log_dir:
            cls.LOG_DIR = log_dir
        
        # 设置日志级别
        if log_level:
            cls.LOG_LEVEL = log_level
        
        # 创建日志目录
        if file_output and not os.path.exists(cls.LOG_DIR):
            os.makedirs(cls.LOG_DIR)
            
        # 获取根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(cls.LOG_LEVEL)
        
        # 清除已存在的处理器，避免重复
        root_logger.handlers.clear()
        
        # 创建日志格式器
        formatter = logging.Formatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        
        # ==================== 控制台输出处理器 ====================
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(cls.LOG_LEVEL)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # ==================== 文件输出处理器 ====================
        if file_output:
            # 1. 按日期轮转的日志文件（每天一个文件）
            today = datetime.now().strftime('%Y-%m-%d')
            daily_log_file = os.path.join(cls.LOG_DIR, f'funding_rate_{today}.log')
            
            daily_handler = TimedRotatingFileHandler(
                daily_log_file,
                when='midnight',  # 每天午夜轮转
                interval=1,
                backupCount=30,  # 保留30天的日志
                encoding='utf-8'
            )
            daily_handler.setLevel(cls.LOG_LEVEL)
            daily_handler.setFormatter(formatter)
            daily_handler.suffix = "%Y-%m-%d"  # 备份文件后缀
            root_logger.addHandler(daily_handler)
            
            # 2. 按大小轮转的总日志文件（防止单个文件过大）
            all_log_file = os.path.join(cls.LOG_DIR, 'funding_rate_all.log')
            
            rotating_handler = RotatingFileHandler(
                all_log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,  # 保留5个备份文件
                encoding='utf-8'
            )
            rotating_handler.setLevel(cls.LOG_LEVEL)
            rotating_handler.setFormatter(formatter)
            root_logger.addHandler(rotating_handler)
            
            # 3. 错误日志单独记录
            error_log_file = os.path.join(cls.LOG_DIR, 'error.log')
            
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)  # 只记录ERROR及以上级别
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
        
        # 标记为已初始化
        cls._initialized = True
        
        # 记录初始化信息
        logger = logging.getLogger(__name__)
        logger.info("=" * 70)
        logger.info("日志系统初始化成功")
        logger.info(f"日志目录: {os.path.abspath(cls.LOG_DIR)}")
        logger.info(f"日志级别: {logging.getLevelName(cls.LOG_LEVEL)}")
        logger.info(f"控制台输出: {'开启' if console_output else '关闭'}")
        logger.info(f"文件输出: {'开启' if file_output else '关闭'}")
        logger.info("=" * 70)
    
    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            name: 记录器名称，通常使用 __name__
            
        Returns:
            logging.Logger: 日志记录器对象
        """
        if not cls._initialized:
            # 如果未初始化，使用默认配置初始化
            cls.init_logger()
        
        return logging.getLogger(name)
    
    @classmethod
    def set_level(cls, level: int):
        """
        动态修改日志级别
        
        Args:
            level: 日志级别（logging.DEBUG, logging.INFO, etc.）
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        for handler in root_logger.handlers:
            handler.setLevel(level)
        
        cls.LOG_LEVEL = level
        logging.getLogger(__name__).info(f"日志级别已修改为: {logging.getLevelName(level)}")


def get_logger(name: str = None) -> logging.Logger:
    """
    快捷函数：获取日志记录器
    
    使用示例：
        from utils.logger_config import get_logger
        logger = get_logger(__name__)
        logger.info("这是一条日志")
    
    Args:
        name: 记录器名称，通常使用 __name__
        
    Returns:
        logging.Logger: 日志记录器对象
    """
    return LoggerConfig.get_logger(name)

