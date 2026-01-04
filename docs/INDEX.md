# 📚 Індекс документації Confluence AI

Повна карта всієї документації проєкту з посиланнями та описами.

**Дата оновлення:** 2 січня 2026  
**Структура версія:** 4.0 (реструктурована)

---

## 🗂️ Структура папок

```
docs/
├── architecture/        # Архітектура системи, агенти, AI маршрутизація
├── bulk-operations/     # Операції з масовим тегуванням (tag-pages, tag-tree, tag-space)
├── guides/             # Гайди, best practices, оптимізація
├── logging/            # Логування, трекінг, обробка витрат
├── spaces/             # Spaces metadata, фільтрація, нормалізація
├── testing/            # Правила тестування (DEPRECATED: див. guides/)
├── vscode/             # VS Code оптимізація (DEPRECATED: див. guides/)
├── whitelist/          # Whitelist механізм та керування доступом
├── archive/            # Старі та deprecated файли
├── README.md           # Основний гайд для початку
├── INDEX.md            # Цей файл
└── AUDIT_REPORT_2026-01.md # Результати аудиту документації
```

---

## 📘 Основні документи

### 🏠 Стартові файли

| Файл | Опис | Для кого |
|------|------|----------|
| **[README.md](README.md)** | Основний гайд, quick start, структура | Всім |
| **[INDEX.md](INDEX.md)** | Этот файл, повна карта | Тим, хто шукає конкретну інформацію |
| **[AUDIT_REPORT_2026-01.md](AUDIT_REPORT_2026-01.md)** | Результати аудиту та рекомендації | Мейнтейнери |

---

## 🏗️ Архітектура системи

### Система режимів агентів

| Файл | Опис | Рівень |
|------|------|--------|
| **[architecture/agent-modes-overview.md](architecture/agent-modes-overview.md)** | Огляд трьох режимів (TEST, SAFE_TEST, PROD) | Вступний |
| **[architecture/agent-mode-router.md](architecture/agent-mode-router.md)** | Маршрутизація та інтеграція з компонентами | Середній |
| **[architecture/agent-mode-lifecycle.md](architecture/agent-mode-lifecycle.md)** | Цикл життя операцій, state diagram | Детальний |
| **[architecture/agent-mode-errors.md](architecture/agent-mode-errors.md)** | Обробка помилок, debug, recovery | Продвинутий |

### Загальна архітектура

| Файл | Опис |
|------|------|
| **[architecture/MULTI_AI_ARCHITECTURE.md](architecture/MULTI_AI_ARCHITECTURE.md)** | Архітектура багатьох AI провайдерів |
| **[architecture/AI_ROUTER_INTEGRATION.md](architecture/AI_ROUTER_INTEGRATION.md)** | Інтеграція AI роутера з системою |
| **[architecture/AI_ROUTING_MODES.md](architecture/AI_ROUTING_MODES.md)** | Режими маршрутизації запитів |
| **[architecture/AI_ROUTING_INSPECTOR.md](architecture/AI_ROUTING_INSPECTOR.md)** | Інспектор для дебагу маршрутизації |

---

## 🏷️ Операції з тегами (Bulk Operations)

### Основні endpoint-и

| Файл | Endpoint | Опис |
|------|----------|------|
| **[bulk-operations/TAG_PAGES_ENDPOINT.md](bulk-operations/TAG_PAGES_ENDPOINT.md)** | `POST /bulk/tag-pages` | Тегування сторінок за ID |
| **[bulk-operations/TAG_TREE_ENDPOINT.md](bulk-operations/TAG_TREE_ENDPOINT.md)** | `POST /bulk/tag-tree/{space_key}/{root_id}` | Тегування дерева сторінок |

### Whitelist для операцій

| Файл | Опис |
|------|------|
| **[bulk-operations/TAG_PAGES_WHITELIST.md](bulk-operations/TAG_PAGES_WHITELIST.md)** | Whitelist для tag-pages |

### Специфічні операції та исправления

