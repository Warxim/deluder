import logging


logging.basicConfig(
    format='%(asctime)s.%(msecs)03dZ [%(levelname)s] (%(name)s) %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger('Deluder')


def create_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_debug_level(debug: bool):
    if debug:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)
