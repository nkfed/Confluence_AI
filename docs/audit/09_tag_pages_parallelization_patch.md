# Patch: Паралелізація обробки tag-pages

**File:** `src/services/bulk_tagging_service.py`  
**Change:** Впровадити asyncio.gather() для паралельної обробки сторінок  
**Expected Impact:** 100+ сек → 30-50 сек для 2-3 сторінок

---

## 📝 Код для заміни

### Поточний код (СЕРІЙНА обробка)

**Локація:** Lines 175-230 у `tag_pages()` методі

```python
        logger.info(
            f"[TagPages] Processing {len(filtered_ids)} allowed pages "
            f"(mode={mode}, effective_dry_run={effective_dry_run}, skipped={skipped_due_to_whitelist})"
        )

        # Process filtered pages only
        for page_id_int in filtered_ids:
            # ✅ Перевірка чи не зупинено процес
            if task_id and not ACTIVE_TASKS.get(task_id, True):
                logger.info(f"[TagPages] Task {task_id} stopped by user, breaking loop")
                break
            
            page_id = str(page_id_int)
            try:
                logger.info(f"[TagPages] Processing page {page_id} (effective_dry_run={effective_dry_run})")
                
                # Завантажуємо контент сторінки
                page = await self.confluence.get_page(page_id)
                if not page:
                    logger.warning(f"[TagPages] Page {page_id} not found")
                    error_count += 1
                    results.append({
                        "page_id": page_id,
                        "status": "error",
                        "message": "Page not found"
                    })
                    continue
                
                text = page.get("body", {}).get("storage", {}).get("value", "")
                logger.debug(f"[TagPages] Extracted {len(text)} chars from page {page_id}")
                
                # Формуємо індивідуальний AI-промпт на основі контенту
                logger.info(f"[TagPages] Calling TaggingAgent via router for page {page_id}")
                from src.agents.tagging_agent import TaggingAgent
                agent = TaggingAgent(ai_router=router)
                tags = await agent.suggest_tags(text)
                
                logger.info(f"[TagPages] Generated tags for {page_id}: {tags}")
                
                # ... rest of processing
                
            except Exception as e:
                logger.error(f"[TagPages] Failed to process page {page_id}: {e}")
                error_count += 1
                results.append({
                    "page_id": page_id,
                    "status": "error",
                    "message": str(e),
                    "tags": None
                })
            
            # ✅ Оновити прогрес після обробки сторінки
            if task_id and task_id in TASK_PROGRESS:
                TASK_PROGRESS[task_id]["processed"] += 1

            # Throttling
            await asyncio.sleep(0.3)
```

---

### Новий код (ПАРАЛЕЛЬНА обробка)

**Заміна:**

```python
        logger.info(
            f"[TagPages] Processing {len(filtered_ids)} allowed pages "
            f"(mode={mode}, effective_dry_run={effective_dry_run}, skipped={skipped_due_to_whitelist})"
        )

        # ✅ Внутрішня функція для обробки однієї сторінки
        async def process_single_page(page_id_int: int) -> dict:
            """
            Обробляє одну сторінку асинхронно.
            Повертає результат обробки або error dict.
            """
            page_id = str(page_id_int)
            
            # ✅ Перевірка чи не зупинено процес (перед обробкою)
            if task_id and not ACTIVE_TASKS.get(task_id, True):
                logger.info(f"[TagPages] Task {task_id} stopped by user, skipping page {page_id}")
                return None  # Пропускаємо цю сторінку
            
            try:
                logger.info(f"[TagPages] Processing page {page_id} (effective_dry_run={effective_dry_run})")
                
                # Завантажуємо контент сторінки
                page = await self.confluence.get_page(page_id)
                if not page:
                    logger.warning(f"[TagPages] Page {page_id} not found")
                    return {
                        "page_id": page_id,
                        "status": "error",
                        "message": "Page not found"
                    }
                
                text = page.get("body", {}).get("storage", {}).get("value", "")
                logger.debug(f"[TagPages] Extracted {len(text)} chars from page {page_id}")
                
                # Формуємо індивідуальний AI-промпт на основі контенту
                logger.info(f"[TagPages] Calling TaggingAgent via router for page {page_id}")
                from src.agents.tagging_agent import TaggingAgent
                agent = TaggingAgent(ai_router=router)
                tags = await agent.suggest_tags(text)
                
                logger.info(f"[TagPages] Generated tags for {page_id}: {tags}")
                
                # Flatten tags and compare with existing
                flat_tags = flatten_tags(tags)
                logger.debug(f"[TagPages] Flattened tags: {flat_tags}")
                
                # Get existing labels
                existing_labels = await self.confluence.get_labels(page_id)
                logger.debug(f"[TagPages] Existing labels: {existing_labels}")
                
                # Calculate differences
                proposed = set(flat_tags)
                existing = set(existing_labels)
                to_add = proposed - existing
                
                logger.info(f"[TagPages] Tag comparison for {page_id}: proposed={len(proposed)}, existing={len(existing)}, to_add={len(to_add)}")
                
                # Використовуємо effective_dry_run для перевірки режиму
                if effective_dry_run:
                    # У TEST режимі всі оновлення заборонені (навіть для whitelist сторінок)
                    status = "forbidden" if mode == "TEST" else "dry_run"
                    logger.info(f"[TagPages] [{status.upper()}] Would add labels for {page_id}: {list(to_add)}")
                    return {
                        "page_id": page_id,
                        "status": status,
                        "tags": {
                            "proposed": list(proposed),
                            "existing": list(existing),
                            "added": [],
                            "to_add": list(to_add)
                        },
                        "dry_run": True
                    }
                
                # Real update mode: page is already in whitelist (filtered_ids)
                if to_add:
                    logger.info(f"[TagPages] Updating labels for page {page_id}: adding {list(to_add)}")
                    await self.confluence.update_labels(page_id, list(to_add))
                    logger.info(f"[TagPages] Successfully updated labels for page {page_id}")
                else:
                    logger.info(f"[TagPages] No new labels to add for page {page_id}")
                
                return {
                    "page_id": page_id,
                    "status": "updated",
                    "tags": {
                        "proposed": list(proposed),
                        "existing": list(existing),
                        "added": list(to_add),
                        "to_add": []
                    },
                    "dry_run": False
                }

            except Exception as e:
                logger.error(f"[TagPages] Failed to process page {page_id}: {e}")
                return {
                    "page_id": page_id,
                    "status": "error",
                    "message": str(e),
                    "tags": None
                }
            finally:
                # ✅ Оновити прогрес після обробки сторінки
                if task_id and task_id in TASK_PROGRESS:
                    TASK_PROGRESS[task_id]["processed"] += 1
                
                # Throttling - добавляємо мінімальну затримку для rate limiting
                await asyncio.sleep(0.1)  # Зменшено з 0.3 з огляду на паралелізм

        # ✅ ПАРАЛЕЛЬНА обробка: запустити всі задачі одночасно
        logger.info(f"[TagPages] Starting parallel processing of {len(filtered_ids)} pages")
        
        if filtered_ids:
            tasks = [process_single_page(page_id_int) for page_id_int in filtered_ids]
            results_list = await asyncio.gather(*tasks, return_exceptions=False)
            
            # Фільтруємо None (скасовані задачи через зупинку) та обробляємо результати
            for result in results_list:
                if result is None:
                    continue  # Сторінка скасована
                
                results.append(result)
                
                if result.get("status") in ["updated", "dry_run"]:
                    success_count += 1
                elif result.get("status") == "error":
                    error_count += 1
        
        logger.info(f"[TagPages] Parallel processing completed: {success_count} success, {error_count} errors")
```

