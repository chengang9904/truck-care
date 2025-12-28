from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from .constants import (
    TRACTOR_TIRE_POSITIONS,
    TRAILER_TIRE_POSITIONS,
    VEHICLE_TYPE_TRACTOR,
    VEHICLE_TYPE_TRAILER,
)


@dataclass(frozen=True)
class Tractor:
    """牵引车"""
    id: int
    plate: str
    mileage: int
    note: str
    created_at: str


@dataclass(frozen=True)
class Trailer:
    """挂车"""
    id: int
    plate: str
    note: str
    created_at: str


@dataclass(frozen=True)
class TireEvent:
    """轮胎更换记录"""
    id: int
    vehicle_type: str  # 'tractor' or 'trailer'
    vehicle_id: int
    position: str
    change_date: str
    mileage: int
    brand: str
    model: str
    note: str
    created_at: str


@dataclass(frozen=True)
class MaintenanceRecord:
    """保养记录"""
    id: int
    vehicle_type: str  # 'tractor' or 'trailer'
    vehicle_id: int
    record_type: str
    service_date: str
    mileage: int
    note: str
    created_at: str


# 兼容旧代码的别名
Vehicle = Tractor


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def default_db_path() -> Path:
    base_dir = Path.home() / ".truck-care"
    _ensure_dir(base_dir)
    return base_dir / "truck_care.sqlite3"


def _to_iso(d: date | str) -> str:
    if isinstance(d, str):
        date.fromisoformat(d)
        return d
    return d.isoformat()


def _get_valid_positions(vehicle_type: str) -> tuple[str, ...]:
    """根据车辆类型返回有效的轮胎位置"""
    if vehicle_type == VEHICLE_TYPE_TRACTOR:
        return TRACTOR_TIRE_POSITIONS
    elif vehicle_type == VEHICLE_TYPE_TRAILER:
        return TRAILER_TIRE_POSITIONS
    else:
        raise ValueError(f"未知车辆类型: {vehicle_type}")


