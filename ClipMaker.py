import json
from yt_dlp import YoutubeDL
from datetime import datetime, timezone, timedelta
import math

path = "./2026-09-04.log"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
    line = json.loads(lines[2])
    log = line
    live_id = line["data"]["liveId"]
    # user_id = line["data"]["userId"]
    # comment = line["data"]["comment"]
    # timestamp = line["data"]["timestamp"]
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
        start_time = datetime.fromtimestamp(info["release_timestamp"], tz=timezone.utc)
        print(start_time)

    duration = timedelta(seconds=int(info["duration"]))
    print(duration)
