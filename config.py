from datetime import timedelta

# =====================
# 강철 작업
# =====================
STEEL_TOTAL_DURATION = timedelta(hours=34)
STEEL_FUEL_INTERVAL = timedelta(hours=7, minutes=30)

STEEL_WARN_OFFSETS = [
    timedelta(hours=3),
    timedelta(hours=2),
    timedelta(hours=1),
    timedelta(minutes=30),
]

# =====================
# 양잠
# =====================
SILK_EGG_TO_LARVA = timedelta(hours=4, minutes=52)
SILK_LARVA_TO_PUPA = timedelta(hours=9, minutes=44)
SILK_PUPA_TO_ADULT = timedelta(hours=9, minutes=44)
SILK_ADULT_TO_EGG = timedelta(hours=5, minutes=30)

SILK_REPEAT_LARVA = timedelta(minutes=30)
SILK_REPEAT_PUPA = timedelta(hours=2)
SILK_REPEAT_ADULT = timedelta(hours=1)

# =====================
# 시간
# =====================
KST_OFFSET = 9
