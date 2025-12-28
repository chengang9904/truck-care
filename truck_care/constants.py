# 牵引车轮胎位置（前8轮，成对）
TRACTOR_TIRE_POSITIONS = (
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
)

# 挂车轮胎位置（后12轮，成对）
TRAILER_TIRE_POSITIONS = (
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "R7",
    "R8",
    "R9",
    "R10",
    "R11",
    "R12",
)

# 所有轮胎位置（兼容旧代码）
TIRE_POSITIONS = TRACTOR_TIRE_POSITIONS + TRAILER_TIRE_POSITIONS

MAINTENANCE_TYPES = (
    "机油更换",
    "保养",
    "其他",
)

# 车辆类型
VEHICLE_TYPE_TRACTOR = "tractor"  # 牵引车
VEHICLE_TYPE_TRAILER = "trailer"  # 挂车

