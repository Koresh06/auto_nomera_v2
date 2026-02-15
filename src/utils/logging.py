import logging
import betterlogging as bl


def setup_logging() -> None:
    log_level = logging.INFO

    bl.basic_colorized_config(level=log_level)

    logger = logging.getLogger("my_app")
    logger.setLevel(log_level)