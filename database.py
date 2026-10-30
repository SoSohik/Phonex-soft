import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

DEFAULT_DB_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "inventory.db"

RARITY_TIERS = {
    "secret": 1,
    "mythic": 2, "mythical": 2,
    "legendary": 3,
    "epic": 4,
    "rare": 5,
    "unusual": 6,
    "common": 7
}


def get_rarity_tier(raw_rarity: str) -> int:
    if not raw_rarity:
        return 99
    clean = raw_rarity.strip().lower()
    for key, val in RARITY_TIERS.items():
        if key in clean:
            return val
    return 99


class InventoryDB:
    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_name TEXT NOT NULL,
                        rarity TEXT NOT NULL,
                        rarity_tier INTEGER NOT NULL DEFAULT 99,
                        price REAL NOT NULL,
                        image_path TEXT,
                        raw_message TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                cursor.execute("PRAGMA table_info(inventory)")
                cols = [col[1] for col in cursor.fetchall()]
                if "rarity_tier" not in cols:
                    cursor.execute("ALTER TABLE inventory ADD COLUMN rarity_tier INTEGER NOT NULL DEFAULT 99")

                cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_created ON inventory(created_at DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_price ON inventory(price DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_tier ON inventory(rarity_tier ASC)")
                conn.commit()

    def add_drop(
        self,
        device_name: str,
        rarity: str,
        price: float,
        image_path: Optional[str] = None,
        raw_message: Optional[str] = None,
        created_at: Optional[str] = None
    ) -> int:
        if created_at is None:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tier = get_rarity_tier(rarity)

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO inventory (device_name, rarity, rarity_tier, price, image_path, raw_message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    device_name.strip(),
                    rarity.strip(),
                    tier,
                    float(price),
                    image_path or "",
                    raw_message or "",
                    created_at
                ))
                conn.commit()
                return cursor.lastrowid

    def get_inventory(self, sort_by: str = "newest") -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if sort_by == "highest_price":
                    order_clause = "ORDER BY price DESC, id DESC"
                elif sort_by == "rarity":
                    order_clause = "ORDER BY rarity_tier ASC, price DESC, id DESC"
                else:
                    order_clause = "ORDER BY id DESC"

                query = f"SELECT * FROM inventory {order_clause}"
                cursor.execute(query)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

    def get_latest_drop(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM inventory ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), COALESCE(SUM(price), 0.0) FROM inventory")
                count, total_sum = cursor.fetchone()

                cursor.execute("SELECT rarity, COUNT(*) FROM inventory GROUP BY rarity")
                rarity_rows = cursor.fetchall()
                rarity_counts = {row[0]: row[1] for row in rarity_rows}

                return {
                    "total_count": int(count or 0),
                    "total_price": float(total_sum or 0.0),
                    "rarity_counts": rarity_counts
                }

    def delete_drop(self, drop_id: int) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM inventory WHERE id = ?", (drop_id,))
                conn.commit()
                return cursor.rowcount > 0

    def delete_by_device_name(self, device_name: str) -> int:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM inventory WHERE device_name = ?", (device_name.strip(),))
                conn.commit()
                return cursor.rowcount

    def clear_all(self):
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM inventory")
                conn.commit()
