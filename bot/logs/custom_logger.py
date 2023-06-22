import logging
import os
import time
from pathlib import Path


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1b[32;1m"
    formatstr = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"
    converter = time.gmtime
    datefmt = "%Y-%m-%d %I:%M:%S %Z"

    FORMATS = {
        logging.DEBUG: grey + formatstr + reset,
        logging.INFO: green + formatstr + reset,
        logging.WARNING: yellow + formatstr + reset,
        logging.ERROR: red + formatstr + reset,
        logging.CRITICAL: bold_red + formatstr + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt)
        return formatter.format(record)


class BotLogger(logging.Logger):
    def __init__(self, name: str, err: bool = False) -> None:
        super().__init__(name, logging.DEBUG)
        console_hndl = logging.StreamHandler()
        console_hndl.setLevel(logging.DEBUG)
        console_hndl.setFormatter(CustomFormatter())

        # watch for the path
        file_handle = logging.FileHandler(
            "./bot/logs/logs.log" if not err else "./bot/logs/exceptions.log",
            encoding="utf-8",
        )
        file_handle.setLevel(logging.DEBUG)
        file_handle.setFormatter(logging.Formatter(CustomFormatter.formatstr))
        self.addHandler(file_handle)
        self.addHandler(console_hndl)


class MailLogger(logging.Logger):
    def __init__(self, name: str) -> None:
        super().__init__(name, logging.INFO)
        console_hndl = logging.StreamHandler()
        console_hndl.setLevel(logging.INFO)
        console_hndl.setFormatter(
            logging.Formatter("%(name)s - %(message)s - at %(asctime)s")
        )
        log_path = Path(f"bot/logs/{name}/{name}-logs.log")
        if not log_path.exists():
            os.mkdir(os.getcwd() + f"/bot/logs/{name}")
        # watch for the path
        file_handle = logging.FileHandler(
            f"bot/logs/{name}/{name}-logs.log",
            encoding="utf-8",
        )
        file_handle.setLevel(logging.INFO)
        self.addHandler(file_handle)
        self.addHandler(console_hndl)
