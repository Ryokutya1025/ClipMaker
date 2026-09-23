from yt_dlp.utils import DownloadError

from config import BROWSER, BROWSER_PROFILE

# =========================================================
# yt-dlp設定
# =========================================================


def create_ydl_options():
    """
    yt-dlpでYouTubeの配信情報を取得するための設定を生成する
    """

    return {
        # yt-dlpの通常ログを非表示
        "quiet": True,
        # 動画本体はダウンロードしない
        "skip_download": True,
        # プレイリストとして処理しない
        "noplaylist": True,
        # ブラウザからCookieを取得
        "cookiesfrombrowser": (BROWSER, BROWSER_PROFILE),
        # JavaScriptランタイム
        "js_runtimes": {"deno": {}},
        # YouTube JavaScriptチャレンジsolver
        "remote_components": {"ejs:github"},
    }


# =========================================================
# YouTube配信情報取得
# =========================================================


def get_live_info(ydl, live_id):
    """
    YouTube動画IDから配信情報を取得する
    """

    # 配信URLを生成
    url = f"https://www.youtube.com/" f"watch?v={live_id}"

    # yt-dlpで配信情報取得
    try:
        info = ydl.extract_info(url, download=False)

    except DownloadError:
        return None

    # 配信タイトル
    title = info.get("title")

    # 配信開始時刻
    start_timestamp = info.get("release_timestamp")

    # release_timestampが取得できなければtimestamp
    if start_timestamp is None:
        start_timestamp = info.get("timestamp")

    # 配信時間
    duration = info.get("duration")

    # 必要な情報が取得できなかった場合
    if start_timestamp is None or duration is None:
        return None

    return {
        "url": url,
        "title": title,
        "start_timestamp": start_timestamp,
        "duration": int(duration),
    }
