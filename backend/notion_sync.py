import os
import sqlite3
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv
import json

# .envファイルから設定を読み込み
load_dotenv()

class NotionSync:
    def __init__(self):
        self.notion_token = os.getenv('NOTION_API_TOKEN')
        self.db_path = '../data/search.db'
        self.notion = Client(auth=self.notion_token)
    
    def extract_text_from_blocks(self, blocks):
        """Notionブロックからテキストを抽出"""
        text_content = []
        
        for block in blocks:
            block_type = block.get('type')
            
            if block_type == 'paragraph':
                rich_text = block['paragraph'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                if text.strip():
                    text_content.append(text.strip())
            
            elif block_type == 'heading_1':
                rich_text = block['heading_1'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                if text.strip():
                    text_content.append(f"# {text.strip()}")
            
            elif block_type == 'heading_2':
                rich_text = block['heading_2'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                if text.strip():
                    text_content.append(f"## {text.strip()}")
            
            elif block_type == 'heading_3':
                rich_text = block['heading_3'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                if text.strip():
                    text_content.append(f"### {text.strip()}")
            
            elif block_type == 'bulleted_list_item':
                rich_text = block['bulleted_list_item'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                if text.strip():
                    text_content.append(f"• {text.strip()}")
            
            elif block_type == 'numbered_list_item':
                rich_text = block['numbered_list_item'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                if text.strip():
                    text_content.append(f"1. {text.strip()}")
            
            elif block_type == 'to_do':
                rich_text = block['to_do'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                checked = block['to_do'].get('checked', False)
                checkbox = "☑️" if checked else "☐"
                if text.strip():
                    text_content.append(f"{checkbox} {text.strip()}")
            
            elif block_type == 'code':
                rich_text = block['code'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                language = block['code'].get('language', 'plain')
                if text.strip():
                    text_content.append(f"```{language}\n{text.strip()}\n```")
            
            elif block_type == 'quote':
                rich_text = block['quote'].get('rich_text', [])
                text = ''.join([t.get('plain_text', '') for t in rich_text])
                if text.strip():
                    text_content.append(f"> {text.strip()}")
        
        return '\n\n'.join(text_content)
    
    def get_page_title(self, page):
        """ページのタイトルを取得"""
        try:
            # ページプロパティからタイトルを取得
            if 'properties' in page:
                for prop_name, prop_value in page['properties'].items():
                    if prop_value.get('type') == 'title':
                        if prop_value.get('title') and len(prop_value['title']) > 0:
                            return prop_value['title'][0]['plain_text']
            
            # タイトルが見つからない場合はIDを使用
            return f"ページ_{page['id'][:8]}"
            
        except Exception as e:
            print(f"⚠️ タイトル取得エラー: {e}")
            return f"ページ_{page['id'][:8]}"
    
    def get_page_content(self, page_id):
        """ページの内容を取得"""
        try:
            # ページの子ブロックを取得
            blocks_response = self.notion.blocks.children.list(block_id=page_id)
            blocks = blocks_response.get('results', [])
            
            # テキスト内容を抽出
            content = self.extract_text_from_blocks(blocks)
            return content
            
        except Exception as e:
            print(f"⚠️ ページ内容取得エラー (ID: {page_id}): {e}")
            return ""
    
    def save_to_database(self, pages_data):
        """取得したページデータをデータベースに保存"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            saved_count = 0
            
            for page_data in pages_data:
                # 既存データのチェック
                cursor.execute("""
                    SELECT COUNT(*) FROM messages 
                    WHERE platform = 'notion' AND message_id = ?
                """, (page_data['id'],))
                
                if cursor.fetchone()[0] == 0:
                    # 新規データを挿入
                    cursor.execute("""
                        INSERT INTO messages (platform, message_id, content, author, channel, timestamp, url)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'notion',
                        page_data['id'],
                        page_data['content'],
                        page_data['author'],
                        page_data['title'],
                        page_data['timestamp'],
                        page_data['url']
                    ))
                    saved_count += 1
                else:
                    print(f"📋 既存データをスキップ: {page_data['title']}")
            
            conn.commit()
            conn.close()
            
            print(f"💾 {saved_count}件の新しいNotionページをデータベースに保存しました")
            return saved_count
            
        except Exception as e:
            print(f"❌ データベース保存エラー: {e}")
            return 0
    
    def sync_notion_data(self, limit=10):
        """Notionデータを同期"""
        print("🔄 Notionデータの取得を開始...")
        
        try:
            # ページ一覧を取得
            results = self.notion.search()
            pages = results.get('results', [])
            
            print(f"📊 {len(pages)}件のページが見つかりました")
            
            # 処理するページ数を制限
            pages_to_process = pages[:limit]
            print(f"🎯 最初の{len(pages_to_process)}件を処理します...")
            
            pages_data = []
            
            for i, page in enumerate(pages_to_process, 1):
                print(f"📖 {i}/{len(pages_to_process)}: 処理中...")
                
                # ページ情報を取得
                title = self.get_page_title(page)
                content = self.get_page_content(page['id'])
                
                # メタデータを取得
                created_time = page.get('created_time', datetime.now().isoformat())
                last_edited_time = page.get('last_edited_time', created_time)
                url = page.get('url', f"https://notion.so/{page['id'].replace('-', '')}")
                
                # 作成者情報（簡略化）
                author = "Notion User"
                if 'created_by' in page and 'id' in page['created_by']:
                    author = f"User_{page['created_by']['id'][:8]}"
                
                page_info = {
                    'id': page['id'],
                    'title': title,
                    'content': content,
                    'author': author,
                    'timestamp': last_edited_time,
                    'url': url
                }
                
                pages_data.append(page_info)
                print(f"✅ 「{title}」を取得完了")
            
            # データベースに保存
            saved_count = self.save_to_database(pages_data)
            
            print(f"\n🎉 同期完了！")
            print(f"📥 取得したページ: {len(pages_data)}件")
            print(f"💾 新規保存したページ: {saved_count}件")
            
            return True
            
        except Exception as e:
            print(f"❌ 同期エラー: {e}")
            return False

def main():
    print("=== Notion データ同期 ===")
    
    # NotionSyncインスタンスを作成
    sync = NotionSync()
    
    # データ同期を実行（最初は10件に制限）
    success = sync.sync_notion_data(limit=10)
    
    if success:
        print("\n✅ Notionデータの同期が完了しました！")
        print("🔍 統合検索システムでChatworkとNotionを横断検索できるようになりました。")
    else:
        print("\n❌ 同期に失敗しました。エラーメッセージを確認してください。")

if __name__ == "__main__":
    main()

