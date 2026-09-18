from config import KEYWORD, CLIP_FRONT_TIME, CLIP_REAR_TIME

# =========================================================
# Mark生成
# =========================================================


def create_mark(comment_info):
    """
    キーワードを含むコメントから
    クリップ候補となるMark情報を生成する
    """

    # 指定キーワードを含まないコメントは除外
    if KEYWORD not in comment_info["comment"]:
        return None

    # Markされた時刻
    mark_time = comment_info["timestamp"]

    # クリップ開始時刻
    start_time = max(0, mark_time - CLIP_FRONT_TIME)

    # クリップ終了時刻
    end_time = mark_time + CLIP_REAR_TIME

    # 配信時間がコメント情報に含まれている場合
    if "duration" in comment_info:

        # 配信終了時刻を超えないように補正
        end_time = min(comment_info["duration"], end_time)

    # Mark情報を辞書で返す
    return {
        # YouTube配信ID
        "live_id": comment_info["live_id"],
        # MarkしたユーザーID
        "user_id": comment_info["user_id"],
        # Markしたユーザー名
        "name": comment_info["name"],
        # Markされた時刻
        "mark_time": mark_time,
        # クリップ候補開始時刻
        "start_time": start_time,
        # クリップ候補終了時刻
        "end_time": end_time,
        # Mark元コメント
        "comment": comment_info["comment"],
    }


# =========================================================
# Mark一覧生成
# =========================================================


def create_marks(comment_info_list):
    """
    コメント一覧からキーワードを含むコメントを抽出し、
    Mark一覧を生成する
    """

    # Mark情報を保存するリスト
    mark_list = []

    # コメント情報を1件ずつ処理
    for comment_info in comment_info_list:

        # コメント情報からMarkを生成
        mark = create_mark(comment_info)

        # Mark対象ではないコメントを除外
        if mark is None:
            continue

        # Mark一覧へ追加
        mark_list.append(mark)

    # Mark一覧を返す
    return mark_list


# =========================================================
# Mark結合
# =========================================================


def merge_marks(mark_list):
    """
    時間範囲が重なっているMarkを連鎖的に結合し、
    クリップ候補一覧を生成する

    例:
        A: 03:30 ～ 04:15
        B: 04:00 ～ 04:45
        C: 04:30 ～ 05:15

    AとBが重なり、
    結合後の範囲とCも重なるため、
    最終的に03:30 ～ 05:15として結合する
    """

    # Markが存在しない場合
    if not mark_list:
        return []

    # 配信ID → 開始時間 → Mark時間の順番で並び替え
    sorted_marks = sorted(
        mark_list,
        key=lambda mark: (mark["live_id"], mark["start_time"], mark["mark_time"]),
    )

    # 結合済みクリップ候補を保存するリスト
    clip_list = []

    # -----------------------------------------
    # 最初のMarkからクリップ候補を作成
    # -----------------------------------------

    first_mark = sorted_marks[0]

    current_clip = {
        # YouTube配信ID
        "live_id": first_mark["live_id"],
        # クリップ開始時刻
        "start_time": first_mark["start_time"],
        # クリップ終了時刻
        "end_time": first_mark["end_time"],
        # このクリップ候補に含まれるMark
        "marks": [first_mark],
    }

    # -----------------------------------------
    # 2件目以降のMarkを確認
    # -----------------------------------------

    for mark in sorted_marks[1:]:

        # 同じ配信かどうか
        same_live = mark["live_id"] == current_clip["live_id"]

        # 現在のクリップ範囲とMarkが重なっているか
        overlapping = mark["start_time"] <= current_clip["end_time"]

        # 同じ配信かつ時間範囲が重なっている場合
        if same_live and overlapping:

            # クリップ終了時刻を必要に応じて延長
            current_clip["end_time"] = max(current_clip["end_time"], mark["end_time"])

            # Markを現在のクリップ候補へ追加
            current_clip["marks"].append(mark)

        else:

            # 現在のクリップ候補の集計を行う
            current_clip = calculate_clip_stats(current_clip)

            # 完成したクリップ候補を保存
            clip_list.append(current_clip)

            # 新しいクリップ候補を作成
            current_clip = {
                # YouTube配信ID
                "live_id": mark["live_id"],
                # クリップ開始時刻
                "start_time": mark["start_time"],
                # クリップ終了時刻
                "end_time": mark["end_time"],
                # このクリップ候補に含まれるMark
                "marks": [mark],
            }

    # 最後のクリップ候補を集計
    current_clip = calculate_clip_stats(current_clip)

    # 最後のクリップ候補を保存
    clip_list.append(current_clip)

    # 結合済みクリップ候補一覧を返す
    return clip_list


# =========================================================
# Mark数・ユニーク数集計
# =========================================================


def calculate_clip_stats(clip):
    """
    クリップ候補に含まれる
    Mark数とユニークユーザー数を集計する
    """

    # このクリップ候補に含まれるMark数
    mark_count = len(clip["marks"])

    # ユニークユーザーIDを保存する集合
    unique_users = set()

    # Markを1件ずつ確認
    for mark in clip["marks"]:

        # ユーザーIDを取得
        user_id = mark["user_id"]

        # ユーザーIDが存在する場合
        if user_id:

            # 集合へ追加
            #
            # setは同じ値を重複して保持しないため、
            # ユニークユーザー数の集計に使用できる
            unique_users.add(user_id)

    # Mark数を保存
    clip["mark_count"] = mark_count

    # ユニークユーザー数を保存
    clip["unique_count"] = len(unique_users)

    # 集計済みクリップ候補を返す
    return clip
