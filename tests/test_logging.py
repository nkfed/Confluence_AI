"""
Тестовий скрипт для перевірки логування в logs/utils.log
"""
import sys
import os

# Додаємо кореневу директорію до PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import log

print("Тестування логування в logs/utils.log...")

log.info("Test INFO message - логування працює!")
log.error("Test ERROR message")
log.warning("Test WARNING message")
log.debug("Test DEBUG message")

print("Перевір файл logs/utils.log для підтвердження записів.")
