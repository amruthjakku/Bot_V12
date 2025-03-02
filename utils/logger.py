import logging
from config.config import LOG_FILE

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("BotV12")

def log_info(message):
    logger.info(message)

def log_error(message):
    logger.error(message)