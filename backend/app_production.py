from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import os
from flask_cors import CORS
from datetime import datetime
import requests
from notion_client import Client

app = Flask(__name__)
CORS(app)

# 本番環境設定
PORT = int(os.environ.get('PORT', 8000))
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'integrated_search.db')

# API設定（環境変数から取得）
CHATWORK_API_TOKEN = os.environ.get('CHATWORK_API_TOKEN')
NOTION_API_TOKEN = os.environ.get('NOTION_API_TOKEN')

def init_database():
    """データベース初期化"""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                platform TEXT,
                message_id TEXT,
                content TEXT,
                author TEXT,
                channel TEXT,
                timestamp DATETIME,
                url TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ データベースを初期化しました")
        
    except Exception as e:
        print(f"❌ データベース初期化エラー: {e}")

def sync_chatwork_data():
    """Chatworkデータ同期"""
    if not CHATWORK_API_TOKEN:
        print("⚠️ CHATWORK_API_TOKENが設定されていません")
        return 0
    
    try:
        # Chatwork Room一覧を取得
        headers = {'X-ChatWorkToken': CHATWORK_API_TOKEN}
        response = requests.get('https://api.chatwork.com/v2/rooms', headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Chatwork API エラー: {response.status_code}")
            return 0
            
        rooms = response.json()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        saved_count = 0
        
        for room in rooms[:5]:  # 最初の5つのルームのみ処理
            room_id = room['room_id']
            room_name = room['name']
            
            # メッセージを取得
            msg_response = requests.get(
                f'https://api.chatwork.com/v2/rooms/{room_id}/messages',
                headers=headers,
                params={'force': 1}
            )
            
            if msg_response.status_code == 200:
                messages = msg_response.json()
                
                for msg in messages[-20:]:  # 最新20件
                    # 既存チェック
                    cursor.execute(
                        "SELECT COUNT(*) FROM messages WHERE platform='chatwork' AND message_id=?",
                        (str(msg['message_id']),)
                    )
                    
                    if cursor.fetchone()[0] == 0:
                        cursor.execute('''
                            INSERT INTO messages (platform, message_id, content, author, channel, timestamp, url)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            'chatwork',
                            str(msg['message_id']),
                            msg['body'],
                            msg['account']['name'],
                            room_name,
                            datetime.fromtimestamp(msg['send_time']).isoformat(),
                            f"https://www.chatwork.com/#!rid{room_id}-{msg['message_id']}"
                        ))
                        saved_count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Chatwork: {saved_count}件の新しいメッセージを保存")
        return saved_count
        
    except Exception as e:
        print(f"❌ Chatwork同期エラー: {e}")
        return 0

def sync_notion_data():
    """Notionデータ同期"""
    if not NOTION_API_TOKEN:
        print("⚠️ NOTION_API_TOKENが設定されていません")
        return 0
    
    try:
        notion = Client(auth=NOTION_API_TOKEN)
        
        # ページ検索
        results = notion.search()
        pages = results.get('results', [])
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        saved_count = 0
        
        for page in pages[:10]:  # 最初の10件
            page_id = page['id']
            
            # タイトル取得
            title = "無題のページ"
            if 'properties' in page:
                for prop_name, prop_value in page['properties'].items():
                    if prop_value.get('type') == 'title':
                        if prop_value.get('title') and len(prop_value['title']) > 0:
                            title = prop_value['title'][0]['plain_text']
                        break
            
            # ページ内容取得
            try:
                blocks_response = notion.blocks.children.list(block_id=page_id)
                blocks = blocks_response.get('results', [])
                content = extract_text_from_blocks(blocks)
            except:
                content = title
            
            # 既存チェック
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE platform='notion' AND message_id=?",
                (page_id,)
            )
            
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO messages (platform, message_id, content, author, channel, timestamp, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'notion',
                    page_id,
                    content,
                    'Notion User',
                    title,
                    page.get('last_edited_time', datetime.now().isoformat()),
                    page.get('url', f"https://notion.so/{page_id.replace('-', '')}")
                ))
                saved_count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Notion: {saved_count}件の新しいページを保存")
        return saved_count
        
    except Exception as e:
        print(f"❌ Notion同期エラー: {e}")
        return 0

def extract_text_from_blocks(blocks):
    """Notionブロックからテキスト抽出"""
    text_content = []
    
    for block in blocks[:10]:  # 最初の10ブロックのみ
        block_type = block.get('type')
        
        if block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3']:
            rich_text = block.get(block_type, {}).get('rich_text', [])
            text = ''.join([t.get('plain_text', '') for t in rich_text])
            if text.strip():
                text_content.append(text.strip())
    
    return '\n\n'.join(text_content)

def search_messages(query, platform=None, limit=50):
    """検索機能"""
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
    """統計情報取得"""
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
        
        cursor.execute("SELECT MAX(timestamp) as latest_update FROM messages")
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
    """フロントエンド提供"""
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, 'index_fixed.html')

@app.route('/api/sync', methods=['POST'])
def api_sync():
    """データ同期API"""
    chatwork_count = sync_chatwork_data()
    notion_count = sync_notion_data()
    
    return jsonify({
        'success': True,
        'chatwork_synced': chatwork_count,
        'notion_synced': notion_count,
        'total_synced': chatwork_count + notion_count
    })

@app.route('/api/search', methods=['GET'])
def api_search():
    """検索API"""
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
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database_accessible': os.path.exists(DB_PATH),
        'chatwork_token_set': bool(CHATWORK_API_TOKEN),
        'notion_token_set': bool(NOTION_API_TOKEN)
    })

if __name__ == '__main__':
    print("🚀 統合検索システム（本番版）起動中...")
    
    # データベース初期化
    init_database()
    
    # 初回データ同期
    print("🔄 初回データ同期を実行中...")
    chatwork_count = sync_chatwork_data()
    notion_count = sync_notion_data()
    
    # 統計表示
    stats = get_statistics()
    print(f"📊 総データ数: {stats['total_count']}件")
    for platform, count in stats['platforms'].items():
        emoji = "💬" if platform == "chatwork" else "📄"
        print(f"  {emoji} {platform}: {count}件")
    
    print(f"🌐 ポート: {PORT}")
    app.run(host='0.0.0.0', port=PORT)
