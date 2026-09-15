import json
import re

from datetime import datetime
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# =========================================================
# 設定
# =========================================================

# ログファイルパス
LOG_PATH = "./2026-09-04.log"
# キーワード
KEYWORD = "みずち"
# 使用ブラウザ
BROWSER = "chrome"
# 使用プロファイル
BROWSER_PROFILE = "Default"


# =========================================================
# 正規表現
# =========================================================

# 画像排除
TAG_PATTERN = re.compile(r"<[^>]*>")
# 動画IDチェック
YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


# =========================================================
# yt-dlp設定
# =========================================================


def create_ydl_options():

    return {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        # ブラウザCookie
        "cookiesfrombrowser": (BROWSER, BROWSER_PROFILE),
        # JavaScriptランタイム
        "js_runtimes": {"deno": {}},
        # YouTube JSチャレンジsolver
        "remote_components": {"ejs:github"},
    }


# =========================================================
# YouTube配信情報取得
# =========================================================


def get_live_info(ydl, live_id):
    # 配信URL
    url = f"https://www.youtube.com/watch?v={live_id}"

    # yt-dlpで情報取得
    try:
        info = ydl.extract_info(url, download=False)

    except DownloadError:
        return None

    # 配信開始時刻
    start_timestamp = info.get("release_timestamp")

    # release_timestampが無ければtimestampを使う
    if start_timestamp is None:
        start_timestamp = info.get("timestamp")

    # 配信時間
    duration = info.get("duration")

    # 　タイムスタンプがあるかチェック
    if start_timestamp is None or duration is None:
        return None

    # yt-dlpの情報を出力
    return {
        "url": url,
        "start_timestamp": start_timestamp,
        "duration": int(duration),
    }


# =========================================================
# コメント時刻を配信開始からの秒数へ変換
# =========================================================


def convert_comment_time(timestamp, live_info):

    # 時間フォーマットの変更1
    comment_datetime = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    # 時間フォーマットの変換2
    comment_timestamp = comment_datetime.timestamp()

    # 配信開始から何秒後か
    total_seconds = int(comment_timestamp - live_info["start_timestamp"])

    # 配信開始前コメントを排除
    if total_seconds < 0:
        return None

    # 配信終了後コメントを排除
    if total_seconds > live_info["duration"]:
        return None

    #
    return total_seconds


# =========================================================
# 秒数 → HH:MM:SS
# =========================================================


def seconds_to_time(total_seconds):
    # 時間変換
    hours = total_seconds // 3600
    # 分変換
    minutes = (total_seconds % 3600) // 60
    # 秒変換
    seconds = total_seconds % 60
    # 時間を出力
    return f"{hours:02}:" f"{minutes:02}:" f"{seconds:02}"


# =========================================================
# コメントログ取得
# =========================================================


def get_info(path):
    # コメント情報リスト
    comment_info_list = []

    # 配信情報キャッシュ
    live_info_cache = {}

    # yt-dlpオプション設定
    options = create_ydl_options()

    # YoutubeDLは1回だけ生成
    with YoutubeDL(options) as ydl:

        with open(path, "r", encoding="utf-8") as f:

            for line in f:

                # 空行
                if not line.strip():
                    continue

                # JSON変換
                try:
                    log = json.loads(line)

                except json.JSONDecodeError:
                    continue
                # 必要データ取得
                data = log.get("data")
                # 中身のないデータを排除
                if data is None:
                    continue

                # -----------------------------------------
                # コメント
                # -----------------------------------------

                # コメントデータ取得
                comment = data.get("comment", "")

                # スタンプなどを削除
                comment = TAG_PATTERN.sub("", comment).strip()

                # コメント本文が空
                if not comment:
                    continue

                # -----------------------------------------
                # 配信情報
                # -----------------------------------------

                # ライブID取得
                live_id = data.get("liveId")

                # ライブIDがない場合は
                if not live_id:
                    continue

                # YouTubeのID照合
                if not YOUTUBE_ID_PATTERN.match(live_id):
                    continue

                # 初めて見る配信だけyt-dlp実行
                if live_id not in live_info_cache:
                    # キャッシュに保存
                    live_info_cache[live_id] = get_live_info(ydl, live_id)
                # キャッシュから情報取得
                live_info = live_info_cache[live_id]

                # 配信情報取得失敗
                if live_info is None:
                    continue

                # -----------------------------------------
                # 時刻
                # -----------------------------------------

                timestamp = data.get("timestamp")

                if not timestamp:
                    continue

                total_seconds = convert_comment_time(timestamp, live_info)

                # 配信開始前・終了後
                if total_seconds is None:
                    continue

                # -----------------------------------------
                # コメント情報
                # -----------------------------------------

                # コメント情報辞書
                comment_dict = {
                    "url": live_info["url"],
                    "live_id": live_id,
                    "user_id": data.get("userId", ""),
                    "name": data.get("name", ""),
                    # 配信開始からの秒数
                    "timestamp": total_seconds,
                    # 表示用
                    "time": seconds_to_time(total_seconds),
                    "comment": comment,
                }

                # リストに辞書データ保管
                comment_info_list.append(comment_dict)

    return comment_info_list


# =========================================================
# main
# =========================================================


def main():
    # コメント情報抽出
    comment_info_list = get_info(LOG_PATH)
    # コメント情報を1つずつ取得
    for comment_info in comment_info_list:
        # 特定のワードを含むコメントを抽出
        if KEYWORD in comment_info["comment"]:
            print(
                f"コメント時間{comment_info['time']}\nコメント時間(秒){comment_info['timestamp']}\nコメント内容{comment_info['comment']}\n"
            )
    return comment_info_list


if __name__ == "__main__":
    main()
