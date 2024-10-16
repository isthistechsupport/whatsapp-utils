import os
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
