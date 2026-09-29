import numpy as np

# =========================================================
# 基本色
# =========================================================

# 背景
BACKGROUND_COLOR = np.array([0x0D / 255, 0x11 / 255, 0x17 / 255])

# 空セル
EMPTY_CELL_COLOR = np.array([0x21 / 255, 0x26 / 255, 0x2D / 255])

# Mark
# 今回は「各時間区間の左側」を緑で表示する
MARK_BASE_COLOR = np.array([0x3F / 255, 0xB9 / 255, 0x50 / 255])

# Unique
# 今回は「各時間区間の右側」を黄で表示する
UNIQUE_BASE_COLOR = np.array([0xD2 / 255, 0x99 / 255, 0x22 / 255])

# UI文字
TEXT_PRIMARY_COLOR = "#f0f6fc"
TEXT_SECONDARY_COLOR = "#8b949e"

# 軸色
MARK_AXIS_COLOR = "#3fb950"
UNIQUE_AXIS_COLOR = "#d29922"


# =========================================================
# 線形補間
# =========================================================


def lerp(start, end, ratio):
    """
    2つの値・色を線形補間する
    """

    return start + (end - start) * ratio


# =========================================================
# 密度補正
# =========================================================


def apply_density(base_color, density):
    """
    密度に応じて色の明るさを調整する。

    高さでも値を表しているため、色差は強くしすぎず、
    データが少ない場所も見失わないよう最低輝度を持たせる。
    """

    density = float(np.clip(density, 0.0, 1.0))

    # 少量でも見えるように少し持ち上げる
    strength = 0.45 + 0.55 * (density**0.75)

    return np.clip(
        lerp(EMPTY_CELL_COLOR, base_color, strength),
        0.0,
        1.0,
    )


# =========================================================
# Mark / Unique 表示色
# =========================================================


def mark_color(density):
    """Mark用の緑色を返す。"""

    return apply_density(MARK_BASE_COLOR, density)


def unique_color(density):
    """Unique用の黄色を返す。"""

    return apply_density(UNIQUE_BASE_COLOR, density)
