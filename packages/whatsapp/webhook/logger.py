import sys
import socket
import logging
import logging.config


class ContextFilter(logging.Filter):
    """This filter adds the hostname and name to the log message"""
    hostname: str = socket.gethostname()
    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True


class LevelFilter(logging.Filter):
    """This filter directs log records based on their level (used for stdout and stderr)"""
    def __init__(self, level: int):
        self.level = level

    def filter(self, record):
        return record.levelno <= self.level

    
def init_logging():
    """Initializes the logging system. This should be called at the beginning of the program."""
    CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(hostname)s %(levelname)s tootbot: %(message)s",
                "datefmt": "%b %d %H:%M:%S",
            },
        },
        "filters": {
            "level_filter": {
                "()": LevelFilter,
                "level": logging.WARNING,
            },
            "context_filter": {
                "()": ContextFilter,
            },
        },
        "handlers": {
            "syslog": {
                "class": "logging.handlers.SysLogHandler",
                "address": ("localhost", 514),
                "formatter": "default",
                "filters": ["context_filter"],
                "level": logging.INFO,
            },
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "filters": ["context_filter", "level_filter"],
                "level": logging.INFO
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "stream": sys.stderr,
                "formatter": "default",
                "filters": ["context_filter"],
                "level": logging.ERROR,
            },
        },
        "loggers": {
            "": {
                "handlers": ["syslog", "stdout"],
                "level": logging.INFO,
            },
        },
    }
    logging.config.dictConfig(CONFIG)
