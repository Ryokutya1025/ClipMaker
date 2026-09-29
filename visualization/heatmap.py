import math

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FixedLocator, FuncFormatter
from matplotlib.widgets import Slider

from config import (
    HEATMAP_BIN_STEP,
    HEATMAP_DEFAULT_BIN,
    HEATMAP_GRID_ROWS,
    HEATMAP_MAX_BIN,
    HEATMAP_MIN_BIN,
    HEATMAP_RENDER_HEIGHT,
    HEATMAP_RENDER_WIDTH,
    HEATMAP_SCROLL_STEP,
    HEATMAP_VISIBLE_COLUMNS,
)
from database.connection import get_connection
from time_utils import seconds_to_time
from visualization.colors import (
    BACKGROUND_COLOR,
    EMPTY_CELL_COLOR,
    MARK_AXIS_COLOR,
    MARK_BASE_COLOR,
    TEXT_PRIMARY_COLOR,
    TEXT_SECONDARY_COLOR,
    UNIQUE_AXIS_COLOR,
    UNIQUE_BASE_COLOR,
    mark_color,
    unique_color,
)

# =========================================================
# Matplotlib日本語フォント設定
# =========================================================


def configure_japanese_font():
    """
    macOS / Windows / Linuxで見つかりやすい日本語フォントを順に探し、
    Matplotlibへ設定する。

    macOSでは通常 Hiragino Sans が選ばれる。
    """

    candidates = [
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Yu Gothic",
        "YuGothic",
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "IPAexGothic",
        "IPAGothic",
        "TakaoGothic",
    ]

    available_fonts = {font.name for font in font_manager.fontManager.ttflist}

    selected_font = None

    for font_name in candidates:
        if font_name in available_fonts:
            selected_font = font_name
            break

    if selected_font is not None:
        plt.rcParams["font.family"] = selected_font

    else:
        plt.rcParams["font.family"] = "sans-serif"

        plt.rcParams["font.sans-serif"] = candidates + [
            "DejaVu Sans",
        ]

    # マイナス記号の文字化け防止
    plt.rcParams["axes.unicode_minus"] = False

    return selected_font


# =========================================================
# Y軸最大値計算
# =========================================================


def get_axis_max(value):
    """
    データの最大値より少し大きいY軸最大値を返す。

    最大値をそのままY軸上限にすると、
    一番高いグラフが上端に張り付いて見えるため、
    約20%の余白を持たせる。

    さらにY軸を4分割したとき、
    目盛りが整数になるように調整する。

    例
    ----------
    1  -> 4
    5  -> 8
    9  -> 12
    15 -> 20
    """

    if value <= 0:
        return 1

    # 最大値より20%上を目標にする
    target = value * 1.2

    # Y軸を4分割した際に整数になるようにする
    tick_step = max(
        1,
        math.ceil(target / 4),
    )

    axis_max = tick_step * 4

    return axis_max


# =========================================================
# 配信情報取得
# =========================================================


def get_stream(live_id):
    """
    streamsテーブルから指定された配信情報を取得する。
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

    if row is None:
        return None

    return dict(row)


# =========================================================
# Mark / Unique取得
# =========================================================


def get_mark_unique(stream_id):
    """
    mark_uniqueテーブルから指定された配信の解析結果を取得する。
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


def create_bins(
    duration,
    mark_unique_list,
    bin_seconds,
):
    """
    mark_uniqueの範囲を、
    指定秒数ごとの時間ビンへ展開する。

    戻り値
    ----------
    mark_values:
        各時間ビンのMark数

    unique_values:
        各時間ビンのUnique数

    candidate_ids:
        各時間ビンに含まれるmark_unique.idの一覧
    """

    bin_count = max(
        1,
        math.ceil(duration / bin_seconds),
    )

    mark_values = np.zeros(
        bin_count,
        dtype=int,
    )

    unique_values = np.zeros(
        bin_count,
        dtype=int,
    )

    candidate_ids = [[] for _ in range(bin_count)]

    for item in mark_unique_list:

        start_time = max(
            0,
            int(item["start_time"]),
        )

        end_time = min(
            duration,
            int(item["end_time"]),
        )

        if end_time <= start_time:
            continue

        start_bin = start_time // bin_seconds

        end_bin = (end_time - 1) // bin_seconds

        end_bin = min(
            bin_count - 1,
            end_bin,
        )

        for bin_index in range(
            start_bin,
            end_bin + 1,
        ):

            mark_values[bin_index] += int(item["mark_count"])

            unique_values[bin_index] += int(item["unique_count"])

            candidate_ids[bin_index].append(item["id"])

    return (
        mark_values,
        unique_values,
        candidate_ids,
    )


