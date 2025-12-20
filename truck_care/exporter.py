from __future__ import annotations

import csv
from pathlib import Path

from .db import Database


def export_csv(db: Database, output_dir: Path | str) -> list[Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    vehicles_path = out_dir / "vehicles.csv"
    with vehicles_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "plate", "mileage", "note", "created_at"])
        for v in db.list_vehicles():
            writer.writerow([v.id, v.plate, v.mileage, v.note, v.created_at])
    written.append(vehicles_path)

    tire_events_path = out_dir / "tire_events.csv"
    with tire_events_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "id",
                "vehicle_id",
                "position",
                "change_date",
                "mileage",
                "brand",
                "model",
                "note",
                "created_at",
            ]
        )
        for v in db.list_vehicles():
            for e in db.list_tire_events(v.id):
                writer.writerow(
                    [
                        e.id,
                        e.vehicle_id,
                        e.position,
                        e.change_date,
                        e.mileage,
                        e.brand,
                        e.model,
                        e.note,
                        e.created_at,
                    ]
                )
    written.append(tire_events_path)

    maintenance_path = out_dir / "maintenance_records.csv"
    with maintenance_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "id",
                "vehicle_id",
                "record_type",
                "service_date",
                "mileage",
                "note",
                "created_at",
            ]
        )
        for v in db.list_vehicles():
            for r in db.list_maintenance_records(v.id):
                writer.writerow(
                    [r.id, r.vehicle_id, r.record_type, r.service_date, r.mileage, r.note, r.created_at]
                )
    written.append(maintenance_path)

    return written

