"""
Приклади використання розширеної системи логування src/utils/log.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import log

print("=" * 60)
print("Приклади використання розширеного логування")
print("=" * 60)

# 1. Базові функції логування
print("\n1. Базові функції:")
log.info("Це INFO повідомлення")
log.error("Це ERROR повідомлення")
log.warning("Це WARNING повідомлення")
log.debug("Це DEBUG повідомлення")
log.critical("Це CRITICAL повідомлення")

# 2. Аудит дій
print("\n2. Аудит дій (log.audit):")
log.audit("Tagged 5 pages successfully", actor="BulkTaggingService", action="tag_pages")
log.audit("User logged in", actor="john@example.com", action="login")
log.audit("Configuration changed", actor="admin", action="update_config")
log.audit("System started")  # Без actor/action

# 3. JSON логування
print("\n3. JSON логування (log.log_json):")
log.log_json({
    "page_id": "123456",
    "tags": ["doc-tech", "api"],
    "status": "success"
})

log.log_json({
    "error": "Connection timeout",
    "code": 500,
    "retry_count": 3
}, level="ERROR")

log.log_json({
    "service": "BulkTaggingService",
    "pages_processed": 42,
    "skipped": 5,
    "errors": 0
})

# 4. Метрики
print("\n4. Метрики (log.log_metrics):")
log.log_metrics("pages_tagged", 42)
log.log_metrics("api_response_time", 0.523, tags={"endpoint": "/bulk/tag-pages", "status": "success"})
log.log_metrics("error_count", 3, tags={"service": "BulkTaggingService", "error_type": "timeout"})
log.log_metrics("memory_usage_mb", 256.5, tags={"process": "uvicorn"})

# 5. Генерація SQL для логування в БД
print("\n5. Генерація SQL (log.log_to_db):")
sql1 = log.log_to_db({
    "level": "INFO",
    "message": "Page processed successfully",
    "page_id": "123456"
})
print(f"SQL 1: {sql1}")

sql2 = log.log_to_db({
    "level": "ERROR",
    "message": "Failed to connect to Confluence",
    "error_code": 500
}, table="error_logs")
print(f"SQL 2: {sql2}")

sql3 = log.log_to_db({
    "action": "tag_pages",
    "actor": "BulkTaggingService",
    "success_count": 10,
    "error_count": 2
}, table="audit_logs")
print(f"SQL 3: {sql3}")

# 6. Інформація про ротацію логів
print("\n6. Інформація про ротацію (log.log_rotation):")
rotation_info = log.log_rotation()
print(f"Rotation info: {rotation_info}")

# 7. Комплексний приклад: логування операції масового тегування
print("\n7. Комплексний приклад:")
page_ids = ["111", "222", "333"]
log.audit("Starting bulk tagging operation", actor="BulkTaggingService", action="tag_pages")
log.info(f"Processing {len(page_ids)} pages")

for i, page_id in enumerate(page_ids):
    log.debug(f"Processing page {page_id}")
    
    # Симуляція тегування
    if i < 2:
        log.log_json({
            "page_id": page_id,
            "status": "success",
            "tags": ["doc-tech", "api"]
        })
        log.log_metrics("page_tagged", 1, tags={"page_id": page_id, "status": "success"})
    else:
        log.log_json({
            "page_id": page_id,
            "status": "skipped",
            "reason": "not in whitelist"
        }, level="WARNING")
        log.log_metrics("page_skipped", 1, tags={"page_id": page_id, "reason": "whitelist"})

log.audit("Bulk tagging completed", actor="BulkTaggingService", action="tag_pages")
log.log_metrics("total_pages_processed", len(page_ids))

print("\n" + "=" * 60)
print("Перевір logs/utils.log для всіх записів!")
print("=" * 60)
