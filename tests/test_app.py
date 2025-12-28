"""GUI 应用测试"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from truck_care.app import TireVisualizer
from truck_care.constants import TRACTOR_TIRE_POSITIONS, TRAILER_TIRE_POSITIONS
from truck_care.db import Database


class TireVisualizerTests(unittest.TestCase):
    """轮胎可视化组件测试"""

    def test_tractor_visualizer_positions(self) -> None:
        """牵引车可视化器接受8个轮胎位置"""
        import tkinter as tk
        
        root = tk.Tk()
        try:
            selected_positions = []
            
            def on_select(pos: str) -> None:
                selected_positions.append(pos)
            
            visualizer = TireVisualizer(
                root,
                TRACTOR_TIRE_POSITIONS,
                "牵引车",
                on_select
            )
            
            # 验证轮胎位置数量
            self.assertEqual(len(visualizer.tire_positions), 8)
            self.assertEqual(visualizer.tire_positions, TRACTOR_TIRE_POSITIONS)
            
            # 验证所有位置都创建了项目
            for pos in TRACTOR_TIRE_POSITIONS:
                self.assertIn(pos, visualizer._item_map)
        finally:
            root.destroy()

    def test_trailer_visualizer_positions(self) -> None:
        """挂车可视化器接受12个轮胎位置"""
        import tkinter as tk
        
        root = tk.Tk()
        try:
            selected_positions = []
            
            def on_select(pos: str) -> None:
                selected_positions.append(pos)
            
            visualizer = TireVisualizer(
                root,
                TRAILER_TIRE_POSITIONS,
                "挂车",
                on_select
            )
            
            # 验证轮胎位置数量
            self.assertEqual(len(visualizer.tire_positions), 12)
            self.assertEqual(visualizer.tire_positions, TRAILER_TIRE_POSITIONS)
            
            # 验证所有位置都创建了项目
            for pos in TRAILER_TIRE_POSITIONS:
                self.assertIn(pos, visualizer._item_map)
        finally:
            root.destroy()

    def test_visualizer_selection(self) -> None:
        """测试轮胎选择功能"""
        import tkinter as tk
        
        root = tk.Tk()
        try:
            selected_positions = []
            
            def on_select(pos: str) -> None:
                selected_positions.append(pos)
            
            visualizer = TireVisualizer(
                root,
                TRACTOR_TIRE_POSITIONS,
                "牵引车",
                on_select
            )
            
            # 选择一个位置
            visualizer.select("F1")
            self.assertEqual(visualizer.selected_pos, "F1")
            
            # 选择另一个位置
            visualizer.select("F5")
            self.assertEqual(visualizer.selected_pos, "F5")
            
            # 取消选择
            visualizer.select(None)
            self.assertIsNone(visualizer.selected_pos)
        finally:
            root.destroy()


class DatabaseIntegrationTests(unittest.TestCase):
    """数据库集成测试"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_all_tractor_tire_positions_work(self) -> None:
        """测试牵引车所有8个轮胎位置都能正常工作"""
        from truck_care.constants import VEHICLE_TYPE_TRACTOR
        
        tid = self.db.create_tractor("TEST-001", 1000)
        
        # 为所有8个位置创建轮胎记录
        for i, pos in enumerate(TRACTOR_TIRE_POSITIONS):
            eid = self.db.create_tire_event(
                VEHICLE_TYPE_TRACTOR,
                tid,
                pos,
                f"2025-01-{i+1:02d}",
                1000 + i * 100,
                f"品牌{i+1}",
                f"型号{i+1}"
            )
            self.assertIsNotNone(eid)
        
        # 验证所有记录都能查询
        all_events = self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, tid)
        self.assertEqual(len(all_events), 8)
        
        # 验证 current_tires 返回所有8个位置
        current = self.db.current_tires(VEHICLE_TYPE_TRACTOR, tid)
        for pos in TRACTOR_TIRE_POSITIONS:
            self.assertIn(pos, current)
            self.assertIsNotNone(current[pos])

    def test_all_trailer_tire_positions_work(self) -> None:
        """测试挂车所有12个轮胎位置都能正常工作"""
        from truck_care.constants import VEHICLE_TYPE_TRAILER
        
        tid = self.db.create_trailer("TRAILER-TEST-001")
        
        # 为所有12个位置创建轮胎记录
        for i, pos in enumerate(TRAILER_TIRE_POSITIONS):
            eid = self.db.create_tire_event(
                VEHICLE_TYPE_TRAILER,
                tid,
                pos,
                f"2025-01-{i+1:02d}",
                i * 50,
                f"品牌{i+1}",
                f"型号{i+1}"
            )
            self.assertIsNotNone(eid)
        
        # 验证所有记录都能查询
        all_events = self.db.list_tire_events(VEHICLE_TYPE_TRAILER, tid)
        self.assertEqual(len(all_events), 12)
        
        # 验证 current_tires 返回所有12个位置
        current = self.db.current_tires(VEHICLE_TYPE_TRAILER, tid)
        for pos in TRAILER_TIRE_POSITIONS:
            self.assertIn(pos, current)
            self.assertIsNotNone(current[pos])

    def test_mixed_vehicles_and_events(self) -> None:
        """测试混合多辆车和多条记录的场景"""
        from truck_care.constants import VEHICLE_TYPE_TRACTOR, VEHICLE_TYPE_TRAILER
        
        # 创建2辆牵引车
        t1 = self.db.create_tractor("T1", 1000)
        t2 = self.db.create_tractor("T2", 2000)
        
        # 创建2辆挂车
        r1 = self.db.create_trailer("R1")
        r2 = self.db.create_trailer("R2")
        
        # 为每辆车添加轮胎记录
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, t1, "F1", "2025-01-01", 1000)
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, t1, "F8", "2025-01-02", 1100)
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, t2, "F5", "2025-01-03", 2000)
        
        self.db.create_tire_event(VEHICLE_TYPE_TRAILER, r1, "R1", "2025-01-04", 0)
        self.db.create_tire_event(VEHICLE_TYPE_TRAILER, r1, "R12", "2025-01-05", 0)
        self.db.create_tire_event(VEHICLE_TYPE_TRAILER, r2, "R6", "2025-01-06", 0)
        
        # 验证查询不会混淆
        t1_events = self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, t1)
        self.assertEqual(len(t1_events), 2)
        
        t2_events = self.db.list_tire_events(VEHICLE_TYPE_TRACTOR, t2)
        self.assertEqual(len(t2_events), 1)
        
        r1_events = self.db.list_tire_events(VEHICLE_TYPE_TRAILER, r1)
        self.assertEqual(len(r1_events), 2)
        
        r2_events = self.db.list_tire_events(VEHICLE_TYPE_TRAILER, r2)
        self.assertEqual(len(r2_events), 1)


