import logging
import os


def get_logger():
    FORMATTER = logging.Formatter(
        "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s"  # noqa
    )
    logger = logging.getLogger("convert-video")
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(FORMATTER)
    logger.addHandler(console_handler)
    return logger


logger = get_logger()
