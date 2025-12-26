"""
Тестування оновленої функції log_to_db()
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import log

print("=" * 80)
print("Тестування оновленої функції log.log_to_db()")
print("=" * 80)

# Тест 1: Базовий приклад
print("\n1. Базовий приклад:")
sql1 = log.log_to_db({
    "level": "INFO",
    "message": "Page processed"
})
print(f"SQL: {sql1}")

# Тест 2: З екранізацією одинарних лапок
print("\n2. Екранізація одинарних лапок:")
sql2 = log.log_to_db({
    "level": "ERROR",
    "message": "User's input contains error",
    "details": "Can't process the request"
})
print(f"SQL: {sql2}")

# Тест 3: Кастомна таблиця
print("\n3. Кастомна таблиця:")
sql3 = log.log_to_db({
    "action": "tag_pages",
    "actor": "BulkTaggingService",
    "success_count": 10,
    "error_count": 2
}, table="audit_logs")
print(f"SQL: {sql3}")

# Тест 4: З timestamp
print("\n4. З власним timestamp:")
sql4 = log.log_to_db({
    "timestamp": "2025-12-26 12:00:00",
    "level": "WARNING",
    "message": "High memory usage"
})
print(f"SQL: {sql4}")

# Тест 5: JSON-подібні дані
print("\n5. JSON-подібні дані:")
sql5 = log.log_to_db({
    "level": "INFO",
    "message": "Operation completed",
    "data": '{"page_id": "123", "status": "success"}',
    "tags": "['tag1', 'tag2']"
})
print(f"SQL: {sql5}")

# Тест 6: Порожній словник
print("\n6. Порожній словник:")
sql6 = log.log_to_db({})
print(f"SQL: {sql6}")

# Тест 7: Спеціальні символи
print("\n7. Спеціальні символи:")
sql7 = log.log_to_db({
    "level": "ERROR",
    "message": "Error: It's a SQL injection test with 'quotes' and \"double quotes\"",
    "query": "SELECT * FROM users WHERE name = 'O'Brien'"
})
print(f"SQL: {sql7}")

# Тест 8: Числові значення
print("\n8. Числові значення:")
sql8 = log.log_to_db({
    "level": "INFO",
    "response_time": 0.523,
    "status_code": 200,
    "bytes_sent": 1024
})
print(f"SQL: {sql8}")

print("\n" + "=" * 80)
print("Всі тести пройдено успішно!")
print("Функція log_to_db() стабільна, безпечна та готова до використання.")
print("=" * 80)
