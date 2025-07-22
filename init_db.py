#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ データベース初期化スクリプト

このスクリプトは、統合検索システム用のSQLiteデータベースを作成します。
実行すると、必要なテーブルがすべて作成されます。
"""

import sqlite3
import os
from datetime import datetime

def create_database():
    """データベースとテーブルを作成する関数"""

    # データベースフォルダが存在しない場合は作成
    if not os.path.exists('database'):
        os.makedirs('database')

    # データベースに接続（存在しない場合は自動作成）
    conn = sqlite3.connect('database/integrated_search.db')
    cursor = conn.cursor()

    print("🗄️ データベースを初期化しています...")

    # 1. メッセージテーブル（全プラットフォーム共通）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,           -- 'chatwork', 'notion', 'discord'
        platform_id TEXT NOT NULL,        -- 各プラットフォームでのメッセージID
        title TEXT,                       -- メッセージのタイトル（あれば）
        content TEXT NOT NULL,            -- メッセージの本文
        author_name TEXT,                 -- 発信者の名前
        author_id TEXT,                   -- 発信者のID
        channel_name TEXT,                -- チャンネル/ルーム名
        channel_id TEXT,                  -- チャンネル/ルームID
        created_at DATETIME,              -- メッセージ作成日時
        updated_at DATETIME,              -- メッセージ更新日時
        synchronized_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 同期日時
        is_deleted INTEGER DEFAULT 0,    -- 削除フラグ
        metadata TEXT,                    -- JSON形式の追加情報
        UNIQUE(platform, platform_id)    -- 重複防止
    )
    ''')

    # 2. 添付ファイルテーブル
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,               -- messagesテーブルのID
        file_name TEXT,                   -- ファイル名
        file_url TEXT,                    -- ファイルURL
        file_type TEXT,                   -- ファイルタイプ
        file_size INTEGER,                -- ファイルサイズ
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (message_id) REFERENCES messages (id)
    )
    ''')

    # 3. 同期ログテーブル
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,          -- 同期したプラットフォーム
        status TEXT NOT NULL,             -- 'success', 'error', 'partial'
        messages_count INTEGER DEFAULT 0,-- 同期したメッセージ数
        error_message TEXT,               -- エラーメッセージ（あれば）
        started_at DATETIME,              -- 同期開始時間
        completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 同期完了時間
        duration_seconds REAL             -- 同期時間（秒）
    )
    ''')

    # 4. 検索統計テーブル
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS search_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_query TEXT NOT NULL,       -- 検索クエリ
        results_count INTEGER,            -- 検索結果数
        search_time_ms REAL,              -- 検索時間（ミリ秒）
        searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # インデックスを作成（検索高速化のため）
    print("📊 インデックスを作成しています...")

    # メッセージ検索用インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_platform ON messages(platform)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_author ON messages(author_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content)')

    # 同期ログ用インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_logs_platform ON sync_logs(platform)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_logs_completed_at ON sync_logs(completed_at)')

    # 変更を保存
    conn.commit()

    # テスト用サンプルデータを挿入
    print("🧪 サンプルデータを挿入しています...")

    sample_messages = [
        ('test', 'sample_1', 'テストメッセージ', 'これは動作確認用のテストメッセージです。', 
         'テストユーザー', 'test_user_1', 'テストチャンネル', 'test_channel_1', 
         datetime.now(), datetime.now(), '{}'),
        ('test', 'sample_2', 'サンプル投稿', '統合検索システムのテストです。正常に動作していますか？', 
         'サンプルユーザー', 'test_user_2', 'サンプルルーム', 'test_channel_2', 
         datetime.now(), datetime.now(), '{}')
    ]

    cursor.executemany('''
    INSERT OR IGNORE INTO messages 
    (platform, platform_id, title, content, author_name, author_id, channel_name, channel_id, created_at, updated_at, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_messages)

    conn.commit()

    # 作成されたテーブルの確認
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    print("✅ データベースの初期化が完了しました！")
    print(f"📋 作成されたテーブル数: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")

    # データベース接続を閉じる
    conn.close()

    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🗄️ 統合検索システム - データベース初期化")
    print("=" * 50)

    try:
        create_database()
        print("🎉 初期化が正常に完了しました！")
        print("次は「python backend/app.py」を実行してWebサーバーを起動してください。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        print("問題が解決しない場合は、database/フォルダを削除してから再実行してください。")
