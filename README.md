# ClipMaker 0.1.0 β版

配信コメントログから特定のキーワードを検出し、  
切り抜き候補となる時間帯を自動で抽出するツールです。

現在は β版のため、機能・仕様は今後変更される可能性があります。

---

![Version](https://img.shields.io/badge/version-0.1.0--beta-orange)
![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Framework-black?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)
![yt-dlp](https://img.shields.io/badge/yt--dlp-Supported-red?logo=youtube&logoColor=white)
![License](https://img.shields.io/github/license/Ryokutya1025/ClipMaker)
![Last Commit](https://img.shields.io/github/last-commit/Ryokutya1025/ClipMaker)

## 概要

ClipMaker は配信コメントログを解析し、

- 指定キーワードを含むコメントの抽出
- 配信開始からのコメント時刻の算出
- 近い時間に発生したコメントの結合
- Mark数 / Unique数の集計
- SQLiteへの保存
- ヒートマップによる可視化

を行います。

現在のデフォルトキーワードは、

```text
クリップ
```

です。

---

## 現在のクリップ範囲

現時点では、クリップ候補の範囲は固定値です。

```text
Mark発生時刻の30秒前
        ↓
    [ クリップ範囲 ]
        ↑
Mark発生時刻の15秒後
```

つまり、

```text
30秒前 ～ 15秒後
```

の計45秒を基本範囲として扱います。

また、近い時間に発生したMarkは、連続した候補として結合されます。

現在これらの秒数は固定設定ですが、今後変更可能にする予定です。

---

## ヒートマップ

解析結果はヒートマップとして確認できます。

- 緑 : Mark数
- 黄 : Unique数

1つの時間区間について、

```text
左側 : Mark
右側 : Unique
```

として表示します。

これにより、

- 「クリップ」と発言された回数
- 実際に何人のユーザーが反応したか

を比較できます。

---

## 必要環境

- Python 3.x
- yt-dlp
- Flask
- SQLite
- matplotlib
- numpy

必要なパッケージをインストールしてください。

```bash
pip install yt-dlp flask matplotlib numpy
```

---

## 使い方

### 1. ログファイルを用意

配信コメントログをプロジェクト内に配置します。

例:

```text
2026-09-04_test.log
```

---

### 2. config.py を設定

ログファイルや検索キーワードを設定します。

```python
LOG_PATH = "./2026-09-04_test.log"

KEYWORD = "クリップ"
```

現在のクリップ時間設定は、

```python
CLIP_FRONT_TIME = 30
CLIP_REAR_TIME = 15
```

です。

---

### 3. 実行

```bash
python main.py
```

ログを解析し、対象コメントと配信情報を取得します。

解析結果はSQLiteデータベースへ保存されます。

---

## データベース

現在は主に以下のデータを管理しています。

### streams

配信情報を保存します。

```text
id
live_id
title
url
start_timestamp
duration
```

### comments

指定キーワードに一致したコメントを保存します。

```text
id
stream_id
user_id
name
timestamp
comment
```

### mark_unique

結合されたMark候補と集計結果を保存します。

```text
id
stream_id
start_time
end_time
mark_count
unique_count
```

---

## 現在の制限

ClipMaker 0.1.0 β版では、以下の制限があります。

- クリップ前後の秒数は固定
- Mark結合条件も固定
- UI / ヒートマップは開発中
- YouTube配信を中心に開発
- ログ形式によっては正常に解析できない可能性あり
- yt-dlpによる配信情報取得にはCookie設定が必要になる場合あり

---

## 今後追加予定

- クリップ秒数の変更
- Mark結合時間の変更
- キーワード設定
- ヒートマップUI改善
- クリップ候補の一覧表示
- 実際の動画切り抜き処理
- 設定画面
- 配信履歴管理

---

## Version

```text
ClipMaker 0.1.0 β
```

現在開発中です。
