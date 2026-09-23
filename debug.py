from time_utils import seconds_to_time

# =========================================================
# Mark確認
# =========================================================


def print_marks(mark_list):
    """
    検出されたMarkを表示する
    """

    print("\n===== Mark Test =====")

    for index, mark in enumerate(mark_list, start=1):
        print(
            f"[{index}] "
            f"{seconds_to_time(mark['mark_time'])} | "
            f"{mark['name']} | "
            f"{mark['comment']}"
        )

    print(f"\nMark Count: {len(mark_list)}")


# =========================================================
# Mark / Unique確認
# =========================================================


def print_clips(clip_list):
    """
    結合後のMark数・Unique数を表示する
    """

    print("\n===== Clip Test =====")

    for index, clip in enumerate(clip_list, start=1):
        start = seconds_to_time(clip["start_time"])

        end = seconds_to_time(clip["end_time"])

        print(
            f"[{index}] "
            f"{start} ～ {end} | "
            f"Mark: {clip['mark_count']} | "
            f"Unique: {clip['unique_count']}"
        )

    print(f"\nClip Candidates: {len(clip_list)}")
