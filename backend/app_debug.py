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
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect('data/search.db')
    conn.row_factory = sqlite3.Row
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
        
        logger.info(f"=== 検索開始 ===")
        logger.info(f"検索クエリ: '{query}'")
        logger.info(f"クエリの文字数: {len(query)}")
        logger.info(f"クエリのバイト表現: {query.encode('utf-8')}")
        logger.info(f"ページ: {page}")
        
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
        
        # テスト1: 総データ数確認
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        logger.info(f"データベース内の総メッセージ数: {total_messages}")
        
        # テスト2: 井上さんのデータ確認（直接）
        cursor.execute("SELECT COUNT(*) FROM messages WHERE author LIKE '%井上%'")
        inoue_count = cursor.fetchone()[0]
        logger.info(f"井上さんのデータ数（直接検索）: {inoue_count}")
        
        # テスト3: 著者名のサンプル表示
        cursor.execute("SELECT DISTINCT author FROM messages LIMIT 5")
        authors = [row[0] for row in cursor.fetchall()]
        logger.info(f"著者名のサンプル: {authors}")
        
        # テスト4: パラメータ化クエリのテスト
        search_pattern = f'%{query}%'
        logger.info(f"作成した検索パターン: '{search_pattern}'")
        
        # まず著者名だけで検索してみる
        cursor.execute("SELECT COUNT(*) FROM messages WHERE author LIKE ?", [search_pattern])
        author_count = cursor.fetchone()[0]
        logger.info(f"著者名での検索結果数: {author_count}")
        
        # 次にコンテンツだけで検索
        cursor.execute("SELECT COUNT(*) FROM messages WHERE content LIKE ?", [search_pattern])
        content_count = cursor.fetchone()[0]
        logger.info(f"コンテンツでの検索結果数: {content_count}")
        
        # 組み合わせ検索
        cursor.execute("SELECT COUNT(*) FROM messages WHERE (author LIKE ? OR content LIKE ?)", [search_pattern, search_pattern])
        combined_count = cursor.fetchone()[0]
        logger.info(f"組み合わせ検索結果数: {combined_count}")
        
        # 実際のデータ取得
        offset = (page - 1) * per_page
        sql_query = """
            SELECT 
                id, platform, message_id, content, 
                author, channel, timestamp, url
            FROM messages 
            WHERE (author LIKE ? OR content LIKE ?)
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        
        params = [search_pattern, search_pattern, per_page, offset]
        logger.info(f"最終SQL: {sql_query.strip()}")
        logger.info(f"最終パラメータ: {params}")
        
        cursor.execute(sql_query, params)
        results = cursor.fetchall()
        
        logger.info(f"最終結果件数: {len(results)}")
        
        # 結果の詳細ログ
        for i, row in enumerate(results[:3]):  # 最初の3件だけログ出力
            logger.info(f"結果{i+1}: author='{row['author']}', content_preview='{row['content'][:50]}'")
        
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
        
        conn.close()
        
        response_data = {
            'success': True,
            'data': data,
            'total': combined_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (combined_count + per_page - 1) // per_page
        }
        
        logger.info(f"=== レスポンス送信: {len(data)}件のデータ ===")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"検索エラー: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    logger.info(f"デバッグ版サーバーをポート{port}で起動します")
    app.run(debug=True, host='0.0.0.0', port=port)
