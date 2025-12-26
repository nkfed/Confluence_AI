"""
Діагностика логерів для services - спрощена версія
"""
import logging
import os

# Перевірка наявності логерів без імпорту проєкту
print("=" * 80)
print("ДІАГНОСТИКА СТРУКТУРИ ЛОГУВАННЯ")
print("=" * 80)

# Перевірка наявності файлів
logs_dir = "logs"
print(f"\n1. Перевірка наявності директорії {logs_dir}:")
print(f"   Існує: {os.path.exists(logs_dir)}")

if os.path.exists(logs_dir):
    log_files = os.listdir(logs_dir)
    print(f"   Файли у logs/: {log_files}")
    
    for log_file in log_files:
        log_path = os.path.join(logs_dir, log_file)
        size = os.path.getsize(log_path)
        print(f"   - {log_file}: {size} bytes")

# Перевірка конфігурації logging
print("\n2. Перевірка зареєстрованих логерів:")
print(f"   Всі логери: {list(logging.Logger.manager.loggerDict.keys())[:20]}")

# Перевірка конкретних логерів
for logger_name in ["utils", "services", "api", "agents", "clients"]:
    logger = logging.getLogger(logger_name)
    print(f"\n3. Логер '{logger_name}':")
    print(f"   Level: {logger.level} ({logging.getLevelName(logger.level) if logger.level else 'NOTSET'})")
    print(f"   Handlers: {len(logger.handlers)}")
    for i, handler in enumerate(logger.handlers):
        print(f"      Handler {i}: {type(handler).__name__}")
        if hasattr(handler, 'baseFilename'):
            print(f"         File: {handler.baseFilename}")
    print(f"   Propagate: {logger.propagate}")

print("\n" + "=" * 80)
print("ПРОБЛЕМА:")
print("=" * 80)
print("bulk_tagging_service.py використовує 'from src.utils import log'")
print("Це означає, що всі повідомлення йдуть у logs/utils.log, а не logs/services.log")
print("\n✅ РІШЕННЯ: Замінити імпорт на правильний логер для сервісів")
