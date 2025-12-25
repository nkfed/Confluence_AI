import json
import os
from datetime import datetime
from pathlib import Path
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

class TaggingAuditService:
    AUDIT_FILE = Path("data/tagging_audit.jsonl")

    @staticmethod
    def log_change(page_id, old_labels, new_labels, to_add, to_remove, dry_run, status):
        record = {
            "page_id": str(page_id),
            "timestamp": datetime.now().isoformat(),
            "old_labels": list(old_labels),
            "new_labels": list(new_labels),
            "added": list(to_add),
            "removed": list(to_remove),
            "dry_run": bool(dry_run),
            "status": status
        }
        
        TaggingAuditService.save_record(record)
        logger.info(f"[Audit] Page {page_id}: added={to_add}, removed={to_remove}, dry_run={dry_run}, status={status}")

    @staticmethod
    def save_record(record):
        # Переконуємось, що директорія існує
        TaggingAuditService.AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(TaggingAuditService.AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def get_history(page_id: str):
        """
        Повертає список записів аудиту для конкретної сторінки.
        """
        if not TaggingAuditService.AUDIT_FILE.exists():
            return []
            
        history = []
        with open(TaggingAuditService.AUDIT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    if record.get("page_id") == str(page_id):
                        history.append(record)
                except Exception:
                    continue
        return history
