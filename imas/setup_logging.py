# This file is part of imas-python.
# You should have received the imas-python LICENSE file with this project.
"""Create a default log handler when imas-python is imported.
"""

import logging
import os


class _PrettyFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    light_grey = "\x1b[90m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    formatstr = (
        "%(asctime)s %(levelname)-8s %(message)s "
        f"{light_grey}@%(filename)s:%(lineno)d{reset}"
    )
    time_format = "%H:%M:%S"

    FORMATS = {
        logging.DEBUG: logging.Formatter(light_grey + formatstr, time_format),
        logging.INFO: logging.Formatter(formatstr, time_format),
        logging.WARNING: logging.Formatter(yellow + formatstr, time_format),
        logging.ERROR: logging.Formatter(red + formatstr, time_format),
        logging.CRITICAL: logging.Formatter(bold_red + formatstr, time_format),
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        return formatter.format(record)


def test_messages():
    """Print out a message on each logging level"""
    logger = logging.getLogger("imas.testlogger")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")


def connect_formatter(logger):
    """Connect general formatter to given logger"""
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_PrettyFormatter())
    logger.addHandler(ch)


# Log to console by default, and output it all
logger = logging.getLogger("imas")
connect_formatter(logger)

loglevel = os.getenv("IMAS_LOGLEVEL") or "INFO"
logger.setLevel(loglevel)

if __name__ == "__main__":
    test_messages()
