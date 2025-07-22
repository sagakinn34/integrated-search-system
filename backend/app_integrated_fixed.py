from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from flask_cors import CORS
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# データベースパス
DB_PATH = '../data/search.db'

def search_messages(query, platform=None, limit=50):
    """統合検索機能：ChatworkとNotionを横断検索"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
        cursor = conn.cursor()
        
        # 基本的な検索クエリ
        base_query = """
            SELECT id, platform, message_id, content, author, channel, timestamp, url
            FROM messages 
            WHERE content LIKE ?
        """
        
        params = [f'%{query}%']
        
        # プラットフォーム指定がある場合
        if platform and platform in ['chatwork', 'notion']:
            base_query += " AND platform = ?"
            params.append(platform)
        
        # 日付順で並び替え（新しい順）
        base_query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(base_query, params)
        results = cursor.fetchall()
        
        # 結果を辞書形式に変換
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
        
        # 総件数
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_count = cursor.fetchone()[0]
        
        # プラットフォーム別件数
        cursor.execute("""
            SELECT platform, COUNT(*) as count 
            FROM messages 
            GROUP BY platform
        """)
        platform_stats = dict(cursor.fetchall())
        
        # 最新更新日時
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
    return send_from_directory('../frontend', 'index_fixed.html')

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
    
    # 検索実行
    result = search_messages(query, platform, limit)
    
    # 統計情報も含める
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
    print("🚀 統合検索システムを起動中...")
    print("📊 データベース統計:")
    
    stats = get_statistics()
    print(f"  📝 総メッセージ数: {stats['total_count']}件")
    for platform, count in stats['platforms'].items():
        emoji = "💬" if platform == "chatwork" else "📄"
        print(f"  {emoji} {platform.title()}: {count}件")
    
    print("\n🌐 アクセス方法:")
    print("  🔍 検索画面: http://localhost:8000")
    print("  🔗 API: http://localhost:8000/api/search?q=検索語")
    print("  📊 統計: http://localhost:8000/api/stats")
    
    app.run(host='0.0.0.0', port=8000, debug=True)

