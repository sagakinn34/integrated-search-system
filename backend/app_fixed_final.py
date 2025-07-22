# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template
import sqlite3
import os
from dotenv import load_dotenv
import logging

# 環境変数を読み込み
load_dotenv()

app = Flask(__name__, template_folder='../frontend')

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect('data/search.db')
    conn.row_factory = sqlite3.Row
    # SQLiteのUnicodeサポートを有効化
    conn.execute('PRAGMA encoding="UTF-8"')
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search():
    try:
        query = request.args.get('q', '').strip()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        logger.info(f"検索クエリ: '{query}' (長さ: {len(query)}), ページ: {page}")
        
        if not query:
            return jsonify({
                'success': True,
                'data': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            })
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # デバッグ: 総データ数を確認
        cursor.execute('SELECT COUNT(*) as total_messages FROM messages')
        total_messages = cursor.fetchone()[0]
        logger.info(f"データベース内の総メッセージ数: {total_messages}")
        
        # より柔軟な検索クエリ（大文字小文字を区別しない、部分一致）
        search_pattern = f'%{query}%'
        offset = (page - 1) * per_page
        
        logger.info(f"検索パターン: '{search_pattern}'")
        
        # データ取得（大文字小文字を区別しない検索）
        sql_query = """
            SELECT 
                id, platform, message_id, content, 
                author, channel, timestamp, url
            FROM messages 
            WHERE (content LIKE ? COLLATE NOCASE OR author LIKE ? COLLATE NOCASE)
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        
        params = [search_pattern, search_pattern, per_page, offset]
        logger.info(f"実行するSQL: {sql_query.strip()}")
        logger.info(f"パラメータ: {params}")
        
        cursor.execute(sql_query, params)
        results = cursor.fetchall()
        
        logger.info(f"SQLクエリ結果: {len(results)}件")
        
        # 総数取得
        count_sql = """
            SELECT COUNT(*) as total 
            FROM messages 
            WHERE (content LIKE ? COLLATE NOCASE OR author LIKE ? COLLATE NOCASE)
        """
        count_params = [search_pattern, search_pattern]
        
        cursor.execute(count_sql, count_params)
        total_count = cursor.fetchone()[0]
        total_pages = (total_count + per_page - 1) // per_page
        
        logger.info(f"総検索結果数: {total_count}件")
        
        # 結果を辞書に変換
        data = []
        for row in results:
            item = {
                'id': row['id'],
                'platform': row['platform'],
                'message_id': row['message_id'],
                'content': row['content'],
                'author': row['author'],
                'channel': row['channel'],
                'timestamp': row['timestamp'],
                'url': row['url']
            }
            data.append(item)
            logger.debug(f"結果項目: author='{row['author']}', content_length={len(row['content'] or '')}")
        
        conn.close()
        
        response_data = {
            'success': True,
            'data': data,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        }
        
        logger.info(f"APIレスポンス: {len(data)}件のデータを返却")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"検索エラー: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    logger.info(f"サーバーをポート{port}で起動します")
    app.run(debug=True, host='0.0.0.0', port=port)
