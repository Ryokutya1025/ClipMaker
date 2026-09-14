import json, math, re
from yt_dlp import YoutubeDL
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import math

path = "./2026-09-04.log"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
    line = json.loads(lines[2])
    for line in lines:
        line = json.loads(line)
        live_id = line["data"]["liveId"]
        user_id = line["data"]["userId"]
        name = line["data"]["name"]
        comment = line["data"]["comment"]
        comment = re.sub(r"<[^>]*>", "", comment)
        timestamp = str(line["data"]["timestamp"])
        comment_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        comment_time_jst = comment_time.astimezone(ZoneInfo("Asia/Tokyo"))

        if comment == "":
            continue

        # print(json.dumps(log, ensure_ascii=False, indent=2))
        # print(f"liveID:{live_id} userID:{user_id}, comment:{comment} time:{timestamp} ")

        url = f"https://www.youtube.com/watch?v={live_id}"
        options = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
        }

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        with open("info.json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
            start_time = datetime.fromtimestamp(
                info["release_timestamp"], tz=timezone(timedelta(hours=9))
            )
            # print(f"配信開始：{start_time}")

        duration = timedelta(seconds=int(info["duration"]))
        live_comment_time = comment_time_jst - start_time
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
