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

    取得する情報:
        url
        title
        start_timestamp
        duration
    """

    # 配信URLを生成
    url = f"https://www.youtube.com/watch?v={live_id}"

    # yt-dlpで動画・配信情報を取得
    try:
        info = ydl.extract_info(url, download=False)

    except DownloadError:
        return None

    # 配信タイトルを取得
    title = info.get("title")

    # 配信開始時刻をUnix timestampで取得
    start_timestamp = info.get("release_timestamp")

    # release_timestampが取得できない場合はtimestampを使用
    if start_timestamp is None:
        start_timestamp = info.get("timestamp")

    # 配信時間を秒数で取得
    duration = info.get("duration")

    # 配信開始時刻または配信時間を取得できなかった場合
    if start_timestamp is None or duration is None:
        return None

    # 必要な配信情報を辞書で返す
    return {
        "url": url,
        "title": title,
        "start_timestamp": start_timestamp,
        "duration": int(duration),
    }
