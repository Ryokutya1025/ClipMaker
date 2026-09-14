import json, math, re
from yt_dlp import YoutubeDL
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import math



def get_info(path):
    comment_info_list = []

    # 情報取得
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        # jsonデータに変換
        line = json.loads(line)
        # コメント情報の取得
        comment = line["data"]["comment"]
        # コメント情報からスタンプ情報を排除
        comment = re.sub(r"<[^>]*>", "", comment)
        # 文字のないコメントを排除 ←早い段階から排除⭐
        if comment == "":
            continue
        
        live_id = line["data"]["liveId"] # 配信ID
        user_id = line["data"]["userId"] # ユーザーID
        name = line["data"]["name"] # ユーザー名
        timestamp = str(line["data"]["timestamp"]) # タイムスタンプ情報
        comment_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) # フォーマットの変更
        comment_time_jst = comment_time.astimezone(ZoneInfo("Asia/Tokyo")) # 日本時間に変更
        url = f"https://www.youtube.com/watch?v={live_id}" # 配信URL

        comment_dict = {
            "url": f"{url}",
            
        }
    return comment_info_list

def get_yt_dlp_info(url, comment_time_jst):        
    # yt-dlpオプション
    options = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
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

    duration = timedelta(seconds=int(info["duration"])) # 配信時間
    live_comment_time = comment_time_jst - start_time # コメント時間
    if live_comment_time >= timedelta(0):
        total_seconds = int(live_comment_time.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
    else:
        continue
    print(
        f"コメント日 {comment_time_jst.date()}\nコメント時間 {hours:02}:{minutes:02}:{seconds:02}\n投稿者 {name}\nコメント内容『{comment}』\n"
    )

def main():
    # ログのパス
    path = "./2026-09-04.log"

    url, live_id, comment_time_jst, user_id, name, comment = get_info(path)
