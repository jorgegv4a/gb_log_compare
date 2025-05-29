import time
import random
import inspect
import logging
import logging.config
import numpy as np

from queue import LifoQueue, Empty
from typing import Optional, List, Dict

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

class TimedItem:
    def __init__(self, name: str, depth: int = 0, parent: Optional["TimedItem"] = None):
        self.name = name
        self.samples: List[float] = []
        self.sum: float = 0
        self.count: int = 0
        self.min: float = 0
        self.max: float = 0
        self.mean = 0
        self._sum_sq: float = 0
        self.std: float = None

        self.depth: int = depth
        self.parent: Optional["TimedItem"] = parent
        self.children: Dict[str, "TimedItem"] = dict()

    def add_sample(self, sample: float):
        self.samples.append(sample)
        if self.count == 0:
            self.min = sample
            self.max = sample
        else:
            self.min = min(self.min, sample)
            self.max = max(self.max, sample)
        self.sum += sample
        self.count += 1
        self.mean = self.sum / self.count
        self._sum_sq += sample ** 2
        self.std = np.sqrt(self._sum_sq / self.count - self.mean ** 2)

    def hierarchy_str(self) -> List[str]:
        result = [str(self)]
        for child in sorted(self.children.values(), key=lambda x: x.sum, reverse=True):
            children = child.hierarchy_str()
            result += children
        # result += [str(self)]
        return result

    def __repr__(self):
        mean = self.mean
        std = self.std
        total = self.sum
        num = self.count
        name = self.name

        color_letter = depth_colors[self.depth % len(depth_colors)]
        exp_value = int(np.floor(np.log(mean) / np.log(1000)))
        exp_string, exp_color = exponent_map[exp_value * 3]

        mean_formatted = f"{txt(f'%{color_letter}ki{mean * 1000 ** (-exp_value):8.2f}')} {txt(f'%K{exp_color}b{exp_string}')}"
        std_str = f"{std / mean * 100:6.2f}" if std is not None else "N/A"
        mean_str = f"mean: {mean_formatted:<16} (+- {std_str}%)"
        total_str = f"total: {txt(f'%{color_letter}kb{total:8.4f}%  .s')}"
        if self.depth == 0:
            name_str = f"{txt(f'%{color_letter}  {name}')}"
        else:
            name_str = f"      " * self.depth + f"\{'':->4}" + f"{txt(f'%{color_letter}  {name}')}"
            parent_frac = total / self.parent.sum
            total_str += f"{txt(f'%{color_letter}kb ({parent_frac*100:8.4f}%)')}"
        return f"{name_str:<60} | {mean_str:<32} | # {txt(f'%y  {num:<8}')} | {total_str:<16}"

    def __str__(self):
        return self.__repr__()


class TimedBlock:
    items: Dict[str, "TimedItem"] = dict()
    contexts: LifoQueue = LifoQueue()
    max_depth: int = 0

    def __init__(self, name, supress=True):
        self.t0 = time.time()
        self.name = name
        self.suppressed = supress

    def __enter__(self):
        if self.name in TimedBlock.items:
            timer = TimedBlock.items[self.name]
        else:
            timer = TimedItem(self.name, depth=TimedBlock.contexts.qsize())
        try:
            parent = TimedBlock.contexts.get(block=False)
            timer.parent = parent
            TimedBlock.contexts.put(parent)
        except Empty:
            pass
        TimedBlock.items[self.name] = timer
        TimedBlock.contexts.put(timer)
        TimedBlock.max_depth = max(TimedBlock.contexts.qsize(), TimedBlock.max_depth)

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.t0
        if not self.suppressed:
            print(f"{self.name} | elapsed: {elapsed:.4f}s")

        timer = TimedBlock.items[self.name]
        timer.add_sample(elapsed)

        x = TimedBlock.contexts.get(block=False)

        if not TimedBlock.contexts.empty():
            parent = TimedBlock.contexts.get(block=False)
            parent.children[timer.name] = timer
            TimedBlock.contexts.put(parent)

    @classmethod
    def stats(cls, name: Optional[str] = None):
        if name is None:
            names = [x for x, val in TimedBlock.items.items() if val.depth == 0]
        else:
            if name not in TimedBlock.items:
                return
            else:
                names = [name]

        values = sorted([x for key, x in TimedBlock.items.items() if key in names], key=lambda x: x.sum, reverse=True)
        for item in values:
            ret = item.hierarchy_str()
            print()
            for elem in ret:
                logger.debug(elem)
            # for d in range(1, TimedBlock.max_depth + 1):
            #     for child in sorted(item.children.values(), key=lambda x: x.sum, reverse=True):
            #         if child.depth == d:
            #             logger.debug(child)
            # # recurse over depth values to print children


if __name__ == "__main__":
    logger = get_logger()
    # logger.debug(txt("Hello %r  Friend!%.  how are you? What '%%' are you at? %by Actually,"))
    # logger.debug(txt("%.. Heck"))
    # logger.debug(txt("Hello %rkiWorld"))
    # logger.debug(txt("Hello %rkbWorld%.k., how are you?"))
    # logger.debug(txt("Hello %rkiWorld"))
    with TimedBlock("Parent A"):
        time.sleep(0.07 + 0.001 * np.random.rand())
        for i in range(7):
            with TimedBlock("Child A"):
                time.sleep(0.17 + 0.001 * np.random.rand())
        with TimedBlock("Child B"):
            time.sleep(0.03 + 0.001 * np.random.rand())
            with TimedBlock("Child C"):
                time.sleep(0.02 + 0.001 * np.random.rand())
    with TimedBlock("Parent B"):
        time.sleep(0.01 + 0.001 * np.random.rand())
        for i in range(2):
            with TimedBlock("Child D"):
                time.sleep(0.001 + 0.001 * np.random.rand())
    TimedBlock.stats()
    logger.debug("-")
    TimedBlock.stats("Child A")

    logger.info("Info")
    time.sleep(0.1)
    logger.debug("Debug")
    time.sleep(0.1)
    logger.warning("Warning")
    time.sleep(0.1)
    try:
        x = 1/0
    except Exception as e:
        logger.exception("Exception")
    time.sleep(0.1)
    logger.error("Error")
    logger.critical("Critical")
