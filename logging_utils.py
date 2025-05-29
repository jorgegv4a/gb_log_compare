import time
import random
import inspect
import logging
import logging.config

from general import txt


class MaxLevelFilter(logging.Filter):
    """A filter to allow only log messages below a specified level."""
    def __init__(self, level):
        super().__init__()
        self.max_level = level

    def filter(self, record):
        return record.levelno < self.max_level


def get_logger(name=None, logfile=f"logfile.log", color=None):
    if color:
        color = random.choice("mygbrw")
    if name is None:
        stack = inspect.stack()
        caller_frame = stack[1]  # The frame of the caller
        module = inspect.getmodule(caller_frame[0])
        name = module.__name__
    if color:
        name = txt(f"%{color}  {name}")
    logger = logging.getLogger(name)
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "[%(module)-16s] %(levelname)-8s| %(asctime)s | %(message)s"
            },
            "traceable_src": {
                "format": f'[%(module)-16s] %(levelname)-8s| %(asctime)s | %(message)s \n{"": <19}File "%(pathname)s", line %(lineno)d in %(funcName)s'
            }
        },
        "filters": {
            "below_warning": {
                "()": MaxLevelFilter,
                "level": logging.WARNING
            }
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
              "filters": ["below_warning"]
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                # "formatter": "simple",
                "formatter": "traceable_src",
                "stream": "ext://sys.stderr"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "filename": logfile,
                "mode": "w",
                "maxBytes": 1024*1024*80,
            },
            # "telegram": {
            #     "class": "telegram.TelegramHandler",
            #     "level": "ERROR",
            #     "formatter": "simple",
            # }
        },
        "loggers": {
            "": {
                "level": "WARNING",
                "handlers": [
                    "stderr",
                    "stdout",
                    "file",
                ]
            },
            name: {
                "level": "DEBUG",
                "handlers": [
                    # "telegram",
                    "stderr",
                    "stdout",
                    "file",
                ],
                "propagate": False
            }
        }
    }

    logging.config.dictConfig(config=logging_config)
    return logger



exponent_map = {
    0: (" s", "r"),
    -3: ("ms", "Y"),
    -6: ("µs", "g"),
    -9: ("ns", "w")
}

depth_colors = [
    "m",
    "y",
    "g",
    "b",
    "r"
    "w",
]


if __name__ == "__main__":
    pass
