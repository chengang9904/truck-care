# TruckCare AI Coding Instructions

## 项目概览
TruckCare 是一个离线本地桌面应用，用于管理**牵引车（车头）和挂车**的健康维护记录（轮胎更换、机油保养等）。使用 Python + Tkinter GUI + SQLite 数据库。

**核心架构**：
- `truck_care/app.py` - Tkinter GUI 主应用，包含牵引车/挂车管理、轮胎管理、维护记录 CRUD 界面
- `truck_care/db.py` - SQLite 数据访问层，使用 dataclass 建模（Tractor/Trailer/TireEvent/MaintenanceRecord）
- `truck_care/exporter.py` - CSV 数据导出功能（UTF-8-BOM 编码）
- `truck_care/constants.py` - 业务常量（牵引车轮胎 F1-F4，挂车轮胎 R1-R6，维护类型）

## 关键业务逻辑

### 牵引车与挂车分离管理
- **牵引车（Tractor）**：车头，有 4 个轮胎位置（F1-F4），有里程数字段
- **挂车（Trailer）**：拖挂部分，有 6 个轮胎位置（R1-R6），无里程数字段
- 两者各有独立的车牌号，分别管理轮胎和保养记录
- 轮胎和保养记录通过 `vehicle_type` + `vehicle_id` 关联到具体车辆

### 轮胎位置约束
```python
TRACTOR_TIRE_POSITIONS = ("F1", "F2", "F3", "F4")  # 牵引车专用
TRAILER_TIRE_POSITIONS = ("R1", "R2", "R3", "R4", "R5", "R6")  # 挂车专用
VEHICLE_TYPE_TRACTOR = "tractor"
VEHICLE_TYPE_TRAILER = "trailer"
```
- 牵引车只能添加 F1-F4 位置的轮胎记录
- 挂车只能添加 R1-R6 位置的轮胎记录
- `current_tires(vehicle_type, vehicle_id)` 返回每个位置的最新轮胎

### 数据完整性约束
- 所有里程数（mileage）必须 `>= 0`（CHECK 约束）
- 车牌号（plate）在各自表内唯一且非空
- 删除车辆时手动级联删除关联的轮胎和保养记录
- 日期统一使用 ISO 格式字符串（YYYY-MM-DD）

## 开发工作流

### 本地开发
```bash
# 运行应用
python run.py
# 或
python -m truck_care

# 运行测试
python -m unittest discover tests
```

### 打包分发
```bash
pyinstaller TruckCare.spec      # GUI 版本（无控制台）
pyinstaller TruckCareConsole.spec  # 控制台版本（调试用）
```

### 数据库位置
- 默认路径：`~/.truck-care/truck_care.sqlite3`
- 测试使用临时目录：`tempfile.TemporaryDirectory()`

## 编码约定

### 数据库访问模式
```python
# 写操作必须用 with 确保事务
with self._conn:
    self._conn.execute("INSERT INTO ...", params)

# 读操作用 Row Factory 转 dataclass
rows = self._conn.execute("SELECT ...").fetchall()
return [Tractor(**dict(r)) for r in rows]
```

### UI 组件模式
- `TireVisualizer` - Canvas 绘制轮胎图示，根据 `vehicle_type` 显示不同布局
- `TractorFrame` / `TrailerFrame` - 车辆列表管理
- `TireFrame` / `MaintenanceFrame` - 通过 `vehicle_type` 参数区分牵引车/挂车

## 常见任务

### 添加新的维护类型
更新 `constants.py` 中的 `MAINTENANCE_TYPES` 元组即可

### 修改轮胎布局
1. 调整 `TRACTOR_TIRE_POSITIONS` 或 `TRAILER_TIRE_POSITIONS`
2. 更新 `TireVisualizer._draw_vehicle()` 中的绘图逻辑
3. 需要清空或迁移数据库

## 特殊注意事项
- **不要使用 ORM**：直接 SQLite + dataclasses
- **中文支持**：CSV 导出使用 `encoding="utf-8-sig"` 保证 Excel 兼容
- **测试覆盖**：修改 db.py 必须添加 unittest 测试用例
