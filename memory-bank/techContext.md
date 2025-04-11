# Technical Context: slacraper

## 使用技術

### 言語とバージョン

- **Python**: 3.12 以上
  - 型ヒントを活用
  - 最新の言語機能を使用
  - f-strings による効率的な文字列フォーマット

### 主要ライブラリ

1. **slack-sdk**

   - バージョン: 3.0.0 以上（実装では 3.35.0 を使用）
   - 用途: Slack API との通信
   - 主な使用クラス: `WebClient`
   - 主な使用メソッド:
     - `conversations_list`: チャンネル一覧の取得
     - `conversations_history`: メッセージ履歴の取得
     - `users_info`: ユーザー情報の取得
     - `team_info`: ワークスペース情報の取得
   - ドキュメント: [slack-sdk Python](https://slack.dev/python-slack-sdk/)

2. **click**
   - バージョン: 8.0.0 以上（実装では 8.1.8 を使用）
   - 用途: コマンドラインインターフェースの構築
   - 主な使用機能:
     - オプション定義（`@click.option`）
     - コマンド定義（`@click.command`）
     - ヘルプテキスト生成
     - エラーハンドリング
   - ドキュメント: [Click Documentation](https://click.palletsprojects.com/)

### パッケージング

1. **setuptools**

   - 用途: パッケージのビルドと配布
   - 設定: `setup.py` と `pyproject.toml`
   - エントリーポイント設定: `console_scripts`

2. **setuptools_scm**
   - バージョン: 6.2 以上
   - 用途: Git タグからバージョン番号を自動生成
   - 設定: `pyproject.toml` の `[tool.setuptools_scm]` セクション
   - バージョン情報の保存: `src/slacraper/_version.py`

### テスト

1. **unittest**

   - 用途: ユニットテスト
   - 場所: `tests/` ディレクトリ
   - 主な使用機能:
     - テストケース定義（`unittest.TestCase`）
     - アサーション（`assertEqual`, `assertIn` など）
     - モック（`unittest.mock.patch`, `MagicMock`）
     - テストフィクスチャ（`setUp`, `tearDown`）

2. **click.testing**
   - 用途: CLI テスト
   - 主な使用クラス: `CliRunner`
   - 機能: コマンドライン呼び出しのシミュレーション

## 開発環境設定

### 仮想環境

- **Python 3.12** 仮想環境を使用
- `.python-version` ファイルで指定
- `.envrc` で自動的に仮想環境をアクティベート
- `uv` パッケージマネージャーを使用して依存関係をインストール

### 環境変数

- **SLACK_BOT_TOKEN**: Slack API 認証用のトークン
  - 開発時は `.envrc` で設定可能
  - 本番環境では適切な方法で設定
  - CLI では引数でも指定可能

### ディレクトリ構造

```
slacraper/
├── .github/workflows/  # GitHub Actions 設定
│   └── publish.yaml    # PyPI 公開ワークフロー
├── memory-bank/        # プロジェクト文書
├── src/                # ソースコード
│   └── slacraper/      # パッケージ
│       ├── __init__.py # パッケージ初期化
│       ├── _version.py # 自動生成されるバージョン情報
│       ├── cli.py      # CLI インターフェース
│       └── core.py     # コア機能
├── tests/              # テストコード
│   ├── __init__.py     # テストパッケージ初期化
│   ├── test_cli.py     # CLI テスト
│   └── test_core.py    # コア機能テスト
├── LICENSE             # ライセンス（MIT）
├── README.md           # 使用方法と説明
├── pyproject.toml      # プロジェクト設定
└── setup.py            # セットアップスクリプト
```

## 技術的制約

1. **Slack API の制限**

   - レート制限: 1 分あたり約 50-100 リクエスト（トークンタイプによる）
   - 履歴取得の制限: チャンネルの履歴は最大 1000 メッセージまで一度に取得可能
   - 検索の制限: 検索 API は別のスコープが必要

2. **認証要件**

   - Bot トークンが必要（`xoxb-` で始まるトークン）
   - 適切なスコープ設定が必要:
     - `channels:history`: チャンネルのメッセージ履歴を読む
     - `channels:read`: チャンネル情報を読む
     - `groups:history`: プライベートチャンネルのメッセージ履歴を読む
     - `groups:read`: プライベートチャンネル情報を読む
     - `users:read`: ユーザー情報を読む
     - `team:read`: チーム情報を読む

3. **パフォーマンス考慮事項**

   - 大量のメッセージを取得する場合はページネーションが必要
   - ユーザー情報のキャッシュを検討
   - API コール数の最適化が必要

4. **エラーハンドリング**
   - ネットワークエラーの処理
   - API レート制限への対応
   - 認証エラーの適切な処理

## 依存関係

### 直接的な依存関係

- **slack-sdk**: Slack API との通信

  - バージョン: 3.0.0 以上
  - 主要コンポーネント: WebClient

- **click**: CLI インターフェース
  - バージョン: 8.0.0 以上
  - 主要機能: オプション定義、コマンド定義

### 開発時の依存関係

- **setuptools**: パッケージング
- **setuptools_scm**: バージョン管理
- **wheel**: パッケージビルド
- **build**: パッケージビルド
- **uv**: 高速パッケージマネージャー（オプション）

### 外部サービス依存関係

- **Slack API**: メッセージデータの取得

  - API バージョン: v2
  - エンドポイント: conversations._, users._, team.\*

- **PyPI**: パッケージの公開
  - 公開方法: GitHub Actions
  - 認証: PyPI API トークン

## デプロイメント

### PyPI パッケージング

- **ビルドプロセス**:

  - setuptools_scm によるバージョン生成
  - wheel および sdist パッケージの作成

- **公開プロセス**:
  - GitHub Actions ワークフローによる自動公開
  - タグベースのリリース（`v*` タグ）

### インストール方法

- **pip**:

  ```bash
  pip install slacraper
  ```

- **開発版**:
  ```bash
  pip install git+https://github.com/youyo/slacraper.git
  ```
