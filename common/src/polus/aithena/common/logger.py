"""Logger module for Aithena."""

from datetime import datetime
from . import config
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)-8s - %(levelname)-8s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

# Factory for aithena loggers
def get_logger(file = "", log_level = config.AITHENA_LOG_LEVEL):
    logger = logging.getLogger(file)
    logger.setLevel(log_level)
    return logger

# Create a logger that logs the execution time of decorated functions
exec_time_logger = logging.getLogger('execution_time_logger')
exec_time_logger.setLevel(logging.INFO)
# Create a file handler
date_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f"execution_time_{date_time_str}.log"
file_handler = logging.FileHandler(filename)
file_handler.setLevel(logging.INFO)
# Create a logging format
formatter = logging.Formatter("%(asctime)s - %(name)-8s - %(levelname)-8s - %(message)s")
file_handler.setFormatter(formatter)
# Add the file handler to the logger
exec_time_logger.addHandler(file_handler)

# psycopg.DataError: cannot dump lists of mixed types; got: float, int