# =========================================================
# 左Mark / 右Unique の画像生成
# =========================================================


def create_split_heatmap_image(
    mark_values,
    unique_values,
    max_mark,
    max_unique,
):
    """
    1時間ビンを左右に分割した
    ヒートマップ画像を生成する。

    左半分:
        Mark = 緑

    右半分:
        Unique = 黄

    FancyBboxPatchを大量に生成せず、
    RGBA画像を1枚だけ描画することで、
    スクロール時の再描画負荷を減らす。
    """

    bin_count = len(mark_values)

    render_width = max(
        6,
        int(HEATMAP_RENDER_WIDTH),
    )

    render_height = max(
        3,
        int(HEATMAP_RENDER_HEIGHT),
    )

    image_width = bin_count * render_width

    image_height = HEATMAP_GRID_ROWS * render_height

    image = np.empty(
        (
            image_height,
            image_width,
            4,
        ),
        dtype=float,
    )

    image[
        :,
        :,
        :3,
    ] = EMPTY_CELL_COLOR

    image[
        :,
        :,
        3,
    ] = 1.0

    # 各セルの上下に隙間
    y_inner_start = 1

    y_inner_end = max(
        y_inner_start + 1,
        render_height - 1,
    )

    # 1区間内の左右レイアウト
    #
    # [余白][Mark][隙間][Unique][余白]

    outer_gap = 1

    center_gap = 1

    usable_width = render_width - outer_gap * 2 - center_gap

    half_width = max(
        1,
        usable_width // 2,
    )

    mark_x_start_offset = outer_gap

    mark_x_end_offset = mark_x_start_offset + half_width

    unique_x_end_offset = render_width - outer_gap

    unique_x_start_offset = unique_x_end_offset - half_width

    for bin_index in range(bin_count):

        mark_count = int(mark_values[bin_index])

        unique_count = int(unique_values[bin_index])

        if max_mark:
            mark_ratio = mark_count / max_mark

        else:
            mark_ratio = 0.0

        if max_unique:
            unique_ratio = unique_count / max_unique

        else:
            unique_ratio = 0.0

        mark_height = math.ceil(mark_ratio * HEATMAP_GRID_ROWS)

        unique_height = math.ceil(unique_ratio * HEATMAP_GRID_ROWS)

        mark_rgb = mark_color(mark_ratio)

        unique_rgb = unique_color(unique_ratio)

        base_x = bin_index * render_width

        mark_x0 = base_x + mark_x_start_offset

        mark_x1 = base_x + mark_x_end_offset

        unique_x0 = base_x + unique_x_start_offset

        unique_x1 = base_x + unique_x_end_offset

        for row in range(HEATMAP_GRID_ROWS):

            base_y = row * render_height

            y0 = base_y + y_inner_start

            y1 = base_y + y_inner_end

            if row < mark_height:

                image[
                    y0:y1,
                    mark_x0:mark_x1,
                    :3,
                ] = mark_rgb

            if row < unique_height:

                image[
                    y0:y1,
                    unique_x0:unique_x1,
                    :3,
                ] = unique_rgb

    return image


# =========================================================
# ヒートマップ
# =========================================================


