from typing import Any

from backend.routes.sync import get_sync_status_snapshot
from core.data import get_db_connection


class SystemRepository:
    def get_sync_status(self) -> dict[str, Any]:
        return get_sync_status_snapshot()

    def get_sync_epoch(self) -> int:
        return int(self.get_sync_status().get("sync_epoch", 0))

    def check_db_health(self) -> tuple[str, str]:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return "ok", "connected"
        except Exception as e:
            return "error", str(e)
