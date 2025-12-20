from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Literal, Optional

from .constants import TIRE_POSITIONS


@dataclass(frozen=True)
class Vehicle:
    id: int
    plate: str
    mileage: int
    note: str
    created_at: str


@dataclass(frozen=True)
class TireEvent:
    id: int
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
    id: int
    vehicle_id: int
    record_type: str
    service_date: str
    mileage: int
    note: str
    created_at: str


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
        positions_sql = ",".join([f"'{p}'" for p in TIRE_POSITIONS])
        with self._conn:
            self._conn.executescript(
                f"""
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL UNIQUE,
                    mileage INTEGER NOT NULL CHECK(mileage >= 0),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS tire_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    position TEXT NOT NULL CHECK(position IN ({positions_sql})),
                    change_date TEXT NOT NULL,
                    mileage INTEGER NOT NULL CHECK(mileage >= 0),
                    brand TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tire_events_vehicle_pos_date
                    ON tire_events(vehicle_id, position, change_date);

                CREATE TABLE IF NOT EXISTS maintenance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    record_type TEXT NOT NULL,
                    service_date TEXT NOT NULL,
                    mileage INTEGER NOT NULL CHECK(mileage >= 0),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle_date
                    ON maintenance_records(vehicle_id, service_date);
                """
            )

    def list_vehicles(self) -> list[Vehicle]:
        rows = self._conn.execute(
            "SELECT id, plate, mileage, note, created_at FROM vehicles ORDER BY plate"
        ).fetchall()
        return [Vehicle(**dict(r)) for r in rows]

    def get_vehicle(self, vehicle_id: int) -> Vehicle | None:
        row = self._conn.execute(
            "SELECT id, plate, mileage, note, created_at FROM vehicles WHERE id = ?",
            (vehicle_id,),
        ).fetchone()
        return Vehicle(**dict(row)) if row else None

    def create_vehicle(self, plate: str, mileage: int, note: str = "") -> int:
        plate = plate.strip()
        if not plate:
            raise ValueError("车牌号不能为空")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO vehicles(plate, mileage, note) VALUES (?, ?, ?)",
                (plate, mileage, note or ""),
            )
        return int(cur.lastrowid)

    def update_vehicle(self, vehicle_id: int, plate: str, mileage: int, note: str = "") -> None:
        plate = plate.strip()
        if not plate:
            raise ValueError("车牌号不能为空")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        with self._conn:
            self._conn.execute(
                "UPDATE vehicles SET plate = ?, mileage = ?, note = ? WHERE id = ?",
                (plate, mileage, note or "", vehicle_id),
            )

    def delete_vehicle(self, vehicle_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))

    def list_tire_events(self, vehicle_id: int, position: str | None = None) -> list[TireEvent]:
        params: list[object] = [vehicle_id]
        where = "vehicle_id = ?"
        if position is not None:
            if position not in TIRE_POSITIONS:
                raise ValueError("轮胎位置不合法")
            where += " AND position = ?"
            params.append(position)

        rows = self._conn.execute(
            f"""
            SELECT id, vehicle_id, position, change_date, mileage, brand, model, note, created_at
            FROM tire_events
            WHERE {where}
            ORDER BY change_date DESC, id DESC
            """,
            tuple(params),
        ).fetchall()
        return [TireEvent(**dict(r)) for r in rows]

    def create_tire_event(
        self,
        vehicle_id: int,
        position: str,
        change_date: date | str,
        mileage: int,
        brand: str = "",
        model: str = "",
        note: str = "",
    ) -> int:
        if position not in TIRE_POSITIONS:
            raise ValueError("轮胎位置不合法")
        if mileage < 0:
            raise ValueError("里程数不能为负数")
        change_date_iso = _to_iso(change_date)
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO tire_events(vehicle_id, position, change_date, mileage, brand, model, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (vehicle_id, position, change_date_iso, mileage, brand or "", model or "", note or ""),
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
        if position not in TIRE_POSITIONS:
            raise ValueError("轮胎位置不合法")
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

    def list_maintenance_records(self, vehicle_id: int) -> list[MaintenanceRecord]:
        rows = self._conn.execute(
            """
            SELECT id, vehicle_id, record_type, service_date, mileage, note, created_at
            FROM maintenance_records
            WHERE vehicle_id = ?
            ORDER BY service_date DESC, id DESC
            """,
            (vehicle_id,),
        ).fetchall()
        return [MaintenanceRecord(**dict(r)) for r in rows]

    def create_maintenance_record(
        self,
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
                INSERT INTO maintenance_records(vehicle_id, record_type, service_date, mileage, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (vehicle_id, record_type, service_date_iso, mileage, note or ""),
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

    def current_tires(self, vehicle_id: int) -> dict[str, TireEvent | None]:
        rows = self._conn.execute(
            """
            SELECT t.*
            FROM tire_events t
            WHERE t.vehicle_id = ?
              AND t.id = (
                SELECT t2.id
                FROM tire_events t2
                WHERE t2.vehicle_id = t.vehicle_id
                  AND t2.position = t.position
                ORDER BY t2.change_date DESC, t2.id DESC
                LIMIT 1
              )
            """,
            (vehicle_id,),
        ).fetchall()

        latest_by_pos = {r["position"]: TireEvent(**dict(r)) for r in rows}
        return {pos: latest_by_pos.get(pos) for pos in TIRE_POSITIONS}
