import logging

logger = logging.getLogger(__name__)

shell_handler = logging.StreamHandler()

logger.setLevel(logging.DEBUG)

shell_handler.setLevel(logging.DEBUG)
shell_formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')

shell_handler.setFormatter(shell_formatter)
logger.addHandler(shell_handler)
