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
    logger.setLevel(logging.INFO)


def log_to_redis(media_id: str, from_number: str):
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=os.getenv('REDIS_PORT'),
        password=os.getenv('REDIS_PASSWORD'),
        ssl=True
    )
    sender = from_number if from_number.startswith('+') else f'+{from_number}'
    r.set(media_id, sender)
    r.set(f'{media_id}-timestamp', int(time.time()))
