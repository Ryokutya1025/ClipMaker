from database.connection import get_connection

# =========================================================
# streams登録
# =========================================================


def register_stream(conn, stream_info):

    conn.execute(
        """
        INSERT INTO streams (
            live_id,
            title,
            url,
            start_timestamp,
            duration
        )
        VALUES (?, ?, ?, ?, ?)

        ON CONFLICT(live_id)
        DO UPDATE SET
            title = excluded.title,
            url = excluded.url,
            start_timestamp = excluded.start_timestamp,
            duration = excluded.duration
        """,
        (
            stream_info["live_id"],
            stream_info["title"],
            stream_info["url"],
            stream_info["start_timestamp"],
            stream_info["duration"],
        ),
    )

    row = conn.execute(
        """
        SELECT id
        FROM streams
        WHERE live_id = ?
        """,
        (stream_info["live_id"],),
    ).fetchone()

    return row["id"]


# =========================================================
# comments登録
# =========================================================


def register_comments(conn, stream_ids, mark_list):

    rows = []

    for mark in mark_list:

        rows.append(
            (
                stream_ids[mark["live_id"]],
                mark["user_id"],
                mark["name"],
                mark["mark_time"],
                mark["comment"],
            )
        )

    if not rows:
        return

    conn.executemany(
        """
        INSERT INTO comments (
            stream_id,
            user_id,
            name,
            mark_time,
            comment
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


# =========================================================
# mark_unique登録
# =========================================================


def register_mark_unique(conn, stream_ids, clip_list):

    rows = []

    for clip in clip_list:

        rows.append(
            (
                stream_ids[clip["live_id"]],
                clip["start_time"],
                clip["end_time"],
                clip["mark_count"],
                clip["unique_count"],
            )
        )

    if not rows:
        return

    conn.executemany(
        """
        INSERT INTO mark_unique (
            stream_id,
            start_time,
            end_time,
            mark_count,
            unique_count
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )


# =========================================================
# 解析結果保存
# =========================================================


def save_analysis(comment_info_list, mark_list, clip_list):

    if not comment_info_list:
        return

    streams = {}

    # 配信ごとに情報整理
    for comment in comment_info_list:

        live_id = comment["live_id"]

        streams[live_id] = {
            "live_id": live_id,
            "title": comment["title"],
            "url": comment["url"],
            "start_timestamp": comment["start_timestamp"],
            "duration": comment["duration"],
        }

    stream_ids = {}

    with get_connection() as conn:

        # streams登録
        for live_id, stream in streams.items():

            stream_ids[live_id] = register_stream(conn, stream)

        # 古い解析結果削除
        for stream_id in stream_ids.values():

            conn.execute(
                """
                DELETE FROM comments
                WHERE stream_id = ?
                """,
                (stream_id,),
            )

            conn.execute(
                """
                DELETE FROM mark_unique
                WHERE stream_id = ?
                """,
                (stream_id,),
            )

        # comments登録
        register_comments(conn, stream_ids, mark_list)

        # mark_unique登録
        register_mark_unique(conn, stream_ids, clip_list)
