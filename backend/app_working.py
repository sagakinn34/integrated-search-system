from flask import Flask, request, jsonify, render_template
import sqlite3
import os
from dotenv import load_dotenv
import logging

# 環境変数を読み込み
load_dotenv()

app = Flask(__name__, template_folder='../frontend')

# ログ設定
logging.basicConfig(level=logging.DEBUG)
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
        
        logger.info(f"検索クエリ: {query}, ページ: {page}")
        
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
        
        # 正しいカラム名を使用したSQL文
        offset = (page - 1) * per_page
        params = [f'%{query}%', f'%{query}%']
        
        # データ取得
        cursor.execute("""
            SELECT 
                id, platform, message_id, content, 
                author, channel, timestamp, url
            FROM messages 
            WHERE (content LIKE ? OR author LIKE ?)
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset])
        
        results = cursor.fetchall()
        
        # 総数取得
        count_params = [f'%{query}%', f'%{query}%']
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM messages 
            WHERE (content LIKE ? OR author LIKE ?)
        """, count_params)
        
        total_count = cursor.fetchone()[0]
        total_pages = (total_count + per_page - 1) // per_page
        
        # 結果を辞書に変換
        data = []
        for row in results:
            data.append({
                'id': row['id'],
                'platform': row['platform'],
                'message_id': row['message_id'],
                'content': row['content'],
                'author': row['author'],
                'channel': row['channel'],
                'timestamp': row['timestamp'],
                'url': row['url']
            })
        
        conn.close()
        
        logger.info(f"検索結果: {len(data)}件, 総数: {total_count}件")
        
        return jsonify({
            'success': True,
            'data': data,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        })
        
    except Exception as e:
        logger.error(f"検索エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)
