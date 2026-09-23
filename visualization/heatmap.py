import math

import numpy as np
import matplotlib.pyplot as plt

from matplotlib.patches import FancyBboxPatch, Patch

from matplotlib.widgets import Slider

from matplotlib.ticker import FuncFormatter, FixedLocator

from config import (
    HEATMAP_DEFAULT_BIN,
    HEATMAP_MIN_BIN,
    HEATMAP_MAX_BIN,
    HEATMAP_BIN_STEP,
    HEATMAP_GRID_ROWS,
    HEATMAP_VISIBLE_COLUMNS,
    HEATMAP_CELL_GAP,
    HEATMAP_ROUND_RATIO,
)

from database.connection import get_connection

from time_utils import seconds_to_time

from visualization.colors import (
    BACKGROUND_COLOR,
    EMPTY_CELL_COLOR,
    create_data_color,
    ryb_to_rgb,
)

# =========================================================
# 配信情報取得
# =========================================================


def get_stream(live_id):
    """
    streamsテーブルから
    指定された配信情報を取得する
    """

    with get_connection() as conn:

        row = conn.execute(
            """
            SELECT
                id,
                live_id,
                title,
                duration
            FROM streams
            WHERE live_id = ?
            """,
            (live_id,),
        ).fetchone()

    # 配信が存在しない場合
    if row is None:
        return None

    return dict(row)


# =========================================================
# Mark / Unique取得
# =========================================================


