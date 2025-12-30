"""
API роутер для bulk-тегування простору Confluence.

POST /bulk/tag-space/{space_key}
POST /bulk/tag-space/stop/{task_id}
"""

from typing import Optional
from fastapi import APIRouter, Path, Query, BackgroundTasks
from src.services.bulk_tagging_service import BulkTaggingService
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bulk", tags=["bulk"])


@router.post("/tag-space/stop/{task_id}", summary="Stop tag-space operation")
async def stop_tag_space(
    task_id: str = Path(..., description="Task ID to stop")
):
    """
    🛑 Stop a running tag-space task.
    
    This endpoint signals the running task to stop.
    The task will terminate on its next iteration.
    
    Args:
        task_id: ID задачі, отриманий з start endpoint
        
    Returns:
        {
            "status": "stopping" | "not_found",
            "task_id": str,
            "message": str
        }
    """
    from src.services.bulk_tagging_service import ACTIVE_TASKS
    
    logger.info(f"POST /bulk/tag-space/stop/{task_id}")
    
    if task_id in ACTIVE_TASKS:
        ACTIVE_TASKS[task_id] = False
        logger.info(f"Task {task_id} marked for stopping")
        return {
            "status": "stopping",
            "task_id": task_id,
            "message": "Task will stop on next iteration."
        }
    else:
        logger.warning(f"Task {task_id} not found in active tasks")
        return {
            "status": "not_found",
            "task_id": task_id,
            "message": "Task not found or already completed."
        }


@router.get("/tag-space/status/{task_id}", summary="Check tag-space status")
async def tag_space_status(
    task_id: str = Path(..., description="Task ID to check")
):
    """
    🔍 Check status of a running tag-space task with progress information.
    
    Returns current status, progress (total/processed), and timestamps.
    
    Args:
        task_id: ID задачі
        
    Returns:
        {
            "task_id": str,
            "running": bool,
            "total": int,
            "processed": int,
            "start_timestamp": str,
            "finish_timestamp": str | None,
            "message": str
        }
    """
    from src.services.bulk_tagging_service import ACTIVE_TASKS, TASK_PROGRESS, TASK_TIMESTAMPS
    
    logger.info(f"GET /bulk/tag-space/status/{task_id}")
    
    if task_id not in ACTIVE_TASKS:
        return {
            "task_id": task_id,
            "running": False,
            "message": "Task not found or already completed."
        }
    
    is_running = ACTIVE_TASKS[task_id]
    progress = TASK_PROGRESS.get(task_id, {})
    timestamps = TASK_TIMESTAMPS.get(task_id, {})
    
    return {
        "task_id": task_id,
        "running": is_running,
        "total": progress.get("total"),
        "processed": progress.get("processed"),
        "start_timestamp": timestamps.get("start"),
        "finish_timestamp": timestamps.get("finish"),
        "message": "Task is running." if is_running else "Task is stopping."
    }


@router.get("/tag-space/result/{task_id}", summary="Get result of completed tag-space task")
async def tag_space_result(
    task_id: str = Path(..., description="Task ID to retrieve result")
):
    """
    📦 Get result of a completed tag-space task.
    
    Returns full tagging result if task is completed.
    If task is still running, returns status.
    If task not found, returns error.
    
    Args:
        task_id: ID задачі для отримання результату
        
    Returns:
        Full result dict if completed, or status message
    """
    from src.services.bulk_tagging_service import RESULTS_REGISTRY, ACTIVE_TASKS
    
    logger.info(f"GET /bulk/tag-space/result/{task_id}")
    
    # Перевірка чи є результат
    if task_id in RESULTS_REGISTRY:
        logger.info(f"Returning result for task {task_id}")
        return RESULTS_REGISTRY[task_id]
    
    # Перевірка чи ще виконується
    if task_id in ACTIVE_TASKS:
        logger.info(f"Task {task_id} is still running")
        return {
            "task_id": task_id,
            "status": "running",
            "message": "Task is still in progress. Try again later."
        }
    
    # Не знайдено
    logger.warning(f"Task {task_id} not found in results or active tasks")
    return {
        "task_id": task_id,
        "status": "not_found",
        "message": "Task not found or already purged."
    }


@router.get("/tag-space/list-tasks", summary="List all active and completed tag-space tasks")
async def list_tag_space_tasks():
    """
    📋 List all tasks: active, running, completed.
    
    Returns a list of all known tasks with their current status,
    progress information, and timestamps.
    
    Returns:
        {"tasks": [...]}
    """
    from src.services.bulk_tagging_service import ACTIVE_TASKS, RESULTS_REGISTRY, TASK_PROGRESS, TASK_TIMESTAMPS
    
    logger.info("GET /bulk/tag-space/list-tasks")
    
    tasks = []
    
    # Active tasks
    for task_id in ACTIVE_TASKS.keys():
        tasks.append({
            "task_id": task_id,
            "status": "running",
            "progress": TASK_PROGRESS.get(task_id),
            "timestamps": TASK_TIMESTAMPS.get(task_id)
        })
    
    # Completed tasks
    for task_id, result in RESULTS_REGISTRY.items():
        tasks.append({
            "task_id": task_id,
            "status": "completed",
            "progress": None,
            "timestamps": TASK_TIMESTAMPS.get(task_id),
            "result_available": True
        })
    
    # ✅ Error tasks (є в TASK_TIMESTAMPS, але не в RESULTS_REGISTRY і не в ACTIVE_TASKS)
    all_completed_or_active = set(RESULTS_REGISTRY.keys()) | set(ACTIVE_TASKS.keys())
    for task_id in TASK_TIMESTAMPS.keys():
        if task_id not in all_completed_or_active:
            tasks.append({
                "task_id": task_id,
                "status": "error",
                "progress": None,
                "timestamps": TASK_TIMESTAMPS.get(task_id),
                "result_available": False
            })
    
    return {"tasks": tasks}


