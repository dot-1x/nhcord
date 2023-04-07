import logging


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1b[32;1m"
    formatstr = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + formatstr + reset,
        logging.INFO: green + formatstr + reset,
        logging.WARNING: yellow + formatstr + reset,
        logging.ERROR: red + formatstr + reset,
        logging.CRITICAL: bold_red + formatstr + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class BotLogger(logging.Logger):
    def __init__(self, name: str) -> None:
        super().__init__(name, logging.DEBUG)
        console_hndl = logging.StreamHandler()
        console_hndl.setLevel(logging.DEBUG)
        console_hndl.setFormatter(CustomFormatter())

        # watch for the path
        file_handle = logging.FileHandler("./bot/logs/logs.log", encoding="utf-8")
        file_handle.setLevel(logging.DEBUG)
        file_handle.setFormatter(logging.Formatter(CustomFormatter.formatstr))
        self.addHandler(file_handle)
        self.addHandler(console_hndl)