class ExporterTests(unittest.TestCase):
    """CSV 导出测试"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.db_path)
        self.db.init_db()
        self.export_dir = Path(self.tmp.name) / "exports"
        self.export_dir.mkdir()

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_export_creates_files(self) -> None:
        """测试导出创建所有必需的CSV文件"""
        from truck_care.constants import VEHICLE_TYPE_TRACTOR, VEHICLE_TYPE_TRAILER
        from truck_care.exporter import export_csv
        
        # 创建测试数据
        t1 = self.db.create_tractor("T1", 1000)
        r1 = self.db.create_trailer("R1")
        
        self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, t1, "F1", "2025-01-01", 1000)
        self.db.create_tire_event(VEHICLE_TYPE_TRAILER, r1, "R1", "2025-01-01", 0)
        
        self.db.create_maintenance_record(VEHICLE_TYPE_TRACTOR, t1, "机油更换", "2025-01-01", 1000)
        self.db.create_maintenance_record(VEHICLE_TYPE_TRAILER, r1, "保养", "2025-01-01", 0)
        
        # 执行导出
        paths = export_csv(self.db, self.export_dir)
        
        # 验证创建了4个文件
        self.assertEqual(len(paths), 4)
        
        # 验证文件存在
        for path in paths:
            self.assertTrue(path.exists())
            self.assertTrue(path.is_file())
        
        # 验证文件名
        file_names = {p.name for p in paths}
        expected = {"tractors.csv", "trailers.csv", "tire_events.csv", "maintenance_records.csv"}
        self.assertEqual(file_names, expected)

    def test_export_with_8_and_12_positions(self) -> None:
        """测试导出包含F1-F8和R1-R12位置的数据"""
        from truck_care.constants import VEHICLE_TYPE_TRACTOR, VEHICLE_TYPE_TRAILER
        from truck_care.exporter import export_csv
        
        t1 = self.db.create_tractor("T1", 1000)
        r1 = self.db.create_trailer("R1")
        
        # 添加所有轮胎位置的记录
        for pos in TRACTOR_TIRE_POSITIONS:
            self.db.create_tire_event(VEHICLE_TYPE_TRACTOR, t1, pos, "2025-01-01", 1000)
        
        for pos in TRAILER_TIRE_POSITIONS:
            self.db.create_tire_event(VEHICLE_TYPE_TRAILER, r1, pos, "2025-01-01", 0)
        
        # 执行导出
        paths = export_csv(self.db, self.export_dir)
        
        # 读取tire_events.csv验证内容
        tire_events_path = next(p for p in paths if p.name == "tire_events.csv")
        with open(tire_events_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
            # 验证包含所有位置
            for pos in TRACTOR_TIRE_POSITIONS:
                self.assertIn(pos, content)
            for pos in TRAILER_TIRE_POSITIONS:
                self.assertIn(pos, content)


if __name__ == "__main__":
    unittest.main()