| Файл | Опис |
|------|------|
| **[bulk-operations/RESET_TAGS_ROOT_ID.md](bulk-operations/RESET_TAGS_ROOT_ID.md)** | Скидання тегів за root_id |
| **[bulk-operations/TAG_TREE_REFACTORING.md](bulk-operations/TAG_TREE_REFACTORING.md)** | Рефакторинг tag-tree логіки |
| **[bulk-operations/TAG_TREE_WHITELIST.md](bulk-operations/TAG_TREE_WHITELIST.md)** | Whitelist для tag-tree |
| **[bulk-operations/TAG_SPACE_EMPTY_BODY_FIX.md](bulk-operations/TAG_SPACE_EMPTY_BODY_FIX.md)** | Виправлення для пустих body |
| **[bulk-operations/TAG_SPACE_WHITELIST_ALWAYS_ON.md](bulk-operations/TAG_SPACE_WHITELIST_ALWAYS_ON.md)** | Whitelist завжди увімкнений |
| **[bulk-operations/DRY_RUN_FIX.md](bulk-operations/DRY_RUN_FIX.md)** | Виправлення dry-run логіки |
| **[bulk-operations/DRY_RUN_RESPONSE_STANDARD.md](bulk-operations/DRY_RUN_RESPONSE_STANDARD.md)** | Стандарт для dry-run response |
| **[bulk-operations/EXPAND_PARAMETER_FIX.md](bulk-operations/EXPAND_PARAMETER_FIX.md)** | Виправлення expand параметра |

---

## 📖 Гайди та Best Practices

### Основні гайди

| Файл | Опис | Аудиторія |
|------|------|-----------|
| **[guides/PROMPT_ENGINEERING.md](guides/PROMPT_ENGINEERING.md)** | Інженерія промптів, best practices, приклади | AI розробники |
| **[guides/TESTING_GUIDELINES.md](guides/TESTING_GUIDELINES.md)** | Правила тестування, чеклісти, стратегії | QA, розробники |
| **[guides/VSCODE_OPTIMIZATION.md](guides/VSCODE_OPTIMIZATION.md)** | Оптимізація VS Code, розширення, налаштування | Всі розробники |

---

## 🔐 Whitelist механізм

| Файл | Опис |
|------|------|
| **[whitelist/WHITELIST_MECHANISM.md](whitelist/WHITELIST_MECHANISM.md)** | Основна документація whitelist системи |
| **[whitelist/WHITELIST_QUICK_START.md](whitelist/WHITELIST_QUICK_START.md)** | Quick start для whitelist |
| **[whitelist/WHITELIST_RECURSIVE_FIX.md](whitelist/WHITELIST_RECURSIVE_FIX.md)** | Виправлення рекурсивної логіки |

---

## 📊 Логування та Трекінг

| Файл | Опис |
|------|------|
| **[logging/logging_guide.md](logging/logging_guide.md)** | Основний гайд для логування |
| **[logging/AI_COST_TRACKING.md](logging/AI_COST_TRACKING.md)** | Трекінг вартості AI операцій |
| **[logging/AI_ERROR_HANDLING.md](logging/AI_ERROR_HANDLING.md)** | Обробка помилок в AI |
| **[logging/AI_LOGGING_LAYER.md](logging/AI_LOGGING_LAYER.md)** | Логування рівні для AI |
| **[logging/AI_RATE_LIMITING.md](logging/AI_RATE_LIMITING.md)** | Rate limiting для AI запитів |

---

## 🌍 Spaces операції

| Файл | Опис |
|------|------|
| **[spaces/SPACES_METADATA_FILTERING.md](spaces/SPACES_METADATA_FILTERING.md)** | Фільтрація за metadata |
| **[spaces/SPACES_METADATA_SUMMARY.md](spaces/SPACES_METADATA_SUMMARY.md)** | Summary для spaces |
---

## 📦 Archive (Deprecated та старі файли)

Грудень 2025–січень 2026: перенесено 12 файлів (дублікати, summary-файли, legacy endpoints).
Див. [docs/archive/](archive/) та [docs/audit/05_deprecated_files.md](audit/05_deprecated_files.md).

---

## 🔍 Пошук за темами

### 🤖 AI та машинне навчання
- [MULTI_AI_ARCHITECTURE.md](architecture/MULTI_AI_ARCHITECTURE.md)
- [AI_ROUTER_INTEGRATION.md](architecture/AI_ROUTER_INTEGRATION.md)
- [PROMPT_ENGINEERING.md](guides/PROMPT_ENGINEERING.md)
- [AI_COST_TRACKING.md](logging/AI_COST_TRACKING.md)

