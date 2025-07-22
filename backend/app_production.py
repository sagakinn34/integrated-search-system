from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 本番環境用の設定
PORT = int(os.environ.get('PORT', 8000))
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'search.db')

def search_messages(query, platform=None, limit=50):
    """統合検索機能：ChatworkとNotionを横断検索"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        base_query = """
            SELECT id, platform, message_id, content, author, channel, timestamp, url
            FROM messages 
            WHERE content LIKE ?
        """
        
        params = [f'%{query}%']
        
        if platform and platform in ['chatwork', 'notion']:
            base_query += " AND platform = ?"
            params.append(platform)
        
        base_query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        
        messages = []
        for row in results:
            message = {
                'id': row['id'],
                'platform': row['platform'],
                'message_id': row['message_id'],
                'content': row['content'],
                'author': row['author'],
                'channel': row['channel'],
                'timestamp': row['timestamp'],
                'url': row['url']
            }
            messages.append(message)
        
        conn.close()
        
        return {
            'success': True,
            'query': query,
            'total_results': len(messages),
            'messages': messages
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'messages': []
        }

def get_statistics():
    """データベースの統計情報を取得"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT platform, COUNT(*) as count 
            FROM messages 
            GROUP BY platform
        """)
        platform_stats = dict(cursor.fetchall())
        
        cursor.execute("""
            SELECT MAX(timestamp) as latest_update 
            FROM messages
        """)
        latest_update = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_count': total_count,
            'platforms': platform_stats,
            'latest_update': latest_update
        }
        
    except Exception as e:
        return {
            'total_count': 0,
            'platforms': {},
            'latest_update': None,
            'error': str(e)
        }

@app.route('/')
def index():
    """フロントエンドページの提供"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), '..', 'frontend'), 'index_fixed.html')

@app.route('/api/search', methods=['GET'])
def api_search():
    """統合検索API"""
    query = request.args.get('q', '').strip()
    platform = request.args.get('platform', None)
    limit = int(request.args.get('limit', 50))
    
    if not query:
        return jsonify({
            'success': False,
            'error': '検索クエリが指定されていません',
            'messages': []
        })
    
    result = search_messages(query, platform, limit)
    stats = get_statistics()
    result['stats'] = stats
    
    return jsonify(result)

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """統計情報API"""
    stats = get_statistics()
    return jsonify(stats)

@app.route('/api/health', methods=['GET'])
def api_health():
    """ヘルスチェックAPI"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database_accessible': os.path.exists(DB_PATH)
    })

if __name__ == '__main__':
    print("🚀 統合検索システム（本番版）を起動中...")
    print(f"📊 ポート: {PORT}")
    
    stats = get_statistics()
    print(f"📝 総メッセージ数: {stats['total_count']}件")
    for platform, count in stats['platforms'].items():
        emoji = "💬" if platform == "chatwork" else "📄"
        print(f"  {emoji} {platform.title()}: {count}件")
    
    app.run(host='0.0.0.0', port=PORT)

