# 🔧 設定ファイル - ここに自分の情報を入力してください
# 
# ⚠️ 重要：このファイルは他人に見せないでください！
# APIキーなどの重要な情報が含まれています。

import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# 🌐 基本設定
APP_NAME = "統合検索システム"
DEBUG_MODE = True  # 開発中はTrue、本番運用時はFalseに変更
HOST = "127.0.0.1"  # ローカル開発用
PORT = 5000

# 📁 データベース設定
DATABASE_PATH = "database/integrated_search.db"

# 🔍 MeiliSearch設定
MEILISEARCH_HOST = "http://127.0.0.1:7700"
MEILISEARCH_MASTER_KEY = None  # 開発用は空でOK

# 🔑 API設定（.envファイルから読み込み）
# Chatwork API設定
CHATWORK_API_TOKEN = os.getenv("CHATWORK_API_TOKEN", "")

# Notion API設定
NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# Discord Bot設定
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")

# ⏰ 同期設定
SYNC_INTERVAL_MINUTES = 30  # 30分ごとにデータを取得
MAX_MESSAGES_PER_SYNC = 100  # 1回の同期で取得する最大メッセージ数

# 📋 ログ設定
LOG_LEVEL = "INFO"
LOG_FILE = "logs/system.log"

print("⚙️ 設定ファイルが読み込まれました！")