class MarkUniqueHeatmap:

    def __init__(
        self,
        live_id,
    ):

        # -----------------------------------------
        # 日本語フォント
        # -----------------------------------------

        self.selected_font = configure_japanese_font()

        # -----------------------------------------
        # 配信情報
        # -----------------------------------------

        self.stream = get_stream(live_id)

        if self.stream is None:

            raise ValueError("指定された配信が" "streamsテーブルに" "存在しません。")

        # -----------------------------------------
        # Mark / Unique情報
        # -----------------------------------------

        self.mark_unique_list = get_mark_unique(self.stream["id"])

        if not self.mark_unique_list:

            raise ValueError("mark_uniqueテーブルに" "対象データがありません。")

        # -----------------------------------------
        # 状態
        # -----------------------------------------

        self.bin_seconds = HEATMAP_DEFAULT_BIN

        self.mark_values = np.array(
            [],
            dtype=int,
        )

        self.unique_values = np.array(
            [],
            dtype=int,
        )

        self.candidate_ids = []

        self.max_mark = 1

        self.max_unique = 1

        self.hover_bin = None

        self._updating_scroll_slider = False

        # -----------------------------------------
        # Figure
        # -----------------------------------------

        self.fig = plt.figure(
            figsize=(
                16,
                8,
            )
        )

        self.fig.patch.set_facecolor(BACKGROUND_COLOR)

        # -----------------------------------------
        # グラフ本体
        # -----------------------------------------

        self.ax = self.fig.add_axes(
            [
                0.075,
                0.22,
                0.85,
                0.66,
            ]
        )

        self.ax.set_facecolor(BACKGROUND_COLOR)

        self.ax_right = None

        self.image_artist = None

        # -----------------------------------------
        # Hover表示
        # -----------------------------------------

        self.hover_patch = Rectangle(
            (
                0,
                0,
            ),
            1,
            HEATMAP_GRID_ROWS,
            facecolor=(
                1.0,
                1.0,
                1.0,
                0.035,
            ),
            edgecolor="#f0f6fc",
            linewidth=0.8,
            zorder=8,
            visible=False,
        )

        self.ax.add_patch(self.hover_patch)

        self.annotation = self.ax.annotate(
            "",
            xy=(
                0,
                0,
            ),
            xytext=(
                14,
                14,
            ),
            textcoords=("offset points"),
            bbox={
                "boxstyle": "round,pad=0.6",
                "fc": "#161b22",
                "ec": "#30363d",
            },
            color=(TEXT_PRIMARY_COLOR),
            fontsize=9,
            zorder=20,
        )

        self.annotation.set_visible(False)

        # -----------------------------------------
        # Bin Slider
        # -----------------------------------------

        bin_ax = self.fig.add_axes(
            [
                0.16,
                0.105,
                0.56,
                0.030,
            ]
        )

        bin_ax.set_facecolor("#161b22")

        self.bin_slider = Slider(
            ax=bin_ax,
            label="区間",
            valmin=(HEATMAP_MIN_BIN),
            valmax=(HEATMAP_MAX_BIN),
            valinit=(HEATMAP_DEFAULT_BIN),
            valstep=(HEATMAP_BIN_STEP),
            valfmt="%0.0f 秒",
        )

        # -----------------------------------------
        # Scroll Slider
        # -----------------------------------------

        scroll_ax = self.fig.add_axes(
            [
                0.16,
                0.050,
                0.56,
                0.030,
            ]
        )

        scroll_ax.set_facecolor("#161b22")

        self.scroll_slider = Slider(
            ax=scroll_ax,
            label="時間位置",
            valmin=0.0,
            valmax=100.0,
            valinit=0.0,
            # 連続値で動かす
            valstep=None,
            valfmt="%0.1f%%",
        )

        for slider in (
            self.bin_slider,
            self.scroll_slider,
        ):

            slider.label.set_color(TEXT_SECONDARY_COLOR)

            slider.valtext.set_color("#c9d1d9")

        # -----------------------------------------
        # Event
        # -----------------------------------------

        self.bin_slider.on_changed(self.on_bin_changed)

        self.scroll_slider.on_changed(self.on_scroll_changed)

        self.fig.canvas.mpl_connect(
            "motion_notify_event",
            self.on_mouse_move,
        )

        self.fig.canvas.mpl_connect(
            "scroll_event",
            self.on_mouse_scroll,
        )

        # -----------------------------------------
        # 初期描画
        # -----------------------------------------

        self.rebuild_data()

        self.setup_axes()

        self.rebuild_image()

        self.update_view()

    # =====================================================
    # データ再生成
    # =====================================================

    def rebuild_data(self):
        """
        現在のbin_secondsを使って
        ヒートマップデータを再生成する。
        """

        (
            self.mark_values,
            self.unique_values,
            self.candidate_ids,
        ) = create_bins(
            duration=(self.stream["duration"]),
            mark_unique_list=(self.mark_unique_list),
            bin_seconds=(self.bin_seconds),
        )

        # -----------------------------------------
        # 実データ最大値
        # -----------------------------------------

        raw_max_mark = max(
            1,
            int(self.mark_values.max()),
        )

        raw_max_unique = max(
            1,
            int(self.unique_values.max()),
        )

        # -----------------------------------------
        # Y軸に余白を追加
        # -----------------------------------------

        self.max_mark = get_axis_max(raw_max_mark)

        self.max_unique = get_axis_max(raw_max_unique)

    # =====================================================
    # 軸の初期化 / 更新
    # =====================================================

    def setup_axes(self):
        """
        軸・凡例・タイトルを設定する。

        スクロールごとには作り直さず、
        Bin変更時だけ更新する。
        """

        if self.ax_right is not None:

            self.ax_right.remove()

            self.ax_right = None

        self.ax.set_ylim(
            0,
            HEATMAP_GRID_ROWS,
        )

        # -----------------------------------------
        # 左Y軸 Mark
        # -----------------------------------------

        left_grid_ticks = np.linspace(
            0,
            HEATMAP_GRID_ROWS,
            5,
        )

        self.ax.set_yticks(left_grid_ticks)

        self.ax.yaxis.set_major_formatter(FuncFormatter(self.format_mark_axis))

        # -----------------------------------------
        # 右Y軸 Unique
        # -----------------------------------------

        def grid_to_unique(grid_value):

            return grid_value / HEATMAP_GRID_ROWS * self.max_unique

        def unique_to_grid(unique_value):

            if self.max_unique <= 0:
                return 0

            return unique_value / self.max_unique * HEATMAP_GRID_ROWS

        self.ax_right = self.ax.secondary_yaxis(
            "right",
            functions=(
                grid_to_unique,
                unique_to_grid,
            ),
        )

        unique_ticks = np.linspace(
            0,
            self.max_unique,
            5,
        )

        self.ax_right.set_yticks(unique_ticks)

        self.ax_right.yaxis.set_major_formatter(
            FuncFormatter(lambda value, position: str(int(round(value))))
        )

        # -----------------------------------------
        # ラベル
        # -----------------------------------------

        self.ax.set_xlabel(
            "配信時間",
            color=(TEXT_SECONDARY_COLOR),
            labelpad=12,
        )

        self.ax.set_ylabel(
            "Mark数",
            color=(MARK_AXIS_COLOR),
            labelpad=10,
        )

        self.ax_right.set_ylabel(
            "Unique数",
            color=(UNIQUE_AXIS_COLOR),
            labelpad=10,
        )

        # -----------------------------------------
        # タイトル
        # -----------------------------------------

        self.ax.set_title(
            (
                f"{self.stream['title']}\n"
                f"1区間 "
                f"{self.bin_seconds} 秒   "
                f"左: Mark / 右: Unique"
            ),
            color=(TEXT_PRIMARY_COLOR),
            fontsize=12,
            pad=14,
        )

        # -----------------------------------------
        # Tick色
        # -----------------------------------------

        self.ax.tick_params(
            axis="x",
            colors=(TEXT_SECONDARY_COLOR),
            length=0,
        )

        self.ax.tick_params(
            axis="y",
            colors=(MARK_AXIS_COLOR),
            length=0,
        )

        self.ax_right.tick_params(
            axis="y",
            colors=(UNIQUE_AXIS_COLOR),
            length=0,
        )

        # -----------------------------------------
        # 枠線
        # -----------------------------------------

        for spine in self.ax.spines.values():

            spine.set_visible(False)

        # -----------------------------------------
        # 凡例
        # -----------------------------------------

        legend = self.ax.legend(
            handles=[
                Patch(
                    facecolor=(MARK_BASE_COLOR),
                    edgecolor="none",
                    label=("Mark（左）"),
                ),
                Patch(
                    facecolor=(UNIQUE_BASE_COLOR),
                    edgecolor="none",
                    label=("Unique（右）"),
                ),
            ],
            loc="upper left",
            frameon=False,
            fontsize=9,
        )

        for text in legend.get_texts():

            text.set_color(TEXT_SECONDARY_COLOR)

    # =====================================================
    # ヒートマップ画像再生成
    # =====================================================

    def rebuild_image(self):
        """
        Mark左 / Unique右 の
        RGBA画像を生成する。

        スクロール時は画像を作り直さず、
        xlimだけ移動する。
        """

        image = create_split_heatmap_image(
            mark_values=(self.mark_values),
            unique_values=(self.unique_values),
            max_mark=(self.max_mark),
            max_unique=(self.max_unique),
        )

        total_bins = len(self.mark_values)

        if self.image_artist is None:

            self.image_artist = self.ax.imshow(
                image,
                origin="lower",
                interpolation=("nearest"),
                aspect="auto",
                extent=(
                    0,
                    total_bins,
                    0,
                    HEATMAP_GRID_ROWS,
                ),
                zorder=2,
            )

        else:

            self.image_artist.set_data(image)

            self.image_artist.set_extent(
                (
                    0,
                    total_bins,
                    0,
                    HEATMAP_GRID_ROWS,
                )
            )

        self.hover_patch.set_zorder(8)

        self.annotation.set_zorder(20)

    # =====================================================
    # 表示開始位置
    # =====================================================

    def get_max_start(self):

        total_bins = len(self.mark_values)

        return max(
            0.0,
            total_bins - HEATMAP_VISIBLE_COLUMNS,
        )

    def get_visible_start(self):
        """
        Scroll Sliderから
        表示開始位置を連続値で計算する。
        """

        max_start = self.get_max_start()

        if max_start <= 0:
            return 0.0

        ratio = self.scroll_slider.val / 100.0

        return max_start * ratio

    # =====================================================
    # X軸更新
    # =====================================================

    def update_x_axis(
        self,
        start_bin,
        end_bin,
    ):
        """
        現在見えている範囲に合わせて
        X軸ラベルを更新する。
        """

        visible_count = max(
            1.0,
            end_bin - start_bin,
        )

        # 約6個のラベルを表示
        tick_step = max(
            1,
            int(math.ceil(visible_count / 6)),
        )

        first_tick = math.ceil(start_bin / tick_step) * tick_step

        last_tick = math.floor(end_bin / tick_step) * tick_step

        if last_tick < first_tick:

            x_ticks = [start_bin]

        else:

            x_ticks = list(
                np.arange(
                    first_tick,
                    last_tick + tick_step * 0.5,
                    tick_step,
                )
            )

        self.ax.xaxis.set_major_locator(FixedLocator(x_ticks))

        self.ax.xaxis.set_major_formatter(FuncFormatter(self.format_x_axis))

    # =====================================================
    # 表示範囲更新
    # =====================================================

    def update_view(self):
        """
        スクロール位置だけを更新する。

        セルを作り直さないので、
        描画負荷を抑えられる。
        """

        total_bins = len(self.mark_values)

        if total_bins <= 0:
            return

        if total_bins <= HEATMAP_VISIBLE_COLUMNS:

            start_bin = 0.0

            end_bin = float(total_bins)

        else:

            start_bin = self.get_visible_start()

            end_bin = min(
                float(total_bins),
                start_bin + HEATMAP_VISIBLE_COLUMNS,
            )

        if end_bin <= start_bin:

            end_bin = start_bin + 1.0

        self.ax.set_xlim(
            start_bin,
            end_bin,
        )

        self.update_x_axis(
            start_bin,
            end_bin,
        )

        if self.hover_bin is not None:

            if not (start_bin <= self.hover_bin < end_bin):

                self.clear_hover(draw=False)

        self.fig.canvas.draw_idle()

    # =====================================================
    # X軸フォーマット
    # =====================================================

    def format_x_axis(
        self,
        value,
        position,
    ):

        seconds = max(
            0,
            int(round(value * self.bin_seconds)),
        )

        return seconds_to_time(seconds)

    # =====================================================
    # Mark軸フォーマット
    # =====================================================

    def format_mark_axis(
        self,
        value,
        position,
    ):

        count = value / HEATMAP_GRID_ROWS * self.max_mark

        return str(int(round(count)))

    # =====================================================
    # Bin変更
    # =====================================================

    def on_bin_changed(
        self,
        value,
    ):

        self.bin_seconds = int(value)

        self.rebuild_data()

        self.clear_hover(draw=False)

        self._updating_scroll_slider = True

        self.scroll_slider.set_val(0.0)

        self._updating_scroll_slider = False

        self.setup_axes()

        self.rebuild_image()

        self.update_view()

    # =====================================================
    # Scroll Slider変更
    # =====================================================

    def on_scroll_changed(
        self,
        value,
    ):

        if self._updating_scroll_slider:
            return

        self.update_view()

    # =====================================================
    # マウスホイール横スクロール
    # =====================================================

    def on_mouse_scroll(
        self,
        event,
    ):

        if event.inaxes != self.ax:
            return

        max_start = self.get_max_start()

        if max_start <= 0:
            return

        current_start = self.get_visible_start()

        step = getattr(
            event,
            "step",
            0.0,
        )

        if step == 0:

            if event.button == "up":
                step = 1.0

            elif event.button == "down":
                step = -1.0

        new_start = current_start - step * HEATMAP_SCROLL_STEP

        new_start = float(
            np.clip(
                new_start,
                0.0,
                max_start,
            )
        )

        new_scroll = new_start / max_start * 100.0

        self.scroll_slider.set_val(new_scroll)

    # =====================================================
    # Hover解除
    # =====================================================

    def clear_hover(
        self,
        draw=True,
    ):

        self.hover_bin = None

        self.hover_patch.set_visible(False)

        self.annotation.set_visible(False)

        if draw:
            self.fig.canvas.draw_idle()

    # =====================================================
    # Hover
    # =====================================================

    def on_mouse_move(
        self,
        event,
    ):
        """
        マウス位置から時間ビンへSnapし、
        Mark / UniqueをTooltip表示する。
        """

        if event.inaxes != self.ax or event.xdata is None:

            if self.hover_bin is not None:

                self.clear_hover()

            return

        bin_index = int(math.floor(event.xdata))

        if bin_index < 0 or bin_index >= len(self.mark_values):

            if self.hover_bin is not None:

                self.clear_hover()

            return

        mark_count = int(self.mark_values[bin_index])

        unique_count = int(self.unique_values[bin_index])

        if mark_count == 0 and unique_count == 0:

            if self.hover_bin is not None:

                self.clear_hover()

            return

        start_seconds = bin_index * self.bin_seconds

        end_seconds = min(
            self.stream["duration"],
            start_seconds + self.bin_seconds,
        )

        text = (
            f"{seconds_to_time(start_seconds)}"
            f" - "
            f"{seconds_to_time(end_seconds)}\n"
            f"Mark       {mark_count}\n"
            f"Unique     {unique_count}\n"
            f"候補数      "
            f"{len(self.candidate_ids[bin_index])}"
        )

        mark_ratio = mark_count / self.max_mark

        unique_ratio = unique_count / self.max_unique

        height = (
            max(
                mark_ratio,
                unique_ratio,
            )
            * HEATMAP_GRID_ROWS
        )

        self.hover_bin = bin_index

        self.hover_patch.set_x(bin_index)

        self.hover_patch.set_visible(True)

        self.annotation.xy = (
            bin_index + 0.5,
            min(
                HEATMAP_GRID_ROWS - 0.5,
                max(
                    0.5,
                    height,
                ),
            ),
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


def plot_mark_unique_heatmap(
    live_id,
):

    heatmap = MarkUniqueHeatmap(live_id)

    heatmap.show()
