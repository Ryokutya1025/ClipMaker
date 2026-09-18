from database.connection import get_connection

# =========================================================
# 配信登録
# =========================================================


def register_stream(conn, stream_info):
    """
    配信情報をstreamsテーブルへ登録する

    同じlive_idがすでに存在する場合は
    配信情報を更新する
    """

    # 配信情報を登録
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

    # 登録した配信のDB上のIDを取得
    cursor = conn.execute(
        """
        SELECT id
        FROM streams
        WHERE live_id = ?
        """,
        (stream_info["live_id"],),
    )

    row = cursor.fetchone()

    return row["id"]


# =========================================================
# コメント登録
# =========================================================


def register_comments(conn, stream_ids, mark_list):
    """
    キーワードに該当したコメントを
    commentsテーブルへ登録する
    """

    # 登録データを保存するリスト
    rows = []

    # Markを1件ずつ処理
    for mark in mark_list:

        # live_idからDB上のstream_idを取得
        stream_id = stream_ids[mark["live_id"]]

        # 登録データを作成
        rows.append(
            (
                stream_id,
                mark["user_id"],
                mark["name"],
                mark["mark_time"],
                mark["comment"],
            )
        )

    # データがなければ終了
    if not rows:
        return

    # コメントをまとめて登録
    conn.executemany(
        """
        INSERT OR IGNORE INTO comments (
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
# Mark / Unique登録
# =========================================================


def register_mark_unique(conn, stream_ids, clip_list):
    """
    結合済みクリップ候補の
    Mark数・Unique数をmark_uniqueテーブルへ登録する
    """

    # 登録データを保存するリスト
    rows = []

    # クリップ候補を1件ずつ処理
    for clip in clip_list:

        # live_idからDB上のstream_idを取得
        stream_id = stream_ids[clip["live_id"]]

        # 登録データを作成
        rows.append(
            (
                stream_id,
                clip["start_time"],
                clip["end_time"],
                clip["mark_count"],
                clip["unique_count"],
            )
        )

    # データがなければ終了
    if not rows:
        return

    # Mark / Unique情報をまとめて登録
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
# 解析結果登録
# =========================================================


def save_analysis(comment_info_list, mark_list, clip_list):
    """
    解析したデータをデータベースへ保存する

    streams
        配信情報

    comments
        キーワードに該当したコメント

    mark_unique
        結合済みクリップ候補と
        Mark数・Unique数
    """

    # データがなければ終了
    if not comment_info_list:
        return

    # live_id → stream_id
    stream_ids = {}

    # -----------------------------------------
    # 配信情報整理
    # -----------------------------------------

    # 同じ配信情報がコメントごとに含まれているため
    # live_id単位にまとめる
    streams = {}

    for comment_info in comment_info_list:

        live_id = comment_info["live_id"]

        streams[live_id] = {
            "live_id": live_id,
            "title": comment_info["title"],
            "url": comment_info["url"],
            "start_timestamp": comment_info["start_timestamp"],
            "duration": comment_info["duration"],
        }

    # -----------------------------------------
    # DB登録
    # -----------------------------------------

    with get_connection() as conn:

        # -----------------------------------------
        # streams登録
        # -----------------------------------------

        for live_id, stream_info in streams.items():

            # 配信情報を登録
            stream_id = register_stream(conn, stream_info)

            # live_idとDB上のIDを紐付け
            stream_ids[live_id] = stream_id

        # -----------------------------------------
        # 既存解析結果削除
        # -----------------------------------------

        # 同じ配信を再解析した場合に
        # 古い解析結果が残らないよう削除する
        for stream_id in stream_ids.values():

            # コメント解析結果を削除
            conn.execute(
                """
                DELETE FROM comments
                WHERE stream_id = ?
                """,
                (stream_id,),
            )

            # Mark / Unique解析結果を削除
            conn.execute(
                """
                DELETE FROM mark_unique
                WHERE stream_id = ?
                """,
                (stream_id,),
            )

        # -----------------------------------------
        # comments登録
        # -----------------------------------------

        register_comments(conn, stream_ids, mark_list)

        # -----------------------------------------
        # mark_unique登録
        # -----------------------------------------

        register_mark_unique(conn, stream_ids, clip_list)
