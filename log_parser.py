import json
import re

from yt_dlp import YoutubeDL

from youtube_info import create_ydl_options, get_live_info

from time_utils import convert_comment_time, seconds_to_time

# =========================================================
# 正規表現
# =========================================================

# コメント内のHTML風タグ・スタンプ情報を除去
TAG_PATTERN = re.compile(r"<[^>]*>")

# YouTube動画IDの形式チェック
YOUTUBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


# =========================================================
# コメントログ取得
# =========================================================


def get_info(path):
    """
    わんコメのログファイルを読み込み、
    必要なコメント情報を抽出する
    """

    # 抽出したコメント情報を保存するリスト
    comment_info_list = []

    # 配信情報キャッシュ
    #
    # 同じ配信IDに対して何度もyt-dlpを実行しないようにする
    live_info_cache = {}

    # yt-dlpオプションを生成
    options = create_ydl_options()

    # YoutubeDLインスタンスは1回だけ生成
    with YoutubeDL(options) as ydl:

        # ログファイルを開く
        with open(path, "r", encoding="utf-8") as f:

            # ログを1行ずつ処理
            for line in f:

                # -----------------------------------------
                # ログ基本処理
                # -----------------------------------------

                # 空行を除外
                if not line.strip():
                    continue

                # JSON文字列をPythonの辞書へ変換
                try:
                    log = json.loads(line)

                # JSONとして解析できない行を除外
                except json.JSONDecodeError:
                    continue

                # data部分を取得
                data = log.get("data")

                # dataが存在しないログを除外
                if data is None:
                    continue

                # -----------------------------------------
                # コメント
                # -----------------------------------------

                # コメント本文を取得
                comment = data.get("comment", "")
                # コメント内のスタンプ・HTML風タグを削除
                comment = TAG_PATTERN.sub("", comment).strip()

                # タグ削除後に本文が空になったコメントを除外
                if not comment:
                    continue
                # -----------------------------------------
                # 配信情報
                # -----------------------------------------

                # YouTube配信IDを取得
                live_id = data.get("liveId")

                # 配信IDが存在しないログを除外
                if not live_id:
                    continue

                # YouTube動画IDとして不正な形式を除外
                if not YOUTUBE_ID_PATTERN.match(live_id):
                    continue

                # 初めて処理する配信の場合のみyt-dlpで情報取得
                if live_id not in live_info_cache:

                    # 配信情報を取得してキャッシュへ保存
                    live_info_cache[live_id] = get_live_info(ydl, live_id)

                # キャッシュから配信情報を取得
                live_info = live_info_cache[live_id]

                # 配信情報の取得に失敗していた場合は除外
                if live_info is None:
                    continue

                # -----------------------------------------
                # コメント投稿時刻
                # -----------------------------------------

                # コメント投稿時刻を取得
                timestamp = data.get("timestamp")

                # 投稿時刻がないコメントを除外
                if not timestamp:
                    continue

                # コメント時刻を配信開始からの経過秒数へ変換
                total_seconds = convert_comment_time(timestamp, live_info)

                # 配信開始前・配信終了後のコメントを除外
                if total_seconds is None:
                    continue

                # -----------------------------------------
                # コメント情報
                # -----------------------------------------

                # 必要なコメント情報を辞書へまとめる
                comment_dict = {
                    # 配信URL
                    "url": live_info["url"],
                    # YouTube配信ID
                    "live_id": live_id,
                    # 配信タイトル
                    "title": live_info["title"],
                    # 配信開始時刻
                    "start_timestamp": live_info["start_timestamp"],
                    # 配信時間
                    "duration": live_info["duration"],
                    # コメント投稿者ID
                    "user_id": data.get("userId", ""),
                    # コメント投稿者名
                    "name": data.get("name", ""),
                    # 配信開始からの経過秒数
                    "timestamp": total_seconds,
                    # 表示用のHH:MM:SS
                    "time": seconds_to_time(total_seconds),
                    # コメント本文
                    "comment": comment,
                }

                # コメント情報をリストへ保存
                comment_info_list.append(comment_dict)

    # 抽出した全コメント情報を返す
    return comment_info_list
