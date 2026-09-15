import json, math, re
from yt_dlp import YoutubeDL
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import math


def get_info(path):
    # コメント情報リスト
    comment_info_list = []

    # ログから情報取得
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # ログを1行ずつ処理
    for line in lines:
        # jsonデータに変換
        line = json.loads(line)

        # 【コメント情報】
        # コメント情報の取得
        comment = line["data"]["comment"]
        # コメント情報からスタンプ情報を排除
        comment = re.sub(r"<[^>]*>", "", comment)
        # 文字のないコメントを排除 ←早い段階から排除⭐
        if comment == "":
            continue

        # 【配信情報】
        # 配信ID
        live_id = line["data"]["liveId"]
        # 配信URL
        url = f"https://www.youtube.com/watch?v={live_id}"

        # 【ユーザー情報】
        # ユーザーID
        user_id = line["data"]["userId"]
        # ユーザー名
        name = line["data"]["name"]

        # 【時間情報】
        # タイムスタンプ情報 日時
        timestamp = str(line["data"]["timestamp"])
        # フォーマットの変更
        comment_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        # 日本時間に変更
        comment_time = comment_time.astimezone(ZoneInfo("Asia/Tokyo"))
        # 配信開始からの時間に変換
        comment_time = get_yt_dlp_info(url, comment_time)

        # 各コメントの情報　辞書化
        comment_dict = {
            "url": f"{url}",  # url
            "live_id": f"{live_id}",  # ライブID
            "user_id": f"{user_id}",  # ユーザーID
            "name": f"{name}",  # ユーザー名
            "timestamp": f"{comment_time}",  # タイムスタンプ
            "comment": f"{comment}",  # コメント内容
        }
        print(comment_dict)
        # リストに格納
        comment_info_list.append(comment_dict)
    # リストを出力
    return comment_info_list


def get_yt_dlp_info(url, comment_time_jst):
    # yt-dlpオプション
    options = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        # ChromeのCookie取得
        "cookiesfrombrowser": ("chrome", "Default"),
        # JavaScriptランタイム
        "js_runtimes": {"deno": {}},
        # JSチャレンジsolverを必要に応じて取得
        "remote_components": {"ejs:github"},
    }

    # yt-dlp情報取得
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    # 配信開始時間の取得
    with open("info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
        # 日本時間に変換
        start_time = datetime.fromtimestamp(
            info["release_timestamp"], tz=timezone(timedelta(hours=9))
        )

    live_duration = timedelta(seconds=int(info["duration"]))  # 配信時間
    live_comment_time = comment_time_jst - start_time  # コメント時間

    # 配信開始前と配信後のコメントを排除
    if live_comment_time >= timedelta(0) and live_comment_time <= live_duration:
        # 秒数に変換
        total_seconds = int(live_comment_time.total_seconds())
        hours = total_seconds // 3600  # 時間
        minutes = (total_seconds % 3600) // 60  # 分
        seconds = total_seconds % 60  # 秒
    # print(
    #     f"コメント日 {comment_time_jst.date()}\nコメント時間 {hours:02}:{minutes:02}:{seconds:02}\n投稿者 {name}\nコメント内容『{comment}』\n"
    # )

    # コメント時間(秒)を出力
    return total_seconds, hours, minutes, seconds


def main():
    # ログのパス
    path = "./2026-09-04.log"
    get_info(path)


if __name__ == "__main__":
    main()
