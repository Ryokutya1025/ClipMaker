import sqlite3

from config import DB_PATH

# =========================================================
# データベース接続
# =========================================================


def get_connection():
    """
    SQLiteデータベースへ接続する
    """

    # データベースへ接続
    conn = sqlite3.connect(DB_PATH)

    # SELECT結果をカラム名で取得できるようにする
    conn.row_factory = sqlite3.Row

    # 外部キー制約を有効化
    conn.execute("PRAGMA foreign_keys = ON")

    return conn
