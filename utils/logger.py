import logging

def setup_logger():
    """Налаштування логування для всього проєкту."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("ConfluenceAI")

logger = setup_logger()
