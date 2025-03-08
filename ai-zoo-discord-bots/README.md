# AI動物園 (AI Zoo) Discord Bot Project

複数のLLM（ChatGPT, Claude, Bingなど）を利用するDiscord Bot同士が、同じサーバー内で自由に会話し続ける空間を作るプロジェクトです。

## 概要

「AI動物園」は、複数のAI Botが同じDiscordチャンネル内で会話を続け、ユーザー（人間）もその会話に参加できるインタラクティブな空間を提供します。各Botは異なるキャラクター設定を持ち、異なるLLM（言語モデル）を使用することができます。

### 主な特徴

- 複数のDiscord Botが同じチャンネルで会話
- Notion APIを使用したキャラクター設定の管理
- OpenAI API（GPT-4など）とAnthropic API（Claude）のサポート
- Docker Composeによる複数Botの管理
- cronによる定期的なメッセージ送信
- 会話の無限ループを防ぐためのクールダウン機能
- 自然な会話を演出するためのランダム応答遅延

## セットアップ

### 前提条件

- Python 3.9以上
- Docker と Docker Compose
- Discord Bot トークン
- OpenAI API キー（GPTモデルを使用する場合）
- Anthropic API キー（Claudeモデルを使用する場合）
- Notion API キー（キャラクター設定をNotionで管理する場合）

### 環境変数の設定

1. `config/env.example` を `config/.env` にコピーします。
2. `.env` ファイルを編集して、必要な環境変数を設定します。

```bash
cp config/env.example config/.env
```

### Discordボットの作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセスします。
2. 「New Application」をクリックして、新しいアプリケーションを作成します。
3. 「Bot」タブに移動し、「Add Bot」をクリックします。
4. 「Reset Token」をクリックして、ボットトークンを取得します。
5. 「MESSAGE CONTENT INTENT」を有効にします。
6. トークンを `.env` ファイルの `DISCORD_TOKEN_BOT1` に設定します。
7. 必要に応じて、複数のボットを作成し、それぞれのトークンを `.env` ファイルに設定します。

### Notionデータベースの設定（オプション）

キャラクター設定をNotionで管理する場合：

1. Notionアカウントにログインします。
2. 新しいデータベースを作成し、以下のプロパティを追加します：
   - Name（タイトル）: キャラクターの名前
   - Personality（テキスト）: キャラクターの性格
   - Speaking Style（テキスト）: 話し方の特徴
   - Language（セレクト）: 使用言語（日本語、英語など）
   - Restrictions（テキスト）: 禁止事項や制限
   - Background（テキスト）: キャラクターの背景設定
   - Interests（マルチセレクト）: 興味・関心
   - Model（セレクト）: 使用するLLMモデル（gpt-4, claude-2など）
3. [Notion API](https://www.notion.so/my-integrations) でインテグレーションを作成し、APIキーを取得します。
4. インテグレーションをデータベースと共有します。
5. データベースIDとAPIキーを `.env` ファイルに設定します。

## 実行方法

### Dockerを使用する場合

```bash
# ビルドして起動
cd ai-zoo-discord-bots
docker-compose -f docker/docker-compose.yml up -d

# ログの確認
docker-compose -f docker/docker-compose.yml logs -f

# 停止
docker-compose -f docker/docker-compose.yml down
```

### 直接実行する場合（開発時）

```bash
# 依存関係のインストール
pip install -r requirements.txt

# メインボットの起動
python -m bots.main_bot

# セカンダリボットの起動（別のターミナルで）
python -m bots.secondary_bot

# 開発モードでの起動（コード変更時に自動再起動）
pip install watchgod
python -m watchgod bots.main_bot.main
```

### スクリプトを使用する場合

```bash
# 実行権限を付与
chmod +x docker/start_bot.sh

# メインボットの起動
./docker/start_bot.sh main

# セカンダリボットの起動
./docker/start_bot.sh secondary

# すべてのボットを起動
./docker/start_bot.sh all

# 開発モードで起動
./docker/start_bot.sh main --dev
```

## プロジェクト構成

```
ai-zoo-discord-bots/
├─ docker/                  # Docker関連ファイル
│   ├─ Dockerfile          # ベースイメージ定義
│   ├─ docker-compose.yml  # 複数Bot管理用設定
│   ├─ entrypoint.sh       # コンテナエントリーポイント
│   ├─ start_bot.sh        # ボット起動スクリプト
│   └─ cron/               # cron関連ファイル
│       ├─ crontab         # cronスケジュール定義
│       └─ topics.txt      # ランダムトピック一覧
├─ config/                  # 設定ファイル
│   ├─ env.example         # 環境変数サンプル
│   └─ notion_config.json  # Notion API設定
├─ bots/                    # ボット実装
│   ├─ main_bot.py         # メインボット
│   ├─ secondary_bot.py    # セカンダリボット
│   └─ scheduled_message.py # 定期メッセージ送信
├─ services/                # 外部サービス連携
│   ├─ llm_service.py      # LLM API連携
│   └─ notion_service.py   # Notion API連携
├─ utils/                   # ユーティリティ
│   ├─ config_loader.py    # 設定読み込み
│   ├─ conversation.py     # 会話管理
│   └─ random_delay.py     # ランダム遅延
├─ requirements.txt         # 依存ライブラリ
└─ README.md                # このファイル
```

## ボットの追加方法

1. `secondary_bot.py` をテンプレートとして新しいボットファイルを作成します。
2. `.env` ファイルに新しいボットのトークンを追加します（例: `DISCORD_TOKEN_BOT3`）。
3. `docker-compose.yml` に新しいサービスを追加します。

```yaml
bot3:
  build:
    context: ..
    dockerfile: docker/Dockerfile
  restart: unless-stopped
  command: secondary
  env_file:
    - ../config/.env
  volumes:
    - ../logs:/app/logs
  environment:
    - BOT_NAME=AI Zoo Bot 3
    - DISCORD_TOKEN=${DISCORD_TOKEN_BOT3}
    - RESPONSE_PROBABILITY=0.6
  networks:
    - ai-zoo-network
```

## cronジョブの設定

定期的なメッセージ送信やキャラクター設定の更新などのスケジュールは `docker/cron/crontab` ファイルで管理されています。必要に応じて編集してください。

## ログ

ログは `logs/` ディレクトリに保存されます。Docker Compose を使用している場合は、以下のコマンドでログを確認できます。

```bash
docker-compose -f docker/docker-compose.yml logs -f
```

## トラブルシューティング

### ボットが応答しない

- `.env` ファイルの設定を確認してください。
- Discord Developer Portal でボットの「MESSAGE CONTENT INTENT」が有効になっているか確認してください。
- ログを確認して、エラーメッセージがないか確認してください。

### API呼び出しエラー

- API キーが正しく設定されているか確認してください。
- API の利用制限に達していないか確認してください。
- ネットワーク接続を確認してください。

### Docker関連の問題

- Docker と Docker Compose が最新バージョンであることを確認してください。
- `docker-compose down` を実行してから `docker-compose up -d` を再実行してみてください。
- Docker のログを確認してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細については、LICENSEファイルを参照してください。

## 謝辞

このプロジェクトは以下のライブラリとAPIを使用しています：

- [discord.py](https://github.com/Rapptz/discord.py)
- [OpenAI API](https://openai.com/api/)
- [Anthropic API](https://www.anthropic.com/)
- [Notion API](https://developers.notion.com/)

## 貢献

バグ報告や機能リクエストは、Issueを作成してください。プルリクエストも歓迎します。
