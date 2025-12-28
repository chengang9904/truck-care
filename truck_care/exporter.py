from __future__ import annotations

import csv
from pathlib import Path

from .constants import VEHICLE_TYPE_TRACTOR, VEHICLE_TYPE_TRAILER
from .db import Database


def export_csv(db: Database, output_dir: Path | str) -> list[Path]:
    """导出所有数据到 CSV 文件"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    # 导出牵引车
    tractors_path = out_dir / "tractors.csv"
    with tractors_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "plate", "mileage", "note", "created_at"])
        for v in db.list_tractors():
            writer.writerow([v.id, v.plate, v.mileage, v.note, v.created_at])
    written.append(tractors_path)

    # 导出挂车
    trailers_path = out_dir / "trailers.csv"
    with trailers_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "plate", "note", "created_at"])
        for v in db.list_trailers():
            writer.writerow([v.id, v.plate, v.note, v.created_at])
    written.append(trailers_path)

    # 导出轮胎记录
    tire_events_path = out_dir / "tire_events.csv"
    with tire_events_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "vehicle_type", "vehicle_id", "vehicle_plate",
            "position", "change_date", "mileage", "brand", "model", "note", "created_at"
        ])
        
        # 牵引车轮胎记录
        for v in db.list_tractors():
            for e in db.list_tire_events(VEHICLE_TYPE_TRACTOR, v.id):
                writer.writerow([
                    e.id, "牵引车", e.vehicle_id, v.plate,
                    e.position, e.change_date, e.mileage, e.brand, e.model, e.note, e.created_at
                ])
        
        # 挂车轮胎记录
        for v in db.list_trailers():
            for e in db.list_tire_events(VEHICLE_TYPE_TRAILER, v.id):
                writer.writerow([
                    e.id, "挂车", e.vehicle_id, v.plate,
                    e.position, e.change_date, e.mileage, e.brand, e.model, e.note, e.created_at
                ])
    written.append(tire_events_path)

    # 导出保养记录
    maintenance_path = out_dir / "maintenance_records.csv"
    with maintenance_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "vehicle_type", "vehicle_id", "vehicle_plate",
            "record_type", "service_date", "mileage", "note", "created_at"
        ])
        
        # 牵引车保养记录
        for v in db.list_tractors():
            for r in db.list_maintenance_records(VEHICLE_TYPE_TRACTOR, v.id):
                writer.writerow([
                    r.id, "牵引车", r.vehicle_id, v.plate,
                    r.record_type, r.service_date, r.mileage, r.note, r.created_at
                ])
        
        # 挂车保养记录
        for v in db.list_trailers():
            for r in db.list_maintenance_records(VEHICLE_TYPE_TRAILER, v.id):
                writer.writerow([
                    r.id, "挂车", r.vehicle_id, v.plate,
                    r.record_type, r.service_date, r.mileage, r.note, r.created_at
                ])
    written.append(maintenance_path)

    return written