def get_mark_unique(stream_id):
    """
    mark_uniqueテーブルから
    指定された配信の解析結果を取得する
    """

    with get_connection() as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                start_time,
                end_time,
                mark_count,
                unique_count
            FROM mark_unique
            WHERE stream_id = ?
            ORDER BY start_time
            """,
            (stream_id,),
        ).fetchall()

    return [dict(row) for row in rows]


# =========================================================
# 時間ビン生成
# =========================================================


def create_bins(duration, mark_unique_list, bin_seconds):
    """
    mark_uniqueの範囲を
    指定秒数ごとの時間ビンへ展開する
    """

    # 必要なビン数
    bin_count = math.ceil(duration / bin_seconds)

    # Mark数
    mark_values = np.zeros(bin_count, dtype=int)

    # Unique数
    unique_values = np.zeros(bin_count, dtype=int)

    # 各時間帯に含まれる候補ID
    candidate_ids = [[] for _ in range(bin_count)]

    # -----------------------------------------
    # mark_uniqueを展開
    # -----------------------------------------

    for item in mark_unique_list:

        start_time = max(0, int(item["start_time"]))

        end_time = min(duration, int(item["end_time"]))

        # 不正な範囲
        if end_time <= start_time:
            continue

        # 開始ビン
        start_bin = start_time // bin_seconds

        # 終了ビン
        end_bin = (end_time - 1) // bin_seconds

        end_bin = min(bin_count - 1, end_bin)

        # -----------------------------------------
        # 該当ビンへ加算
        # -----------------------------------------

        for bin_index in range(start_bin, end_bin + 1):

            mark_values[bin_index] += int(item["mark_count"])

            unique_values[bin_index] += int(item["unique_count"])

            candidate_ids[bin_index].append(item["id"])

    return (mark_values, unique_values, candidate_ids)


# =========================================================
# ヒートマップ
# =========================================================


class MarkUniqueHeatmap:

    def __init__(self, live_id):

        # -----------------------------------------
        # 配信情報
        # -----------------------------------------

        self.stream = get_stream(live_id)

        if self.stream is None:
            raise ValueError("指定された配信が" "streamsテーブルに存在しません。")

        # -----------------------------------------
        # Mark / Unique情報
        # -----------------------------------------

        self.mark_unique_list = get_mark_unique(self.stream["id"])

        if not self.mark_unique_list:
            raise ValueError("mark_uniqueテーブルに" "対象データがありません。")

        # -----------------------------------------
        # 状態
        # -----------------------------------------

        # 1マスあたりの秒数
        self.bin_seconds = HEATMAP_DEFAULT_BIN

        self.mark_values = None
        self.unique_values = None

        self.candidate_ids = None

        # 最大値
        self.max_mark = 1
        self.max_unique = 1

        # Hover中のビン
        self.hover_bin = None

        # -----------------------------------------
        # Figure
        # -----------------------------------------

        self.fig = plt.figure(figsize=(16, 8))

        # 背景
        self.fig.patch.set_facecolor(BACKGROUND_COLOR)

        # -----------------------------------------
        # グラフ本体
        # -----------------------------------------

        self.ax = self.fig.add_axes([0.07, 0.22, 0.86, 0.66])

        self.ax.set_facecolor(BACKGROUND_COLOR)

        # Secondary Axis用
        self.ax_right = None

        # -----------------------------------------
        # Bin Slider
        # -----------------------------------------

        bin_ax = self.fig.add_axes([0.16, 0.105, 0.56, 0.030])

        bin_ax.set_facecolor("#161b22")

        self.bin_slider = Slider(
            ax=bin_ax,
            label="Bin",
            valmin=HEATMAP_MIN_BIN,
            valmax=HEATMAP_MAX_BIN,
            valinit=HEATMAP_DEFAULT_BIN,
            valstep=HEATMAP_BIN_STEP,
            valfmt="%0.0f sec",
        )

        # -----------------------------------------
        # Scroll Slider
        # -----------------------------------------

        scroll_ax = self.fig.add_axes([0.16, 0.050, 0.56, 0.030])

        scroll_ax.set_facecolor("#161b22")

        self.scroll_slider = Slider(
            ax=scroll_ax,
            label="Time",
            valmin=0,
            valmax=100,
            valinit=0,
            valstep=1,
            valfmt="%0.0f%%",
        )

        # -----------------------------------------
        # Slider文字色
        # -----------------------------------------

        for slider in (self.bin_slider, self.scroll_slider):

            slider.label.set_color("#8b949e")

            slider.valtext.set_color("#c9d1d9")

        # -----------------------------------------
        # Hover
        # -----------------------------------------

        self.annotation = None

        # -----------------------------------------
        # Event
        # -----------------------------------------

        self.bin_slider.on_changed(self.on_bin_changed)

        self.scroll_slider.on_changed(self.on_scroll_changed)

        self.fig.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)

        self.fig.canvas.mpl_connect("scroll_event", self.on_mouse_scroll)

        # -----------------------------------------
        # 初期データ生成
        # -----------------------------------------

        self.rebuild_data()

        # -----------------------------------------
        # 初期描画
        # -----------------------------------------

        self.draw()

    # =====================================================
    # データ再生成
    # =====================================================

    def rebuild_data(self):
        """
        現在のbin_secondsを使用して
        ヒートマップデータを再生成する
        """

        self.mark_values, self.unique_values, self.candidate_ids = create_bins(
            duration=self.stream["duration"],
            mark_unique_list=self.mark_unique_list,
            bin_seconds=self.bin_seconds,
        )

        # Mark最大値
        self.max_mark = max(1, int(self.mark_values.max()))

        # Unique最大値
        self.max_unique = max(1, int(self.unique_values.max()))

    # =====================================================
    # 表示開始位置
    # =====================================================

    def get_visible_start(self):
        """
        Scroll Sliderから
        表示開始ビンを計算する
        """

        total_bins = len(self.mark_values)

        max_start = max(0, total_bins - HEATMAP_VISIBLE_COLUMNS)

        ratio = self.scroll_slider.val / 100

        return int(round(max_start * ratio))

    # =====================================================
    # セル描画
    # =====================================================

    def draw_cell(self, x, y, color):
        """
        GitHub Grass風の
        フラットな角丸セルを描画する

        透過・グラデーション・影は使用しない
        """

        # マス同士の隙間
        gap = HEATMAP_CELL_GAP

        # セルサイズ
        size = 1.0 - gap

        # 中央寄せ
        offset = gap / 2

        # -----------------------------------------
        # セル
        # -----------------------------------------

        cell = FancyBboxPatch(
            (x + offset, y + offset),
            size,
            size,
            boxstyle=(
                "round," "pad=0," f"rounding_size=" f"{size * HEATMAP_ROUND_RATIO}"
            ),
            facecolor=color,
            # 通常時は枠線なし
            edgecolor="none",
            linewidth=0,
            zorder=2,
        )

        self.ax.add_patch(cell)

    # =====================================================
    # Hover列の枠
    # =====================================================

    def draw_hover_outline(self, bin_index):
        """
        Hover中の時間ビンを
        控えめな枠線で強調する
        """

        mark_count = int(self.mark_values[bin_index])

        unique_count = int(self.unique_values[bin_index])

        mark_ratio = mark_count / self.max_mark

        unique_ratio = unique_count / self.max_unique

        mark_height = math.ceil(mark_ratio * HEATMAP_GRID_ROWS)

        unique_height = math.ceil(unique_ratio * HEATMAP_GRID_ROWS)

        height = max(mark_height, unique_height)

        if height <= 0:
            return

        gap = HEATMAP_CELL_GAP

        size = 1.0 - gap

        offset = gap / 2

        # 各セルに薄い枠を追加
        for row in range(height):

            outline = FancyBboxPatch(
                (bin_index + offset, row + offset),
                size,
                size,
                boxstyle=(
                    "round," "pad=0," f"rounding_size=" f"{size * HEATMAP_ROUND_RATIO}"
                ),
                facecolor="none",
                edgecolor="#f0f6fc",
                linewidth=1.1,
                zorder=5,
            )

            self.ax.add_patch(outline)

    # =====================================================
    # 描画
    # =====================================================

    def draw(self):
        """
        現在の状態で
        ヒートマップを再描画する
        """

        # -----------------------------------------
        # 古い右Y軸削除
        # -----------------------------------------

        if self.ax_right is not None:

            self.ax_right.remove()

            self.ax_right = None

        # -----------------------------------------
        # Axesクリア
        # -----------------------------------------

        self.ax.clear()

        self.ax.set_facecolor(BACKGROUND_COLOR)

        # -----------------------------------------
        # 表示範囲
        # -----------------------------------------

        start_bin = self.get_visible_start()

        end_bin = min(len(self.mark_values), start_bin + HEATMAP_VISIBLE_COLUMNS)

        # -----------------------------------------
        # GitHub Grass風背景セル
        # -----------------------------------------

        # 表示中の全マスを
        # 暗い色で先に描画する
        for bin_index in range(start_bin, end_bin):

            for row in range(HEATMAP_GRID_ROWS):

                self.draw_cell(x=bin_index, y=row, color=EMPTY_CELL_COLOR)

        # -----------------------------------------
        # データセル
        # -----------------------------------------

        for bin_index in range(start_bin, end_bin):

            # Mark数
            mark_count = int(self.mark_values[bin_index])

            # Unique数
            unique_count = int(self.unique_values[bin_index])

            # -------------------------------------
            # 正規化
            # -------------------------------------

            mark_ratio = mark_count / self.max_mark

            unique_ratio = unique_count / self.max_unique

            # -------------------------------------
            # 高さ
            # -------------------------------------

            mark_height = math.ceil(mark_ratio * HEATMAP_GRID_ROWS)

            unique_height = math.ceil(unique_ratio * HEATMAP_GRID_ROWS)

            max_height = max(mark_height, unique_height)

            # -------------------------------------
            # セル
            # -------------------------------------

            for row in range(max_height):

                # Mark領域
                mark_active = row < mark_height

                # Unique領域
                unique_active = row < unique_height

                # RYB色計算
                color = create_data_color(
                    mark_active=mark_active,
                    unique_active=unique_active,
                    mark_ratio=mark_ratio,
                    unique_ratio=unique_ratio,
                )

                # ベタ塗り
                self.draw_cell(x=bin_index, y=row, color=color)

        # -----------------------------------------
        # Hover強調
        # -----------------------------------------

        if self.hover_bin is not None and start_bin <= self.hover_bin < end_bin:

            self.draw_hover_outline(self.hover_bin)

        # -----------------------------------------
        # X軸
        # -----------------------------------------

        self.ax.set_xlim(start_bin, max(start_bin + 1, end_bin))

        visible_count = max(1, end_bin - start_bin)

        # 約6個のラベル
        tick_step = max(1, visible_count // 6)

        x_ticks = list(range(start_bin, end_bin + 1, tick_step))

        self.ax.xaxis.set_major_locator(FixedLocator(x_ticks))

        self.ax.xaxis.set_major_formatter(FuncFormatter(self.format_x_axis))

        # -----------------------------------------
        # 左Y軸
        # -----------------------------------------

        self.ax.set_ylim(0, HEATMAP_GRID_ROWS)

        y_ticks = np.linspace(0, HEATMAP_GRID_ROWS, 5)

        self.ax.set_yticks(y_ticks)

        self.ax.yaxis.set_major_formatter(FuncFormatter(self.format_mark_axis))

        # -----------------------------------------
        # 右Y軸
        # -----------------------------------------

        def grid_to_unique(grid_value):

            return grid_value / HEATMAP_GRID_ROWS * self.max_unique

        def unique_to_grid(unique_value):

            if self.max_unique == 0:
                return 0

            return unique_value / self.max_unique * HEATMAP_GRID_ROWS

        self.ax_right = self.ax.secondary_yaxis(
            "right", functions=(grid_to_unique, unique_to_grid)
        )

        self.ax_right.set_yticks(np.linspace(0, self.max_unique, 5))

        # -----------------------------------------
        # 正方形維持
        # -----------------------------------------

        self.ax.set_aspect("equal", adjustable="box")

        # -----------------------------------------
        # ラベル
        # -----------------------------------------

        self.ax.set_xlabel("Stream time", color="#8b949e", labelpad=12)

        self.ax.set_ylabel("Mark count", color="#58a6ff", labelpad=10)

        self.ax_right.set_ylabel("Unique count", color="#d29922", labelpad=10)

        # -----------------------------------------
        # タイトル
        # -----------------------------------------

        self.ax.set_title(
            (f"{self.stream['title']}\n" f"{self.bin_seconds} sec/bin"),
            color="#f0f6fc",
            fontsize=12,
            pad=14,
        )

        # -----------------------------------------
        # Tick
        # -----------------------------------------

        # X
        self.ax.tick_params(axis="x", colors="#8b949e", length=0)

        # Mark
        self.ax.tick_params(axis="y", colors="#58a6ff", length=0)

        # Unique
        self.ax_right.tick_params(axis="y", colors="#d29922", length=0)

        # -----------------------------------------
        # 枠線
        # -----------------------------------------

        # 上下左右の枠を消す
        for spine in self.ax.spines.values():

            spine.set_visible(False)

        # -----------------------------------------
        # 凡例
        # -----------------------------------------

        mark_color = create_data_color(True, False, 1.0, 0.0)

        mixed_color = create_data_color(True, True, 1.0, 1.0)

        unique_color = create_data_color(False, True, 0.0, 1.0)

        legend = self.ax.legend(
            handles=[
                Patch(facecolor=mark_color, edgecolor="none", label="Mark"),
                Patch(facecolor=mixed_color, edgecolor="none", label="Mark + Unique"),
                Patch(facecolor=unique_color, edgecolor="none", label="Unique"),
            ],
            loc="upper left",
            frameon=False,
            fontsize=9,
        )

        for text in legend.get_texts():

            text.set_color("#8b949e")

        # -----------------------------------------
        # Hover Tooltip
        # -----------------------------------------

        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(14, 14),
            textcoords=("offset points"),
            bbox={"boxstyle": "round,pad=0.6", "fc": "#161b22", "ec": "#30363d"},
            color="#f0f6fc",
            fontsize=9,
            zorder=20,
        )

        self.annotation.set_visible(False)

        # -----------------------------------------
        # 更新
        # -----------------------------------------

        self.fig.canvas.draw_idle()

    # =====================================================
    # X軸
    # =====================================================

    def format_x_axis(self, value, position):

        seconds = int(value * self.bin_seconds)

        return seconds_to_time(seconds)

    # =====================================================
    # Mark軸
    # =====================================================

    def format_mark_axis(self, value, position):

        count = value / HEATMAP_GRID_ROWS * self.max_mark

        return str(int(round(count)))

    # =====================================================
    # Bin変更
    # =====================================================

    def on_bin_changed(self, value):

        # 秒数変更
        self.bin_seconds = int(value)

        # データ再生成
        self.rebuild_data()

        # Hover解除
        self.hover_bin = None

        # スクロールを先頭へ
        self.scroll_slider.set_val(0)

        self.draw()

    # =====================================================
    # Scroll変更
    # =====================================================

    def on_scroll_changed(self, value):

        # Hover解除
        self.hover_bin = None

        self.draw()

    # =====================================================
    # マウスホイール横スクロール
    # =====================================================

    def on_mouse_scroll(self, event):

        if event.inaxes != self.ax:
            return

        total_bins = len(self.mark_values)

        max_start = max(0, total_bins - HEATMAP_VISIBLE_COLUMNS)

        if max_start == 0:
            return

        current_start = self.get_visible_start()

        # 3マスずつ移動
        move = 3

        if event.button == "up":

            new_start = max(0, current_start - move)

        else:

            new_start = min(max_start, current_start + move)

        new_scroll = new_start / max_start * 100

        self.scroll_slider.set_val(new_scroll)

    # =====================================================
    # Hover
    # =====================================================

    def on_mouse_move(self, event):
        """
        マウス位置から
        最寄りの時間マスへSnapする
        """

        # -----------------------------------------
        # グラフ外
        # -----------------------------------------

        if event.inaxes != self.ax or event.xdata is None:

            if self.hover_bin is not None:

                self.hover_bin = None

                self.draw()

            return

        # -----------------------------------------
        # 時間ビン
        # -----------------------------------------

        bin_index = int(math.floor(event.xdata))

        # 範囲外
        if bin_index < 0 or bin_index >= len(self.mark_values):
            return

        # -----------------------------------------
        # 値
        # -----------------------------------------

        mark_count = int(self.mark_values[bin_index])

        unique_count = int(self.unique_values[bin_index])

        # -----------------------------------------
        # データなし
        # -----------------------------------------

        if mark_count == 0 and unique_count == 0:

            if self.hover_bin is not None:

                self.hover_bin = None

                self.draw()

            return

        # -----------------------------------------
        # Hover対象が変わった場合だけ再描画
        # -----------------------------------------

        if self.hover_bin != bin_index:

            self.hover_bin = bin_index

            self.draw()

        # -----------------------------------------
        # 時間
        # -----------------------------------------

        start_seconds = bin_index * self.bin_seconds

        end_seconds = min(self.stream["duration"], start_seconds + self.bin_seconds)

        # -----------------------------------------
        # Tooltip
        # -----------------------------------------

        text = (
            f"{seconds_to_time(start_seconds)}"
            f" - "
            f"{seconds_to_time(end_seconds)}\n"
            f"Mark      {mark_count}\n"
            f"Unique    {unique_count}\n"
            f"Candidates "
            f"{len(self.candidate_ids[bin_index])}"
        )

        # -----------------------------------------
        # Tooltip位置
        # -----------------------------------------

        mark_ratio = mark_count / self.max_mark

        unique_ratio = unique_count / self.max_unique

        height = max(mark_ratio, unique_ratio) * HEATMAP_GRID_ROWS

        self.annotation.xy = (
            bin_index + 0.5,
            min(HEATMAP_GRID_ROWS - 0.5, max(0.5, height)),
        )

        self.annotation.set_text(text)

        self.annotation.set_visible(True)

        self.fig.canvas.draw_idle()

    # =====================================================
    # 表示
    # =====================================================

    def show(self):

        plt.show()


# =========================================================
# 外部呼び出し
# =========================================================


def plot_mark_unique_heatmap(live_id):

    heatmap = MarkUniqueHeatmap(live_id)

    heatmap.show()
