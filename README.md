# slacraper

Slack のメッセージを取得するためのツールです。ライブラリとしての利用を基本としますが、CLI としても利用できます。

## インストール

```bash
# pipを使用する場合
pip install slacraper

# uvを使用する場合
uv pip install slacraper
```

または、開発版を使用する場合：

```bash
# pipを使用する場合
pip install git+https://github.com/youyo/slacraper.git

# uvを使用する場合
uv pip install git+https://github.com/youyo/slacraper.git
```

### uvx での実行

uvx を使用して直接実行することもできます：

```bash
# モジュールとして実行
uvx slacraper --channel general

# ソースコードから直接実行
uvx src/slacraper/cli.py --channel general
```

## 使い方

### ライブラリとして

```python
from slacraper import Slacraper

# 環境変数 SLACK_BOT_TOKEN が設定されている場合
scraper = Slacraper(channel="general")
messages = scraper.get_messages()
print(messages)
# トークンを直接指定する場合
scraper = Slacraper(channel="general", token="xoxb-your-token")

# 時間範囲を指定する場合（数値で指定）
messages = scraper.get_messages(time_range=2)  # 過去2時間のメッセージを取得

# 時間範囲を自然言語で指定する場合
messages = scraper.get_messages(time_range="1 day")  # 過去1日のメッセージを取得
messages = scraper.get_messages(time_range="1 week")  # 過去1週間のメッセージを取得
messages = scraper.get_messages(time_range="2 weeks")  # 過去2週間のメッセージを取得
print(messages)

# フィルタリングオプションを使用する場合
messages = scraper.get_messages(
    user="user_name",
    text_contains="検索キーワード",
    reaction="thumbsup",
    include_url=True
)
print(messages)
```

### CLI として

```bash
# 環境変数 SLACK_BOT_TOKEN が設定されている場合
slacraper --channel general

# トークンを直接指定する場合
slacraper --channel general --token xoxb-your-token
# 時間範囲を自然言語で指定する場合
slacraper --channel general --time-range "1 day"  # 過去1日のメッセージを取得
slacraper --channel general --time-range "1 week"  # 過去1週間のメッセージを取得
slacraper --channel general --time-range "2 weeks"  # 過去2週間のメッセージを取得

# フィルタリングオプションを使用する場合
slacraper --channel general --user user_name --text-contains "検索キーワード" --reaction thumbsup --include-url
```

## 必要な Slack Bot のパーミッション

このツールを使用するには、Slack Bot に以下のパーミッション（スコープ）が必要です：

- `channels:read` - パブリックチャンネルの一覧取得
- `groups:read` - プライベートチャンネルの一覧取得
- `users:read` - ユーザー情報の取得
- `channels:history` - パブリックチャンネルのメッセージ履歴取得
- `groups:history` - プライベートチャンネルのメッセージ履歴取得
- `team:read` - ワークスペース情報の取得（メッセージ URL の生成に使用）

これらのパーミッションは、Slack API の[アプリ管理画面](https://api.slack.com/apps)で設定できます。

## オプション

- `--channel`: (必須) メッセージを取得するチャンネル名
- `--token`: Slack Bot Token（環境変数 `SLACK_BOT_TOKEN` が設定されていない場合は必須）
- `--time-range`: 時間範囲を自然言語で指定（例: "1 hour", "2 days", "1 week", "1 month"）（デフォルト: "1 hour"）
- `--user`: 特定のユーザーのメッセージのみを取得
- `--text-contains`: 特定のテキストを含むメッセージのみを取得
- `--reaction`: 特定のリアクション（スタンプ）が付与されたメッセージのみを取得
- `--include-url`: メッセージの URL も出力に含める

## 出力形式

出力は構造化 JSON フォーマットです：

```json
[
  {
    "channel": "general",
    "user": "U12345678",
    "user_name": "username",
    "text": "メッセージ内容",
    "timestamp": "2023-01-01T12:34:56Z",
    "reactions": [
      {
        "name": "thumbsup",
        "count": 3,
        "users": ["U12345678", "U87654321", "U11223344"]
      }
    ],
    "url": "https://workspace.slack.com/archives/C12345678/p1234567890123456"
  }
]
```

## ライセンス

MIT
