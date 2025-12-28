from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from truck_care.constants import VEHICLE_TYPE_TRACTOR, VEHICLE_TYPE_TRAILER
from truck_care.db import Database


class TractorTests(unittest.TestCase):
    """牵引车 CRUD 测试"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_tractor_crud(self) -> None:
        tid = self.db.create_tractor("ABC-123", 1000, "note")
        tractors = self.db.list_tractors()
        self.assertEqual(len(tractors), 1)
        self.assertEqual(tractors[0].id, tid)
        
        self.db.update_tractor(tid, "ABC-123", 1200, "n2")
        t = self.db.get_tractor(tid)
        self.assertIsNotNone(t)
        self.assertEqual(t.mileage, 1200)  # type: ignore[union-attr]
        
        self.db.delete_tractor(tid)
        self.assertEqual(self.db.list_tractors(), [])

    def test_tractor_plate_unique(self) -> None:
        self.db.create_tractor("UNIQUE-001", 0)
        with self.assertRaises(Exception):
            self.db.create_tractor("UNIQUE-001", 100)


class TrailerTests(unittest.TestCase):
    """挂车 CRUD 测试"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_trailer_crud(self) -> None:
        tid = self.db.create_trailer("TRAILER-001", "挂车备注")
        trailers = self.db.list_trailers()
        self.assertEqual(len(trailers), 1)
        self.assertEqual(trailers[0].id, tid)
        
        self.db.update_trailer(tid, "TRAILER-002", "更新备注")
        t = self.db.get_trailer(tid)
        self.assertIsNotNone(t)
        self.assertEqual(t.plate, "TRAILER-002")  # type: ignore[union-attr]
        
        self.db.delete_trailer(tid)
        self.assertEqual(self.db.list_trailers(), [])


class TireEventTests(unittest.TestCase):
    """轮胎事件测试"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_tractor_tire_positions(self) -> None:
        """牵引车只能使用 F1-F8 轮胎位置"""
        tid = self.db.create_tractor("TRACTOR-001", 0)
        
        # 有效位置
        eid = self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F1", "2025-01-01", 100)
        self.assertTrue(any(e.id == eid for e in self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, tid)))
        
        # 测试所有8个位置都有效
        for pos in ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"]:
            eid = self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, pos, "2025-01-01", 100)
            self.assertIsNotNone(eid)
        
        # 无效位置（R1 属于挂车）
        with self.assertRaises(ValueError):
            self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "R1", "2025-01-01", 100)

    def test_trailer_tire_positions(self) -> None:
        """挂车只能使用 R1-R12 轮胎位置"""
        tid = self.db.create_trailer("TRAILER-001")
        
        # 有效位置
        eid = self.db.create_tire_event(VEHICLE_TYPE_TRAILER, tid, "R1", "2025-01-01", 100)
        self.assertTrue(any(e.id == eid for e in self.db.list_tire_events(VEHICLE_TYPE_TRAILER, tid)))
        
        # 测试所有12个位置都有效
        for pos in ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12"]:
            eid = self.db.create_tire_event(VEHICLE_TYPE_TRAILER, tid, pos, "2025-01-01", 100)
            self.assertIsNotNone(eid)
        
        # 无效位置（F1 属于牵引车）
        with self.assertRaises(ValueError):
            self.db.create_tire_event(VEHICLE_TYPE_TRAILER, tid, "F1", "2025-01-01", 100)

    def test_current_tires_picks_latest(self) -> None:
        """current_tires 返回最新的轮胎记录"""
        tid = self.db.create_tractor("TRACTOR-002", 0)
        
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F1", "2025-01-01", 100, brand="B1")
        latest_id = self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F1", "2025-01-02", 200, brand="B2")
        
        current = self.db.current_tires(VEHICLE_TYPE_TRACTOR, tid)
        self.assertIsNotNone(current["F1"])
        self.assertEqual(current["F1"].id, latest_id)  # type: ignore[union-attr]
        self.assertEqual(current["F1"].brand, "B2")  # type: ignore[union-attr]

    def test_current_tires_same_date_uses_id(self) -> None:
        """同一天的记录按 id 降序取最新"""
        tid = self.db.create_tractor("TRACTOR-003", 0)
        
        id1 = self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F2", "2025-01-03", 300, brand="T1")
        id2 = self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F2", "2025-01-03", 301, brand="T2")
        
        current = self.db.current_tires(VEHICLE_TYPE_TRACTOR, tid)
        self.assertIsNotNone(current["F2"])
        self.assertEqual(current["F2"].id, max(id1, id2))  # type: ignore[union-attr]

    def test_list_tire_events_filter_by_position(self) -> None:
        """按位置筛选轮胎事件"""
        tid = self.db.create_tractor("TRACTOR-004", 0)
        
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F1", "2025-01-01", 100, brand="A")
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F2", "2025-01-02", 200, brand="B")
        
        f1_events = self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, tid, position="F1")
        self.assertEqual(len(f1_events), 1)
        self.assertEqual(f1_events[0].position, "F1")


class MaintenanceRecordTests(unittest.TestCase):
    """保养记录测试"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_tractor_maintenance(self) -> None:
        tid = self.db.create_tractor("TRACTOR-M1", 1000)
        
        rid = self.db.create_maintenance_record(
            VEHICLE_TYPE_TRACTOR, tid, "机油更换", "2025-01-01", 1000, "备注"
        )
        
        records = self.db.list_maintenance_records(VEHICLE_TYPE_TRACTOR, tid)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, rid)
        self.assertEqual(records[0].record_type, "机油更换")

    def test_trailer_maintenance(self) -> None:
        tid = self.db.create_trailer("TRAILER-M1")
        
        rid = self.db.create_maintenance_record(
            VEHICLE_TYPE_TRAILER, tid, "保养", "2025-02-01", 0, "挂车保养"
        )
        
        records = self.db.list_maintenance_records(VEHICLE_TYPE_TRAILER, tid)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].id, rid)


class CascadeDeleteTests(unittest.TestCase):
    """级联删除测试"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_delete_tractor_cascades(self) -> None:
        """删除牵引车时关联记录也被删除"""
        tid = self.db.create_tractor("CASCADE-T1", 0)
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, tid, "F1", "2025-01-01", 0)
        self.db.create_maintenance_record(VEHICLE_TYPE_TRACTOR, tid, "机油更换", "2025-01-02", 10)
        
        self.db.delete_tractor(tid)
        
        self.assertEqual(self.db.list_tractors(), [])
        self.assertEqual(self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, tid), [])
        self.assertEqual(self.db.list_maintenance_records(VEHICLE_TYPE_TRACTOR, tid), [])

    def test_delete_trailer_cascades(self) -> None:
        """删除挂车时关联记录也被删除"""
        tid = self.db.create_trailer("CASCADE-R1")
        self.db.create_tire_event(VEHICLE_TYPE_TRAILER, tid, "R1", "2025-01-01", 0)
        self.db.create_maintenance_record(VEHICLE_TYPE_TRAILER, tid, "保养", "2025-01-02", 0)
        
        self.db.delete_trailer(tid)
        
        self.assertEqual(self.db.list_trailers(), [])
        self.assertEqual(self.db.list_tire_events(VEHICLE_TYPE_TRAILER, tid), [])
        self.assertEqual(self.db.list_maintenance_records(VEHICLE_TYPE_TRAILER, tid), [])


if __name__ == "__main__":
    unittest.main()
