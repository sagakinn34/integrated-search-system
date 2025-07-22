#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 統合検索システム - メインアプリケーション

このファイルは、統合検索システムのメインとなるWebアプリケーションです。
FlaskというPythonのWebフレームワークを使用しています。
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

# 設定ファイルを読み込み
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import *

# Flaskアプリケーションを作成
app = Flask(__name__)
CORS(app)  # CORSを有効にする（フロントエンドからのアクセスを許可）

def get_db_connection():
    """データベース接続を取得する関数"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
    return conn

@app.route('/')
def index():
    """メインページを表示"""
    return send_from_directory('../frontend', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """静的ファイル（CSS、JSなど）を提供"""
    return send_from_directory('../frontend/static', filename)

@app.route('/api/search')
def search_messages():
    """
    🔍 メッセージ検索API

    パラメータ:
    - q: 検索クエリ
    - platform: プラットフォーム絞り込み（chatwork, notion, discord）
    - limit: 取得件数制限（デフォルト: 50）
    - offset: 取得開始位置（デフォルト: 0）
    """

    # 検索パラメータを取得
    query = request.args.get('q', '').strip()
    platform = request.args.get('platform', '').strip()
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))

    if not query:
        return jsonify({
            'success': False,
            'message': '検索クエリが空です',
            'results': [],
            'total': 0
        })

    try:
        start_time = datetime.now()

        # データベース接続
        conn = get_db_connection()

        # 検索SQL構築
        sql = '''
        SELECT 
            id, platform, message_id, content, 
            author, room_name, created_at, search_text
        FROM messages 
        WHERE (content LIKE ? OR author LIKE ? OR search_text LIKE ?)
        '''

        params = [f'%{query}%', f'%{query}%', f'%{query}%']

        # プラットフォーム絞り込み
        if platform:
            sql += ' AND platform = ?'
            params.append(platform)

        # 並び順（新しい順）
        sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        # 検索実行
        cursor = conn.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]

        # 総件数取得
        count_sql = '''
        SELECT COUNT(*) as total 
        FROM messages 
        WHERE (content LIKE ? OR author LIKE ? OR search_text LIKE ?)
        '''
        count_params = [f'%{query}%', f'%{query}%', f'%{query}%']

        if platform:
            count_sql += ' AND platform = ?'
            count_params.append(platform)

        total_count = conn.execute(count_sql, count_params).fetchone()['total']

        conn.close()

        # 検索時間計算
        search_time = (datetime.now() - start_time).total_seconds() * 1000

        # 検索統計を記録
        log_search_stats(query, total_count, search_time)

        return jsonify({
            'success': True,
            'query': query,
            'platform': platform,
            'results': results,
            'total': total_count,
            'count': len(results),
            'search_time_ms': round(search_time, 2)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'検索エラー: {str(e)}',
            'results': [],
            'total': 0
        })

@app.route('/api/stats')
def get_stats():
    """
    📊 システム統計情報API

    メッセージ数、プラットフォーム別統計などを返す
    """

    try:
        conn = get_db_connection()

        # 総メッセージ数
        total_messages = conn.execute(
            'SELECT COUNT(*) as count FROM messages WHERE is_deleted = 0'
        ).fetchone()['count']

        # プラットフォーム別統計
        platform_stats = conn.execute('''
        SELECT platform, COUNT(*) as count 
        FROM messages 
        WHERE is_deleted = 0 
        GROUP BY platform
        ''').fetchall()

        # 最新の同期時刻
        last_sync = conn.execute('''
        SELECT MAX(synchronized_at) as last_sync 
        FROM messages
        ''').fetchone()['last_sync']

        # よく検索されるキーワード（上位10件）
        popular_searches = conn.execute('''
        SELECT search_query, COUNT(*) as count 
        FROM search_stats 
        GROUP BY search_query 
        ORDER BY count DESC 
        LIMIT 10
        ''').fetchall()

        conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'total_messages': total_messages,
                'platform_stats': [dict(row) for row in platform_stats],
                'last_sync': last_sync,
                'popular_searches': [dict(row) for row in popular_searches]
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'統計取得エラー: {str(e)}'
        })

@app.route('/api/sync/status')
def get_sync_status():
    """
    🔄 同期状況確認API

    最新の同期ログ情報を返す
    """

    try:
        conn = get_db_connection()

        # 最新の同期ログ（プラットフォーム別）
        sync_status = conn.execute('''
        SELECT platform, status, messages_count, completed_at, error_message
        FROM sync_logs 
        WHERE id IN (
            SELECT MAX(id) 
            FROM sync_logs 
            GROUP BY platform
        )
        ORDER BY completed_at DESC
        ''').fetchall()

        conn.close()

        return jsonify({
            'success': True,
            'sync_status': [dict(row) for row in sync_status]
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'同期状況取得エラー: {str(e)}'
        })

def log_search_stats(query, results_count, search_time_ms):
    """検索統計をログに記録"""
    try:
        conn = get_db_connection()
        conn.execute('''
        INSERT INTO search_stats (search_query, results_count, search_time_ms)
        VALUES (?, ?, ?)
        ''', (query, results_count, search_time_ms))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"検索統計記録エラー: {e}")

@app.route('/api/test')
def test_api():
    """API動作テスト用エンドポイント"""
    return jsonify({
        'success': True,
        'message': 'API is working!',
        'timestamp': datetime.now().isoformat(),
        'app_name': APP_NAME
    })

if __name__ == '__main__':
    print("=" * 60)
    print(f"🌐 {APP_NAME} - Webサーバー起動中...")
    print("=" * 60)
    print(f"📍 URL: http://{HOST}:{PORT}")
    print("🔍 ブラウザで上記URLにアクセスしてください")
    print("🛑 停止するには Ctrl+C を押してください")
    print("=" * 60)

    # データベースファイルの存在確認
    if not os.path.exists(DATABASE_PATH):
        print("⚠️  データベースが見つかりません！")
        print("先に「python database/init_db.py」を実行してください。")
        sys.exit(1)

    # Webサーバーを起動
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG_MODE,
        threaded=True
    )
