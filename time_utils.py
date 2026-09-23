from datetime import datetime

# =========================================================
# コメント時刻 → 配信開始からの秒数
# =========================================================


def convert_comment_time(timestamp, live_info):
    """
    コメント投稿時刻を
    配信開始からの経過秒数へ変換する
    """

    # ISO形式 → datetime
    comment_datetime = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    # datetime → Unix timestamp
    comment_timestamp = comment_datetime.timestamp()

    # 配信開始からの経過秒数
    total_seconds = int(comment_timestamp - live_info["start_timestamp"])

    # 配信開始前
    if total_seconds < 0:
        return None

    # 配信終了後
    if total_seconds > live_info["duration"]:
        return None

    return total_seconds


# =========================================================
# 秒数 → HH:MM:SS
# =========================================================


def seconds_to_time(total_seconds):

    total_seconds = max(0, int(total_seconds))

    hours = total_seconds // 3600

    minutes = (total_seconds % 3600) // 60

    seconds = total_seconds % 60

    return f"{hours:02}:" f"{minutes:02}:" f"{seconds:02}"
