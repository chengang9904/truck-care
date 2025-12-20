from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from truck_care.db import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_vehicle_crud(self) -> None:
        vid = self.db.create_vehicle("ABC-123", 1000, "note")
        vehicles = self.db.list_vehicles()
        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0].id, vid)
        self.db.update_vehicle(vid, "ABC-123", 1200, "n2")
        v = self.db.get_vehicle(vid)
        self.assertIsNotNone(v)
        self.assertEqual(v.mileage, 1200)  # type: ignore[union-attr]
        self.db.delete_vehicle(vid)
        self.assertEqual(self.db.list_vehicles(), [])

    def test_tire_event_positions(self) -> None:
        vid = self.db.create_vehicle("DEF-456", 0, "")
        eid = self.db.create_tire_event(vid, "F1", "2025-01-01", 100, "B", "M", "N")
        self.assertTrue(any(e.id == eid for e in self.db.list_tire_events(vid)))
        with self.assertRaises(ValueError):
            self.db.create_tire_event(vid, "X", "2025-01-01", 100)

    def test_current_tires_picks_latest_by_date_then_id(self) -> None:
        vid = self.db.create_vehicle("JKL-000", 0, "")
        self.db.create_tire_event(vid, "F1", "2025-01-01", 100, brand="B1")
        latest_id = self.db.create_tire_event(vid, "F1", "2025-01-02", 200, brand="B2")
        current = self.db.current_tires(vid)
        self.assertIsNotNone(current["F1"])
        self.assertEqual(current["F1"].id, latest_id)  # type: ignore[union-attr]
        self.assertEqual(current["F1"].brand, "B2")  # type: ignore[union-attr]

        id1 = self.db.create_tire_event(vid, "R1", "2025-01-03", 300, brand="T1")
        id2 = self.db.create_tire_event(vid, "R1", "2025-01-03", 301, brand="T2")
        current = self.db.current_tires(vid)
        self.assertIsNotNone(current["R1"])
        self.assertEqual(current["R1"].id, max(id1, id2))  # type: ignore[union-attr]

    def test_list_tire_events_can_filter_by_position(self) -> None:
        vid = self.db.create_vehicle("POS-001", 0, "")
        self.db.create_tire_event(vid, "F1", "2025-01-01", 100, brand="A")
        self.db.create_tire_event(vid, "F2", "2025-01-02", 200, brand="B")
        f1 = self.db.list_tire_events(vid, position="F1")
        self.assertEqual(len(f1), 1)
        self.assertEqual(f1[0].position, "F1")

    def test_delete_vehicle_cascades(self) -> None:
        vid = self.db.create_vehicle("GHI-789", 0, "")
        self.db.create_tire_event(vid, "F1", "2025-01-01", 0)
        self.db.create_maintenance_record(vid, "机油更换", "2025-01-02", 10, "ok")
        self.db.delete_vehicle(vid)
        self.assertEqual(self.db.list_vehicles(), [])


if __name__ == "__main__":
    unittest.main()
