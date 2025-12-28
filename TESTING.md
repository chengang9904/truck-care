# TruckCare 测试文档

## 测试概览

本项目包含全面的单元测试和集成测试，确保所有功能正常工作。

### 测试统计
- **总测试数**: 20个
- **测试文件**: 2个
  - `tests/test_db.py` - 数据库层测试（12个测试）
  - `tests/test_app.py` - 应用层测试（8个测试）
- **测试状态**: ✅ 全部通过

## 运行测试

### 运行所有测试
```bash
python -m unittest discover tests -v
```

### 运行特定测试文件
```bash
python -m unittest tests.test_db -v
python -m unittest tests.test_app -v
```

### 运行单个测试
```bash
python -m unittest tests.test_db.TractorTests.test_tractor_crud -v
```

## 测试覆盖

### 1. 数据库层测试 (`test_db.py`)

#### TractorTests - 牵引车测试
- ✅ `test_tractor_crud` - 牵引车增删改查
- ✅ `test_tractor_plate_unique` - 车牌唯一性约束

#### TrailerTests - 挂车测试
- ✅ `test_trailer_crud` - 挂车增删改查

#### TireEventTests - 轮胎事件测试
- ✅ `test_tractor_tire_positions` - 牵引车轮胎位置验证（F1-F8）
- ✅ `test_trailer_tire_positions` - 挂车轮胎位置验证（R1-R12）
- ✅ `test_current_tires_picks_latest` - 最新轮胎记录选择
- ✅ `test_current_tires_same_date_uses_id` - 同日期记录按ID排序
- ✅ `test_list_tire_events_filter_by_position` - 按位置筛选轮胎事件

#### MaintenanceRecordTests - 保养记录测试
- ✅ `test_tractor_maintenance` - 牵引车保养记录
- ✅ `test_trailer_maintenance` - 挂车保养记录

#### CascadeDeleteTests - 级联删除测试
- ✅ `test_delete_tractor_cascades` - 删除牵引车级联删除相关记录
- ✅ `test_delete_trailer_cascades` - 删除挂车级联删除相关记录

### 2. 应用层测试 (`test_app.py`)

#### TireVisualizerTests - 轮胎可视化测试
- ✅ `test_tractor_visualizer_positions` - 牵引车可视化器8个轮胎位置
- ✅ `test_trailer_visualizer_positions` - 挂车可视化器12个轮胎位置
- ✅ `test_visualizer_selection` - 轮胎选择功能

#### DatabaseIntegrationTests - 数据库集成测试
- ✅ `test_all_tractor_tire_positions_work` - 牵引车所有8个位置正常工作
- ✅ `test_all_trailer_tire_positions_work` - 挂车所有12个位置正常工作
- ✅ `test_mixed_vehicles_and_events` - 多车辆混合场景

#### ExporterTests - CSV导出测试
- ✅ `test_export_creates_files` - 导出创建4个CSV文件
- ✅ `test_export_with_8_and_12_positions` - 导出包含所有轮胎位置

## 关键测试场景

### 轮胎位置验证
- 牵引车：严格限制F1-F8，拒绝R系列
- 挂车：严格限制R1-R12，拒绝F系列
- 位置错误时抛出 `ValueError`

### 数据完整性
- 车牌唯一性约束
- 里程数非负约束
- 日期格式验证（ISO格式）

### 级联删除
- 删除车辆时自动删除：
  - 所有轮胎更换记录
  - 所有保养维护记录

### CSV导出
- 生成4个文件：
  1. `tractors.csv` - 牵引车列表
  2. `trailers.csv` - 挂车列表
  3. `tire_events.csv` - 轮胎更换记录
  4. `maintenance_records.csv` - 保养记录
- UTF-8-BOM编码，Excel兼容

## 测试数据隔离

所有测试使用临时数据库，测试完成后自动清理：
```python
self.tmp = tempfile.TemporaryDirectory()
self.db_path = Path(self.tmp.name) / "test.sqlite3"
```

## 持续集成建议

### GitHub Actions 配置示例
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Run tests
        run: python -m unittest discover tests -v
```

## 测试最佳实践

1. **测试前运行** - 修改代码后立即运行测试
2. **添加新功能** - 先写测试，后写代码（TDD）
3. **保持独立** - 每个测试独立运行，不依赖其他测试
4. **清理资源** - 使用 `setUp` 和 `tearDown` 管理测试资源
5. **有意义的名称** - 测试名称清楚描述测试内容

## 测试输出示例

```
test_all_tractor_tire_positions_work ... ok
test_all_trailer_tire_positions_work ... ok
test_mixed_vehicles_and_events ... ok
test_export_creates_files ... ok
test_export_with_8_and_12_positions ... ok
test_tractor_visualizer_positions ... ok
test_trailer_visualizer_positions ... ok
test_visualizer_selection ... ok
test_delete_tractor_cascades ... ok
test_delete_trailer_cascades ... ok
test_tractor_maintenance ... ok
test_trailer_maintenance ... ok
test_current_tires_picks_latest ... ok
test_current_tires_same_date_uses_id ... ok
test_list_tire_events_filter_by_position ... ok
test_tractor_tire_positions ... ok
test_trailer_tire_positions ... ok
test_tractor_crud ... ok
test_tractor_plate_unique ... ok
test_trailer_crud ... ok

----------------------------------------------------------------------
Ran 20 tests in 0.822s

OK
```

## 故障排查

### 测试失败常见原因
1. **数据库锁定** - 确保没有运行中的应用实例
2. **路径问题** - 使用绝对路径或相对于项目根目录的路径
3. **GUI测试失败** - 确保测试环境支持Tkinter（需要图形界面支持）

### 调试单个测试
```bash
# 添加详细输出
python -m unittest tests.test_db.TractorTests.test_tractor_crud -v

# 使用pdb调试
python -m pdb -m unittest tests.test_db.TractorTests.test_tractor_crud
```