@router.post("/tag-space/{space_key}", summary="Start tag-space operation")
async def bulk_tag_space(
    space_key: str = Path(..., description="Confluence space key"),
    dry_run: Optional[bool] = Query(
        default=None,
        description="Override dry-run mode. If None, defaults to True for safety"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Bulk-тегування всіх сторінок у просторі Confluence з уніфікованою архітектурою.
    
    **Архітектура:** Використовує BulkTaggingService з WhitelistManager.
    
    **Режимна матриця (уніфікована):**
    - TEST: завжди dry_run=True (forced), тільки whitelist сторінки
    - SAFE_TEST: dry_run керується параметром, тільки whitelist сторінки
    - PROD: dry_run керується параметром, тільки whitelist сторінки
    
    **Whitelist:**
    - Завжди застосовується (у всіх режимах: TEST, SAFE_TEST, PROD)
    - Конфігурація: src/core/whitelist/whitelist_config.json
    - Управління: WhitelistManager
    - Якщо whitelist порожній → повертається помилка 403
    
    **Логіка:**
    1. Завантажує whitelist з whitelist_config.json для space_key
    2. Отримує всі сторінки простору
    3. Фільтрує сторінки через whitelist (allowed_ids)
    4. Викликає BulkTaggingService.tag_pages() для відфільтрованих сторінок
    5. Для кожної сторінки:
       - Отримує контент
       - Викликає TaggingAgent для AI-аналізу
       - Формує structured tags (proposed, existing, added)
       - Якщо не dry_run → додає теги в Confluence
    
    **Підтримка зупинки та моніторингу:**
    - Повертає task_id для керування процесом
    
    **Після запуску:**
    - Використовуй `/bulk/tag-space/status/{task_id}` для перевірки статусу
    - Використовуй `/bulk/tag-space/result/{task_id}` для отримання результату
    - Використовуй `/bulk/tag-space/stop/{task_id}` для зупинки процесу
    
    **Args:**
        space_key: Ключ простору Confluence
        dry_run: Режим симуляції (None = default True)
        
    **Returns:**
        {
            "task_id": str,                # ID задачі для зупинки
            "total": int,                  # Всього сторінок у просторі
            "processed": int,              # Оброблено (після whitelist)
            "success": int,                # Успішно оброблено
            "errors": int,                 # Помилки
            "skipped_by_whitelist": int,   # Пропущено через whitelist
            "duplicates_removed": int,     # Видалено дублікатів
            "dry_run": bool,               # Чи була симуляція
            "mode": str,                   # Режим (TEST/SAFE_TEST/PROD)
            "whitelist_enabled": bool,     # Чи був whitelist активний
            "details": [                   # Деталі по кожній сторінці
                {
                    "page_id": str,
                    "title": str,
                    "status": "updated" | "dry_run" | "error",
                    "tags": {
                        "proposed": list[str],  # AI-згенеровані теги
                        "existing": list[str],  # Існуючі теги
                        "added": list[str],     # Реально додані (у prod)
                        "to_add": list[str]     # Буде додано (у dry-run)
                    },
                    "dry_run": bool
                }
            ]
        }
    
    **Example:**
        ```bash
        # Dry-run (симуляція)
        curl -X POST "http://localhost:8000/bulk/tag-space/nkfedba?dry_run=true"
        
        # Реальні зміни (тільки whitelist сторінки)
        curl -X POST "http://localhost:8000/bulk/tag-space/nkfedba?dry_run=false"
        
        # Зупинити процес
        curl -X POST "http://localhost:8000/bulk/tag-space/stop/{task_id}"
        ```
    """
    logger.info(f"POST /bulk/tag-space/{space_key}: dry_run={dry_run} (background mode)")
    
    # ✅ Валідація: space_key не повинен бути числом (page_id)
    if space_key.isdigit():
        logger.error(f"Invalid space_key: {space_key} appears to be a page_id, not a space_key")
        return {
            "status": "error",
            "message": f"Invalid parameter: '{space_key}' appears to be a page_id. Please provide a space_key (e.g., 'nkfedba', 'euheals'). Use /pages/{{page_id}}/auto-tag for single page tagging.",
            "task_id": None,
            "total": 0,
            "processed": 0,
            "success": 0,
            "errors": 1,
            "hint": "Available space_keys in whitelist_config.json: nkfedba, euheals"
        }

    service = BulkTaggingService()
    task_id = service.create_task_id()

    background_tasks.add_task(
        service.tag_space,
        space_key=space_key,
        dry_run=dry_run,
        task_id=task_id
    )

    return {
        "task_id": task_id,
        "status": "started",
        "stop_endpoint": f"/bulk/tag-space/stop/{task_id}",
        "status_endpoint": f"/bulk/tag-space/status/{task_id}",
        "instructions": "Use stop_endpoint to stop the process, status_endpoint to check progress."
    }
