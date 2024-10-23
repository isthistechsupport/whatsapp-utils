import os
import time
import redis
import socket
import logging
import logging.config
from logging.handlers import SysLogHandler


class ContextFilter(logging.Filter):
    hostname: str = socket.gethostname()
    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True
    

def init_logging():
    syslogaddress = (os.getenv('SYSLOG_HOST'), int(os.getenv('SYSLOG_PORT')))
    syslog = SysLogHandler(address=syslogaddress, facility=SysLogHandler.LOG_USER)
    syslog.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger = logging.getLogger()
    logger.addHandler(syslog)
    logger.setLevel(logging.DEBUG)


def log_to_redis(key: str, value: str, value_is_sender: bool = True):
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=os.getenv('REDIS_PORT'),
        password=os.getenv('REDIS_PASSWORD'),
        ssl=True
    )
    if value_is_sender:
        value = value if value.startswith('+') else f'+{value}'
    r.set(key, value)
    r.set(f'{key}-timestamp', int(time.time()))


def read_from_redis(key: str) -> str:
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=os.getenv('REDIS_PORT'),
        password=os.getenv('REDIS_PASSWORD'),
        ssl=True
    )
    return r.get(key).decode('utf-8')