### 🏷️ Тегування та Tagging
- [TAG_PAGES_ENDPOINT.md](bulk-operations/TAG_PAGES_ENDPOINT.md)
- [TAG_TREE_ENDPOINT.md](bulk-operations/TAG_TREE_ENDPOINT.md)
- [RESET_TAGS_ROOT_ID.md](bulk-operations/RESET_TAGS_ROOT_ID.md)
- [DRY_RUN_RESPONSE_STANDARD.md](bulk-operations/DRY_RUN_RESPONSE_STANDARD.md)

### 🔒 Безпека та Дозволи
- [WHITELIST_MECHANISM.md](whitelist/WHITELIST_MECHANISM.md)
- [agent-modes-overview.md](architecture/agent-modes-overview.md)
- [agent-mode-errors.md](architecture/agent-mode-errors.md)

### 📊 Логування та Моніторинг
- [logging_guide.md](logging/logging_guide.md)
- [AI_COST_TRACKING.md](logging/AI_COST_TRACKING.md)
- [AI_ERROR_HANDLING.md](logging/AI_ERROR_HANDLING.md)

### 🧪 Тестування
- [TESTING_GUIDELINES.md](guides/TESTING_GUIDELINES.md)
- [agent-mode-lifecycle.md](architecture/agent-mode-lifecycle.md)

### ⚙️ Конфігурація та Оптимізація
- [VSCODE_OPTIMIZATION.md](guides/VSCODE_OPTIMIZATION.md)
- [AI_ROUTING_MODES.md](architecture/AI_ROUTING_MODES.md)

---

## 🎯 Для конкретних задач

### Я хочу...

#### ...додати новий AI провайдер
1. Почніть з [MULTI_AI_ARCHITECTURE.md](architecture/MULTI_AI_ARCHITECTURE.md)
2. Потім див. [AI_ROUTER_INTEGRATION.md](architecture/AI_ROUTER_INTEGRATION.md)
3. Додайте логування через [logging_guide.md](logging/logging_guide.md)

#### ...реалізувати новий режим роботи
1. Див. [agent-modes-overview.md](architecture/agent-modes-overview.md)
2. Реалізуйте маршрутизацію [agent-mode-router.md](architecture/agent-mode-router.md)
3. Обробіть помилки [agent-mode-errors.md](architecture/agent-mode-errors.md)

#### ...покращити тегування
1. Почніть з [TAG_PAGES_ENDPOINT.md](bulk-operations/TAG_PAGES_ENDPOINT.md)
2. Порівняйте з [DRY_RUN_RESPONSE_STANDARD.md](bulk-operations/DRY_RUN_RESPONSE_STANDARD.md)
3. Прочитайте [WHITELIST_MECHANISM.md](whitelist/WHITELIST_MECHANISM.md)

#### ...налаштувати логування
1. Див. [logging_guide.md](logging/logging_guide.md)
2. Для AI операцій див. [AI_LOGGING_LAYER.md](logging/AI_LOGGING_LAYER.md)
3. Для вартості див. [AI_COST_TRACKING.md](logging/AI_COST_TRACKING.md)

#### ...написати тести
1. Див. [TESTING_GUIDELINES.md](guides/TESTING_GUIDELINES.md)
2. Для агентів див. [agent-mode-lifecycle.md](architecture/agent-mode-lifecycle.md)
3. Для error cases див. [agent-mode-errors.md](architecture/agent-mode-errors.md)

---

## 📈 Статистика документації

- **Всього документів:** 41+
- **Основні папки:** 9
- **Архівовактивних документів:** 30+
- **Основні папки:** 9
- **Архівовано:** 12
- **Останнє оновлення:** 2 січня 2026
- **Структура версія:** 4

## 📝 Метадані

- **Інструмент:** VS Code Agent
- **Тип:** Документація проєкту Confluence AI
- **Мова:** Українська
- **Формат:** Markdown
- **Статус:** ✅ Актуальна (відновлена 2026-01-02)

---

**Останнє оновлення:** 2 січня 2026, 12:00  
**Версія документації:** 4.0  
**Статус:** ✅ Реструктурована v4.0