class Database:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else default_db_path()
        _ensure_dir(self.db_path.parent)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")

    def close(self) -> None:
        self._conn.close()

    def init_db(self) -> None:
        tractor_positions_sql = ",".join([f"'{p}'" for p in TRACTOR_TIRE_POSITIONS])
        trailer_positions_sql = ",".join([f"'{p}'" for p in TRAILER_TIRE_POSITIONS])
        all_positions_sql = ",".join([f"'{p}'" for p in TRACTOR_TIRE_POSITIONS + TRAILER_TIRE_POSITIONS])
        
        with self._conn:
            self._conn.executescript(
                f"""
                -- 牵引车表
                CREATE TABLE IF NOT EXISTS tractors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL UNIQUE,
                    mileage INTEGER NOT NULL CHECK(mileage >= 0),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- 挂车表
                CREATE TABLE IF NOT EXISTS trailers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL UNIQUE,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- 轮胎更换记录表（支持牵引车和挂车）
                CREATE TABLE IF NOT EXISTS tire_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('tractor', 'trailer')),
                    vehicle_id INTEGER NOT NULL,
                    position TEXT NOT NULL CHECK(position IN ({all_positions_sql})),
                    change_date TEXT NOT NULL,
                    mileage INTEGER NOT NULL CHECK(mileage >= 0),
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_tire_events_vehicle
                    ON tire_events(vehicle_type, vehicle_id, position, change_date);

                -- 保养记录表（支持牵引车和挂车）
                CREATE TABLE IF NOT EXISTS maintenance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('tractor', 'trailer')),
                    vehicle_id INTEGER NOT NULL,
                    record_type TEXT NOT NULL,
                    service_date TEXT NOT NULL,
                    mileage INTEGER NOT NULL CHECK(mileage >= 0),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle
                    ON maintenance_records(vehicle_type, vehicle_id, service_date);
                """
            )

    # ==================== 牵引车 CRUD ====================

    def list_tractors(self) -> list[Tractor]:
        rows = self._conn.execute(
            "SELECT id, plate, mileage, note, created_at FROM tractors ORDER BY plate"
        ).fetchall()
        return [Tractor(**dict(r)) for r in rows]

    def get_tractor(self, tractor_id: int) -> Tractor | None:
        row = self._conn.execute(
            "SELECT id, plate, mileage, note, created_at FROM tractors WHERE id = ?",
            (tractor_id,),
        ).fetchone()
        return Tractor(**dict(row)) if row else None

    def create_tractor(self, plate: str, mileage: int, note: str = "") -> int:
        plate = plate.strip()
        if not plate:
            raise ValueError("车牌号不能为空")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO tractors(plate, mileage, note) VALUES (?, ?, ?)",
                (plate, mileage, note or ""),
            )
        return int(cur.lastrowid)

    def update_tractor(self, tractor_id: int, plate: str, mileage: int, note: str = "") -> None:
        plate = plate.strip()
        if not plate:
            raise ValueError("车牌号不能为空")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        with self._conn:
            self._conn.execute(
                "UPDATE tractors SET plate = ?, mileage = ?, note = ? WHERE id = ?",
                (plate, mileage, note or "", tractor_id),
            )

    def delete_tractor(self, tractor_id: int) -> None:
        with self._conn:
            # 手动删除关联记录（因为没有外键约束到多表）
            self._conn.execute(
                "DELETE FROM tire_events WHERE vehicle_type = ? AND vehicle_id = ?",
                (VEHICLE_TYPE_TRACTOR, tractor_id),
            )
            self._conn.execute(
                "DELETE FROM maintenance_records WHERE vehicle_type = ? AND vehicle_id = ?",
                (VEHICLE_TYPE_TRACTOR, tractor_id),
            )
            self._conn.execute("DELETE FROM tractors WHERE id = ?", (tractor_id,))

    # ==================== 挂车 CRUD ====================

    def list_trailers(self) -> list[Trailer]:
        rows = self._conn.execute(
            "SELECT id, plate, note, created_at FROM trailers ORDER BY plate"
        ).fetchall()
        return [Trailer(**dict(r)) for r in rows]

    def get_trailer(self, trailer_id: int) -> Trailer | None:
        row = self._conn.execute(
            "SELECT id, plate, note, created_at FROM trailers WHERE id = ?",
            (trailer_id,),
        ).fetchone()
        return Trailer(**dict(row)) if row else None

    def create_trailer(self, plate: str, note: str = "") -> int:
        plate = plate.strip()
        if not plate:
            raise ValueError("车牌号不能为空")
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO trailers(plate, note) VALUES (?, ?)",
                (plate, note or ""),
            )
        return int(cur.lastrowid)

    def update_trailer(self, trailer_id: int, plate: str, note: str = "") -> None:
        plate = plate.strip()
        if not plate:
            raise ValueError("车牌号不能为空")
        with self._conn:
            self._conn.execute(
                "UPDATE trailers SET plate = ?, note = ? WHERE id = ?",
                (plate, note or "", trailer_id),
            )

    def delete_trailer(self, trailer_id: int) -> None:
        with self._conn:
            # 手动删除关联记录
            self._conn.execute(
                "DELETE FROM tire_events WHERE vehicle_type = ? AND vehicle_id = ?",
                (VEHICLE_TYPE_TRAILER, trailer_id),
            )
            self._conn.execute(
                "DELETE FROM maintenance_records WHERE vehicle_type = ? AND vehicle_id = ?",
                (VEHICLE_TYPE_TRAILER, trailer_id),
            )
            self._conn.execute("DELETE FROM trailers WHERE id = ?", (trailer_id,))

    # ==================== 轮胎事件 ====================

    def list_tire_events(
        self,
        vehicle_type: str,
        vehicle_id: int,
        position: str | None = None,
    ) -> list[TireEvent]:
        valid_positions = _get_valid_positions(vehicle_type)
        params: list[object] = [vehicle_type, vehicle_id]
        where = "vehicle_type = ? AND vehicle_id = ?"
        
        if position is not None:
            if position not in valid_positions:
                raise ValueError(f"轮胎位置不合法: {position}，有效位置: {valid_positions}")
            where += " AND position = ?"
            params.append(position)

        rows = self._conn.execute(
            f"""
            SELECT id, vehicle_type, vehicle_id, position, change_date, mileage, brand, model, note, created_at
            FROM tire_events
            WHERE {where}
            ORDER BY change_date DESC, id DESC
            """,
            tuple(params),
        ).fetchall()
        return [TireEvent(**dict(r)) for r in rows]

    def create_tire_event(
        self,
        vehicle_type: str,
        vehicle_id: int,
        position: str,
        change_date: date | str,
        mileage: int,
        brand: str = "",
        model: str = "",
        note: str = "",
    ) -> int:
        valid_positions = _get_valid_positions(vehicle_type)
        if position not in valid_positions:
            raise ValueError(f"轮胎位置不合法: {position}，有效位置: {valid_positions}")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        change_date_iso = _to_iso(change_date)
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO tire_events(vehicle_type, vehicle_id, position, change_date, mileage, brand, model, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (vehicle_type, vehicle_id, position, change_date_iso, mileage, brand or "", model or "", note or ""),
            )
        return int(cur.lastrowid)

    def update_tire_event(
        self,
        event_id: int,
        position: str,
        change_date: date | str,
        mileage: int,
        brand: str = "",
        model: str = "",
        note: str = "",
    ) -> None:
        # 获取现有记录的 vehicle_type 来验证 position
        row = self._conn.execute(
            "SELECT vehicle_type FROM tire_events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise ValueError("记录不存在")
        
        vehicle_type = row["vehicle_type"]
        valid_positions = _get_valid_positions(vehicle_type)
        if position not in valid_positions:
            raise ValueError(f"轮胎位置不合法: {position}，有效位置: {valid_positions}")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        change_date_iso = _to_iso(change_date)
        with self._conn:
            self._conn.execute(
                """
                UPDATE tire_events
                SET position = ?, change_date = ?, mileage = ?, brand = ?, model = ?, note = ?
                WHERE id = ?
                """,
                (position, change_date_iso, mileage, brand or "", model or "", note or "", event_id),
            )

    def delete_tire_event(self, event_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM tire_events WHERE id = ?", (event_id,))

    def current_tires(
        self,
        vehicle_type: str,
        vehicle_id: int,
    ) -> dict[str, TireEvent | None]:
        """获取指定车辆每个轮胎位置的最新记录"""
        valid_positions = _get_valid_positions(vehicle_type)
        
        rows = self._conn.execute(
            """
            SELECT t.*
            FROM tire_events t
            WHERE t.vehicle_type = ? AND t.vehicle_id = ?
              AND t.id = (
                SELECT t2.id
                FROM tire_events t2
                WHERE t2.vehicle_type = t.vehicle_type
                  AND t2.vehicle_id = t.vehicle_id
                  AND t2.position = t.position
                ORDER BY t2.change_date DESC, t2.id DESC
                LIMIT 1
              )
            """,
            (vehicle_type, vehicle_id),
        ).fetchall()

        latest_by_pos = {r["position"]: TireEvent(**dict(r)) for r in rows}
        return {pos: latest_by_pos.get(pos) for pos in valid_positions}

    # ==================== 保养记录 ====================

    def list_maintenance_records(
        self,
        vehicle_type: str,
        vehicle_id: int,
    ) -> list[MaintenanceRecord]:
        rows = self._conn.execute(
            """
            SELECT id, vehicle_type, vehicle_id, record_type, service_date, mileage, note, created_at
            FROM maintenance_records
            WHERE vehicle_type = ? AND vehicle_id = ?
            ORDER BY service_date DESC, id DESC
            """,
            (vehicle_type, vehicle_id),
        ).fetchall()
        return [MaintenanceRecord(**dict(r)) for r in rows]

    def create_maintenance_record(
        self,
        vehicle_type: str,
        vehicle_id: int,
        record_type: str,
        service_date: date | str,
        mileage: int,
        note: str = "",
    ) -> int:
        record_type = record_type.strip()
        if not record_type:
            raise ValueError("维护类型不能为空")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        service_date_iso = _to_iso(service_date)
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO maintenance_records(vehicle_type, vehicle_id, record_type, service_date, mileage, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (vehicle_type, vehicle_id, record_type, service_date_iso, mileage, note or ""),
            )
        return int(cur.lastrowid)

    def update_maintenance_record(
        self,
        record_id: int,
        record_type: str,
        service_date: date | str,
        mileage: int,
        note: str = "",
    ) -> None:
        record_type = record_type.strip()
        if not record_type:
            raise ValueError("维护类型不能为空")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        service_date_iso = _to_iso(service_date)
        with self._conn:
            self._conn.execute(
                """
                UPDATE maintenance_records
                SET record_type = ?, service_date = ?, mileage = ?, note = ?
                WHERE id = ?
                """,
                (record_type, service_date_iso, mileage, note or "", record_id),
            )

    def delete_maintenance_record(self, record_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM maintenance_records WHERE id = ?", (record_id,))
