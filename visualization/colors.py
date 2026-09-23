import numpy as np

# =========================================================
# 基本色
# =========================================================

# 背景
BACKGROUND_COLOR = np.array([0x0D / 255, 0x11 / 255, 0x17 / 255])

# 空セル
EMPTY_CELL_COLOR = np.array([0x21 / 255, 0x26 / 255, 0x2D / 255])

# Mark
MARK_BASE_COLOR = np.array([0x58 / 255, 0xA6 / 255, 0xFF / 255])

# Overlap
OVERLAP_BASE_COLOR = np.array([0x3F / 255, 0xB9 / 255, 0x50 / 255])

# Unique
UNIQUE_BASE_COLOR = np.array([0xE3 / 255, 0xB3 / 255, 0x41 / 255])


# =========================================================
# 線形補間
# =========================================================


def lerp(start, end, ratio):
    """
    2つの値・色を線形補間する
    """

    return start + (end - start) * ratio


# =========================================================
# RYB → RGB
# =========================================================


def ryb_to_rgb(red, yellow, blue):
    """
    互換用に残している関数

    今回のデザインでは色相を固定するので
    実運用では主に使わないが、
    heatmap.py側の既存呼び出しと互換性を保つため残す
    """

    red = np.clip(red, 0.0, 1.0)
    yellow = np.clip(yellow, 0.0, 1.0)
    blue = np.clip(blue, 0.0, 1.0)

    WHITE = np.array([1.00, 1.00, 1.00])
    RED = np.array([0.95, 0.12, 0.12])
    YELLOW = np.array([1.00, 0.82, 0.05])
    BLUE = np.array([0.05, 0.28, 0.95])
    ORANGE = np.array([1.00, 0.40, 0.02])
    VIOLET = np.array([0.45, 0.08, 0.65])
    GREEN = np.array([0.05, 0.72, 0.28])
    BLACK = np.array([0.04, 0.04, 0.05])

    color_00 = lerp(WHITE, RED, red)
    color_10 = lerp(YELLOW, ORANGE, red)
    color_01 = lerp(BLUE, VIOLET, red)
    color_11 = lerp(GREEN, BLACK, red)

    color_0 = lerp(color_00, color_10, yellow)
    color_1 = lerp(color_01, color_11, yellow)

    color = lerp(color_0, color_1, blue)

    return np.clip(color, 0.0, 1.0)


# =========================================================
# 密度補正
# =========================================================


def apply_density(base_color, density):
    """
    密度に応じて色を調整する

    - 色相は固定
    - 密度だけで明るさ・存在感を変える
    - 空セル色からベース色へ補間する
    """

    density = np.clip(density, 0.0, 1.0)

    # 少量でも見えるように少し持ち上げる
    strength = 0.25 + 0.75 * (density**0.80)

    return np.clip(lerp(EMPTY_CELL_COLOR, base_color, strength), 0.0, 1.0)


# =========================================================
# Mark / Unique → 表示色
# =========================================================


def create_data_color(mark_active, unique_active, mark_ratio, unique_ratio):
    """
    色相は完全固定にする

    - Markのみ    → BLUE
    - Overlap     → GREEN
    - Uniqueのみ → YELLOW

    密度だけを変化させる
    """

    # -----------------------------------------
    # データなし
    # -----------------------------------------

    if not mark_active and not unique_active:
        return EMPTY_CELL_COLOR

    # -----------------------------------------
    # Mark + Unique
    # -----------------------------------------

    if mark_active and unique_active:
        density = max(mark_ratio, unique_ratio)

        return apply_density(OVERLAP_BASE_COLOR, density)

    # -----------------------------------------
    # Markのみ
    # -----------------------------------------

    if mark_active:
        return apply_density(MARK_BASE_COLOR, mark_ratio)

    # -----------------------------------------
    # Uniqueのみ
    # -----------------------------------------

    return apply_density(UNIQUE_BASE_COLOR, unique_ratio)
