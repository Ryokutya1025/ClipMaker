from datetime import datetime

# =========================================================
# コメント時刻を配信開始からの経過秒数へ変換
# =========================================================


def convert_comment_time(timestamp, live_info):
    """
    コメントのISO形式時刻を
    配信開始からの経過秒数へ変換する
    """

    # ISO形式のコメント時刻をdatetime型へ変換
    comment_datetime = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    # datetime型をUnix timestampへ変換
    comment_timestamp = comment_datetime.timestamp()

    # 配信開始からコメント投稿までの経過秒数を計算
    total_seconds = int(comment_timestamp - live_info["start_timestamp"])

    # 配信開始前のコメントを除外
    if total_seconds < 0:
        return None

    # 配信終了後のコメントを除外
    if total_seconds > live_info["duration"]:
        return None

    # 配信開始からの経過秒数を返す
    return total_seconds


# =========================================================
# 秒数 → HH:MM:SS
# =========================================================


def seconds_to_time(total_seconds):
    """
    秒数を表示用のHH:MM:SS形式へ変換する
    """

    # 時間を計算
    hours = total_seconds // 3600

    # 分を計算
    minutes = (total_seconds % 3600) // 60

    # 秒を計算
    seconds = total_seconds % 60

    # HH:MM:SS形式の文字列を返す
    return f"{hours:02}:" f"{minutes:02}:" f"{seconds:02}"
