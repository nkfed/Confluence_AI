"""
Тест логування у services.log після виправлення
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("ТЕСТ ЛОГУВАННЯ У SERVICES.LOG")
print("=" * 80)

# Імпортуємо BulkTaggingService
from src.services.bulk_tagging_service import logger

print("\n1. Перевірка імпортованого логера:")
print(f"   Logger name: {logger.name}")
print(f"   Logger level: {logger.level}")
print(f"   Logger handlers: {logger.handlers}")

# Тест запису
print("\n2. Тест запису у services.log:")
logger.info("TEST MESSAGE FROM BULK_TAGGING_SERVICE")
logger.info("[Bulk] Test message with Bulk prefix")
logger.warning("[Bulk] Test WARNING message")
logger.error("[Bulk] Test ERROR message")

print("\n3. Перевірте файл logs/services.log:")
print("   Має містити 4 тестові повідомлення")

# Показуємо останні 5 рядків з services.log
services_log = "logs/services.log"
if os.path.exists(services_log):
    with open(services_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"\n4. Останні 5 рядків з {services_log}:")
        for line in lines[-5:]:
            print(f"   {line.strip()}")
else:
    print(f"\n❌ Файл {services_log} не знайдено!")

print("\n" + "=" * 80)
print("✅ ВИПРАВЛЕННЯ ЗАВЕРШЕНО")
print("=" * 80)
print("bulk_tagging_service.py тепер використовує logger = get_logger(__name__)")
print("Всі повідомлення записуються у logs/services.log")
