import colorlog
from datetime import datetime
import pytz
from config import basic

class Logger:
    def __init__(self,log_name='root'):
        # 创建日志记录器
        self.logger = colorlog.getLogger(log_name)  # 创建日志记录器
        # 设置日志输出格式,输出INFO级别的日志，并添加时区信息
        colorlog.basicConfig(
            level='INFO', 
            format='%(log_color)s[%(asctime)s Shanghai][%(name)s][%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S', 
            reset=True
        )
        # 获取UTC时区
        self.tz = basic.TIMEZONE

    def _get_time(self):
        # 获取当前上海时间
        return datetime.now(self.tz)

    def info(self, message):
        if message == "":
            return
        # 输出INFO级别的日志
        self.logger.info(message)

    def debug(self, message):
        if message == "":
            return
        # 输出DEBUG级别的日志
        self.logger.debug(message)

    def error(self, message):
        if message == "":
            return
        # 输出ERROR级别的日志
        self.logger.error(message)

    def warning(self, message):
        if message == "":
            return
        # 输出WARNING级别的日志
        self.logger.warning(message)

if __name__ == '__main__':
    # 创建日志记录器
    logger = Logger().info('This is an info message with Shanghai time')
    # 输出INFO级别的日志