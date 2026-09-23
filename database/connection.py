import sqlite3

from config import DB_PATH

# =========================================================
# データベース接続
# =========================================================


def get_connection():

    conn = sqlite3.connect(DB_PATH)

    # カラム名で取得できるようにする
    conn.row_factory = sqlite3.Row

    # 外部キー制約を有効化
    conn.execute("PRAGMA foreign_keys = ON")

    return conn
