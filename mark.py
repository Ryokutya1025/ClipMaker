from config import KEYWORD, CLIP_FRONT_TIME, CLIP_REAR_TIME

# =========================================================
# Mark生成
# =========================================================


def create_mark(comment_info):
    """
    キーワードを含むコメントから
    Mark情報を生成する
    """

    # キーワードが含まれていない
    if KEYWORD not in comment_info["comment"]:
        return None

    # Markされた時刻
    mark_time = comment_info["timestamp"]

    # クリップ開始
    start_time = max(0, mark_time - CLIP_FRONT_TIME)

    # クリップ終了
    end_time = min(comment_info["duration"], mark_time + CLIP_REAR_TIME)

    return {
        "live_id": comment_info["live_id"],
        "user_id": comment_info["user_id"],
        "name": comment_info["name"],
        "mark_time": mark_time,
        "start_time": start_time,
        "end_time": end_time,
        "comment": comment_info["comment"],
    }


# =========================================================
# Mark一覧生成
# =========================================================


def create_marks(comment_info_list):

    mark_list = []

    for comment_info in comment_info_list:

        mark = create_mark(comment_info)

        if mark is None:
            continue

        mark_list.append(mark)

    return mark_list


# =========================================================
# Mark数・Unique数集計
# =========================================================


def calculate_clip_stats(clip):
    """
    結合済みクリップ候補に含まれる
    Mark数とUnique数を集計する
    """

    # Mark数
    clip["mark_count"] = len(clip["marks"])

    # Uniqueユーザー
    unique_users = {mark["user_id"] for mark in clip["marks"] if mark["user_id"]}

    # Unique数
    clip["unique_count"] = len(unique_users)

    return clip


# =========================================================
# Mark連鎖結合
# =========================================================


def merge_marks(mark_list):
    """
    時間範囲の重なっているMarkを
    連鎖的に結合する
    """

    if not mark_list:
        return []

    # 配信ID・開始時刻順
    sorted_marks = sorted(
        mark_list,
        key=lambda mark: (mark["live_id"], mark["start_time"], mark["mark_time"]),
    )

    clip_list = []

    # 最初のMark
    first = sorted_marks[0]

    current_clip = {
        "live_id": first["live_id"],
        "start_time": first["start_time"],
        "end_time": first["end_time"],
        "marks": [first],
    }

    # 2件目以降
    for mark in sorted_marks[1:]:

        same_live = mark["live_id"] == current_clip["live_id"]

        overlapping = mark["start_time"] <= current_clip["end_time"]

        # 連鎖結合
        if same_live and overlapping:

            current_clip["end_time"] = max(current_clip["end_time"], mark["end_time"])

            current_clip["marks"].append(mark)

        else:

            clip_list.append(calculate_clip_stats(current_clip))

            current_clip = {
                "live_id": mark["live_id"],
                "start_time": mark["start_time"],
                "end_time": mark["end_time"],
                "marks": [mark],
            }

    # 最後の候補
    clip_list.append(calculate_clip_stats(current_clip))

    return clip_list
