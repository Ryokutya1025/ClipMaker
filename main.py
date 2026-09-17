from config import LOG_PATH, KEYWORD

from log_parser import get_info

# =========================================================
# main
# =========================================================


def main():

    # ログファイルからコメント情報を抽出
    comment_info_list = get_info(LOG_PATH)

    # コメント情報を1件ずつ処理
    for comment_info in comment_info_list:

        # 指定キーワードを含むコメントのみ抽出
        if KEYWORD in comment_info["comment"]:

            # 該当コメントを出力
            print(comment_info["comment"])

            # 詳細確認用
            #
            # print(
            #     f"コメント時間: {comment_info['time']}\n"
            #     f"コメント時間(秒): {comment_info['timestamp']}\n"
            #     f"コメント内容: {comment_info['comment']}\n"
            # )

    # 後続処理で利用できるようコメント一覧を返す
    return comment_info_list


if __name__ == "__main__":
    main()
