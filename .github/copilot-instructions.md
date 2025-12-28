# TruckCare AI Coding Instructions

## 项目概览
TruckCare 是一个离线本地桌面应用，用于管理卡车的健康维护记录（轮胎更换、机油保养等）。使用 Python + Tkinter GUI + SQLite 数据库。

**核心架构**：
- `truck_care/app.py` - Tkinter GUI 主应用（~760行），包含车辆可视化、轮胎管理、维护记录 CRUD 界面
- `truck_care/db.py` - SQLite 数据访问层，使用 dataclass 建模（Vehicle/TireEvent/MaintenanceRecord）
- `truck_care/exporter.py` - CSV 数据导出功能（UTF-8-BOM 编码）
- `truck_care/constants.py` - 业务常量（轮胎位置 F1-F4/R1-R6，维护类型）

## 关键业务逻辑

### 轮胎管理规则
- 固定 10 个轮胎位置：**前 4 轮（F1-F4）+ 后 6 轮（R1-R6）**，定义在 `TIRE_POSITIONS`
- `current_tires()` 返回每个位置的**最新轮胎**（按 `change_date DESC, id DESC` 排序）
- 轮胎历史记录通过 `list_tire_events(vehicle_id, position)` 查询特定位置或全部历史

### 数据完整性约束
- 所有里程数（mileage）必须 `>= 0`（CHECK 约束）
- 轮胎位置必须在 `TIRE_POSITIONS` 中（CHECK + 代码校验）
- 外键级联删除：删除车辆会自动清理其关联的轮胎和维护记录
- 车牌号（plate）必须唯一且非空
- 日期统一使用 ISO 格式字符串（YYYY-MM-DD），`_to_iso()` 处理 date/str 转换

## 开发工作流

### 本地开发
```bash
# 运行应用（推荐方式）
python run.py

# 或通过模块方式
python -m truck_care

# 运行测试
python -m unittest discover tests
```

### 打包分发
使用 PyInstaller 打包成独立 exe：
```bash
# GUI 版本（无控制台窗口）
pyinstaller TruckCare.spec

# 控制台版本（显示调试信息）
pyinstaller TruckCareConsole.spec
```
注意：spec 文件已配置 `console=False`（GUI）/ `console=True`（Console）

### 数据库位置
- 默认路径：`~/.truck-care/truck_care.sqlite3`（跨平台用户目录）
- 测试时使用临时文件：`tempfile.TemporaryDirectory()`

## 编码约定

### UI 组件模式
- **自定义可视化组件**：参考 `TireVisualizer` - Canvas 绘制卡车轮胎图示，带点击选择和悬停效果
- **表格显示**：使用 `ttk.Treeview` 展示列表数据（车辆、维护记录）
- **表单输入**：使用 `ttk.LabelFrame` + `ttk.Entry/DateEntry/Combobox` 组合
- 错误提示统一用 `messagebox.showerror()` / 成功提示用 `messagebox.showinfo()`

### 数据库访问模式
```python
# 所有写操作必须用 with 上下文管理器确保事务性
with self._conn:
    self._conn.execute("INSERT INTO ...", params)

# 读操作直接调用，使用 Row Factory 转 dict 再构造 dataclass
rows = self._conn.execute("SELECT ...").fetchall()
return [Vehicle(**dict(r)) for r in rows]
```

### CSV 导出约定
- 使用 `encoding="utf-8-sig"` 保证 Excel 正确识别中文（添加 BOM）
- 表头使用英文字段名（id, plate, mileage 等）
- 遍历所有车辆，为每辆车导出其关联记录

## 常见任务

### 添加新的维护类型
1. 更新 `constants.py` 中的 `MAINTENANCE_TYPES` 元组
2. UI 会自动从该常量填充下拉框（无需修改 app.py）

### 修改轮胎布局
1. 调整 `TIRE_POSITIONS` 常量
2. 更新 `TireVisualizer._draw_truck()` 中的 layout 列表和绘图逻辑
3. 重新运行 `init_db()` 会更新 CHECK 约束（需清空数据库或迁移）

### 调试 GUI 布局
- 运行 `TruckCareConsole.spec` 版本查看控制台输出
- Tkinter 组件使用 `pack()/grid()` 混合布局，注意 `sticky` 和 `expand/fill` 参数

## 特殊注意事项
- **不要使用 ORM**：直接使用 SQLite + dataclasses，避免额外依赖
- **日期处理**：始终通过 `_to_iso()` 转换为 ISO 字符串存储，显示时可用 `date.fromisoformat()`
- **中文支持**：所有用户可见文字使用中文，变量名/注释可混用英文
- **测试覆盖**：修改 db.py 核心逻辑必须添加 unittest 测试用例
