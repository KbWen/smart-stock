import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from core.data import get_db_connection, get_history_context

# Preset strategies seeded on first run (AC4). Names describe rule WIDTH, never
# an outcome/return promise. "Balanced" is the suggested default for novices.
_PRESET_SUGGESTED_DEFAULT = "Balanced"
_PRESETS: list[dict[str, Any]] = [
    {
        "name": "Tight",
        "notes": "窄幅停利停損，快進快出",
        "params": {
            "target_gain": 0.08,
            "stop_loss": 0.04,
            "holding_days": 10,
            "commission_rate": 0.001425,
            "tax_rate": 0.003,
            "slippage_rate": 0.001,
            "days_ago": 30,
        },
    },
    {
        "name": "Balanced",
        "notes": "與 /api/backtest 預設一致的中間路線",
        "params": {
            "target_gain": 0.15,
            "stop_loss": 0.05,
            "holding_days": 20,
            "commission_rate": 0.001425,
            "tax_rate": 0.003,
            "slippage_rate": 0.001,
            "days_ago": 30,
        },
    },
    {
        "name": "Wide",
        "notes": "寬幅停利停損，長天期持有",
        "params": {
            "target_gain": 0.30,
            "stop_loss": 0.15,
            "holding_days": 60,
            "commission_rate": 0.001425,
            "tax_rate": 0.003,
            "slippage_rate": 0.001,
            "days_ago": 90,
        },
    },
]


class StrategyNameConflictError(Exception):
    """Raised when a create/rename would violate the unique-name DB constraint."""


class StrategyNotFoundError(Exception):
    """Raised when a strategy id does not exist."""


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "params": json.loads(row["params"]),
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrategyRepository:
    def list_all(self) -> list[dict[str, Any]]:
        conn = get_db_connection()
        try:
            rows = conn.execute(
                "SELECT id, name, params, notes, created_at, updated_at FROM strategies ORDER BY id ASC"
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def get(self, strategy_id: int) -> Optional[dict[str, Any]]:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT id, name, params, notes, created_at, updated_at FROM strategies WHERE id = ?",
                (strategy_id,),
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    def create(self, name: str, params: dict[str, Any], notes: Optional[str]) -> dict[str, Any]:
        conn = get_db_connection()
        try:
            now = _now()
            cur = conn.execute(
                "INSERT INTO strategies (name, params, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name, json.dumps(params), notes, now, now),
            )
            conn.commit()
            new_id = cur.lastrowid
        except sqlite3.IntegrityError as e:
            raise StrategyNameConflictError(str(e)) from e
        finally:
            conn.close()
        return self.get(new_id)

    def update(
        self,
        strategy_id: int,
        name: Optional[str],
        params: Optional[dict[str, Any]],
        notes: Optional[str],
        notes_provided: bool,
    ) -> Optional[dict[str, Any]]:
        """Partial update. Caller is responsible for merging/re-validating params
        BEFORE calling this — this method only persists already-validated data."""
        conn = get_db_connection()
        try:
            existing = conn.execute(
                "SELECT id FROM strategies WHERE id = ?", (strategy_id,)
            ).fetchone()
            if not existing:
                return None

            fields = []
            values: list[Any] = []
            if name is not None:
                fields.append("name = ?")
                values.append(name)
            if params is not None:
                fields.append("params = ?")
                values.append(json.dumps(params))
            if notes_provided:
                fields.append("notes = ?")
                values.append(notes)
            fields.append("updated_at = ?")
            values.append(_now())
            values.append(strategy_id)

            try:
                conn.execute(
                    f"UPDATE strategies SET {', '.join(fields)} WHERE id = ?",
                    values,
                )
                conn.commit()
            except sqlite3.IntegrityError as e:
                raise StrategyNameConflictError(str(e)) from e
        finally:
            conn.close()
        return self.get(strategy_id)

    def delete(self, strategy_id: int) -> bool:
        conn = get_db_connection()
        try:
            cur = conn.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get_history_context(self) -> Optional[dict[str, Any]]:
        return get_history_context()

    def seed_presets(self) -> dict[str, Any]:
        """Idempotently seed 2-3 preset strategies, keyed on unique name.

        Never raises on a duplicate — INSERT OR IGNORE keyed on the UNIQUE name
        constraint. Returns which preset name is the suggested default so callers
        never have to hardcode/guess it in two places.
        """
        conn = get_db_connection()
        inserted = 0
        try:
            now = _now()
            for preset in _PRESETS:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO strategies (name, params, notes, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (preset["name"], json.dumps(preset["params"]), preset["notes"], now, now),
                )
                inserted += cur.rowcount
            conn.commit()
        finally:
            conn.close()
        return {"inserted": inserted, "suggested_default": _PRESET_SUGGESTED_DEFAULT}
