from config import LOG_PATH

from log_parser import get_info

from mark import create_marks, merge_marks

from time_utils import seconds_to_time

from database.schema import create_tables
from database.repository import save_analysis

# =========================================================
# main
# =========================================================


def main():

    # -----------------------------------------
    # データベース初期化
    # -----------------------------------------

    # 必要なテーブルを作成
    create_tables()

    # -----------------------------------------
    # コメント情報取得
    # -----------------------------------------

    # ログファイルからコメント情報を抽出
    comment_info_list = get_info(LOG_PATH)

    # -----------------------------------------
    # Mark生成
    # -----------------------------------------

    # コメント情報からMark一覧を生成
    mark_list = create_marks(comment_info_list)

    # -----------------------------------------
    # Mark結合
    # -----------------------------------------

    # 重なっているMarkを連鎖的に結合
    clip_list = merge_marks(mark_list)

    # -----------------------------------------
    # データベース登録
    # -----------------------------------------

    # 配信情報
    # キーワードコメント
    # Mark / Unique集計結果
    # をデータベースへ保存
    save_analysis(comment_info_list, mark_list, clip_list)

    # -----------------------------------------
    # 確認表示
    # -----------------------------------------

    for index, clip in enumerate(clip_list, start=1):

        # 開始時刻を表示用へ変換
        start_time = seconds_to_time(clip["start_time"])

        # 終了時刻を表示用へ変換
        end_time = seconds_to_time(clip["end_time"])

        print(
            f"===== Clip {index} =====\n"
            f"配信ID: {clip['live_id']}\n"
            f"開始時刻: {start_time}\n"
            f"終了時刻: {end_time}\n"
            f"Mark数: {clip['mark_count']}\n"
            f"Unique数: {clip['unique_count']}\n"
        )

    # 後続処理で使用できるよう返す
    return clip_list


if __name__ == "__main__":
    main()
