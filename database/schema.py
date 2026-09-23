from database.connection import get_connection

# =========================================================
# テーブル作成
# =========================================================


def create_tables():

    with get_connection() as conn:

        # -----------------------------------------
        # streams
        # -----------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS streams (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                live_id TEXT NOT NULL UNIQUE,

                title TEXT,

                url TEXT NOT NULL,

                start_timestamp INTEGER NOT NULL,

                duration INTEGER NOT NULL
            )
            """)

        # -----------------------------------------
        # comments
        # -----------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                stream_id INTEGER NOT NULL,

                user_id TEXT,

                name TEXT,

                mark_time INTEGER NOT NULL,

                comment TEXT NOT NULL,

                FOREIGN KEY (stream_id)
                    REFERENCES streams(id)
                    ON DELETE CASCADE
            )
            """)

        # -----------------------------------------
        # mark_unique
        # -----------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS mark_unique (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                stream_id INTEGER NOT NULL,

                start_time INTEGER NOT NULL,

                end_time INTEGER NOT NULL,

                mark_count INTEGER NOT NULL,

                unique_count INTEGER NOT NULL,

                FOREIGN KEY (stream_id)
                    REFERENCES streams(id)
                    ON DELETE CASCADE
            )
            """)

        # -----------------------------------------
        # Index
        # -----------------------------------------

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_comments_stream
            ON comments(stream_id)
            """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_mark_unique_stream
            ON mark_unique(stream_id)
            """)
