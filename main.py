from config import LOG_PATH

from log_parser import get_info

from mark import create_marks, merge_marks

from database.schema import create_tables
from database.repository import save_analysis

from visualization.heatmap import plot_mark_unique_heatmap

from debug import print_marks, print_clips

# =========================================================
# 設定
# =========================================================

DEBUG = True


# =========================================================
# main
# =========================================================


def main():

    # DB初期化
    create_tables()

    # ログ解析
    comments = get_info(LOG_PATH)

    if not comments:
        print("コメントデータがありません。")
        return

    # Mark生成
    marks = create_marks(comments)

    # Mark結合
    clips = merge_marks(marks)

    # テスト表示
    if DEBUG:
        print_marks(marks)
        print_clips(clips)

    # DB保存
    save_analysis(comments, marks, clips)

    # グラフ表示
    plot_mark_unique_heatmap(comments[0]["live_id"])


if __name__ == "__main__":
    main()