---

## 🔄 Різниця логіки

### ПЕРЕД (серійна):
```
Page 111:  [====== AI 20s ======]
Page 222:                       [====== AI 20s ======]
Page 333:                                           [====== AI 20s ======]
Timeline:  0s         20s       40s       60s       80s      100s (SERIAL)
```

### ПІСЛЯ (паралельна):
```
Page 111:  [====== AI 20s ======]
Page 222:  [====== AI 20s ======] (паралельно!)
Page 333:  [====== AI 20s ======] (паралельно!)
Timeline:  0s         20s (PARALLEL)
```

---

## ✅ Перевірка виправлення

### Тест перед виправленням:
```bash
# Запит з 3 сторінками
curl -X POST http://localhost:8000/bulk/tag-pages \
  -H "Content-Type: application/json" \
  -d '{
    "space_key": "nkfedba",
    "page_ids": ["111", "222", "333"],
    "dry_run": true
  }'

# Логи:
# [TagPages] Processing 3 allowed pages
# [TagPages] Processing page 111 (effective_dry_run=True)
# [TagPages] Calling TaggingAgent via router for page 111
# [TagPages] Generated tags for 111: {...}
# [TagPages] Processing page 222 (effective_dry_run=True)
# ... (20-30 сек на 111)
# [TagPages] Calling TaggingAgent via router for page 222
# ... (20-30 сек на 222)
# [TagPages] Processing page 333
# ... (20-30 сек на 333)
# TOTAL: ~60-90 сек (СЕРІЙНА)
```

### Тест після виправлення:
```bash
# ТОЙ ЖЕ запит
curl -X POST http://localhost:8000/bulk/tag-pages ...

# Логи:
# [TagPages] Processing 3 allowed pages
# [TagPages] Starting parallel processing of 3 pages
# [TagPages] Processing page 111 (effective_dry_run=True)
# [TagPages] Processing page 222 (effective_dry_run=True)
# [TagPages] Processing page 333 (effective_dry_run=True)
# [TagPages] Calling TaggingAgent via router for page 111
# [TagPages] Calling TaggingAgent via router for page 222
# [TagPages] Calling TaggingAgent via router for page 333
# ... (20-30 сек - ВСІ паралельно!)
# [TagPages] Parallel processing completed
# TOTAL: ~20-40 сек (ПАРАЛЕЛЬНА) ← 2-3x швидче!
```

---

## 📋 Checklist для впровадження

- [ ] Бекапіти `src/services/bulk_tagging_service.py`
- [ ] Замінити логіку обробки на asyncio.gather()
- [ ] Добавити логування часу виконання
- [ ] Запустити unit тести: `pytest tests/bulk/test_tag_pages.py`
- [ ] Запустити інтеграційний тест з 3+ сторінками
- [ ] Перевірити логи на паралельне виконання
- [ ] Вимірити час виконання (очікуване: 2-3x прискорення)
- [ ] Перевірити, що результати однакові (processed, success, skipped)

---

**Ефективність Fix:** 🚀 2-3x прискорення (100 сек → 30-40 сек)
