#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合検索システム - データ同期スクリプト
Chatwork、Notion、Discordからデータを取得してデータベースに保存
"""

import os
import sys
import sqlite3
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 環境変数を読み込み
load_dotenv()

class DataSyncManager:
    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', './data/search.db')
        self.chatwork_token = os.getenv('CHATWORK_API_TOKEN')
        self.notion_token = os.getenv('NOTION_API_TOKEN')
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID')
        self.discord_token = os.getenv('DISCORD_BOT_TOKEN')
        
    def connect_db(self):
        """データベース接続"""
        return sqlite3.connect(self.db_path)
    
    def sync_chatwork_data(self):
        """Chatworkからデータを同期"""
        print("📱 [Chatwork] データ取得を開始...")
        
        if not self.chatwork_token or self.chatwork_token == 'test_token':
            print("⚠️  Chatwork APIキーが設定されていません")
            return 0
            
        headers = {
            'X-ChatWorkToken': self.chatwork_token
        }
        
        try:
            # ルーム一覧を取得
            rooms_response = requests.get(
                'https://api.chatwork.com/v2/rooms',
                headers=headers
            )
            
            if rooms_response.status_code != 200:
                print(f"❌ Chatwork API エラー: {rooms_response.status_code}")
                return 0
                
            rooms = rooms_response.json()
            total_messages = 0
            
            conn = self.connect_db()
            cursor = conn.cursor()
            
            for room in rooms[:5]:  # 最初の5つのルームのみ
                room_id = room['room_id']
                room_name = room['name']
                
                print(f"📱 ルーム: {room_name} からメッセージを取得中...")
                
                # メッセージを取得
                messages_response = requests.get(
                    f'https://api.chatwork.com/v2/rooms/{room_id}/messages',
                    headers=headers,
                    params={'force': 1}
                )
                
                if messages_response.status_code == 200:
                    messages = messages_response.json()
                    
                    for message in messages[-20:]:  # 最新20件
                        cursor.execute('''
                            INSERT OR REPLACE INTO messages 
                            (platform, message_id, content, author, channel, timestamp, url)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            'chatwork',
                            f"chatwork_{room_id}_{message['message_id']}",
                            message.get('body', ''),
                            message.get('account', {}).get('name', 'Unknown'),
                            room_name,
                            datetime.fromtimestamp(message.get('send_time', 0)),
                            f"https://www.chatwork.com/#!rid{room_id}"
                        ))
                        total_messages += 1
            
            conn.commit()
            conn.close()
            print(f"✅ Chatwork: {total_messages}件のメッセージを同期しました")
            return total_messages
            
        except Exception as e:
            print(f"❌ Chatwork同期エラー: {str(e)}")
            return 0
    
    def sync_notion_data(self):
        """Notionからデータを同期"""
        print("📝 [Notion] データ取得を開始...")
        
        if not self.notion_token or self.notion_token == 'test_token':
            print("⚠️  Notion APIキーが設定されていません")
            return 0
            
        headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        try:
            # ページ検索
            search_response = requests.post(
                'https://api.notion.com/v1/search',
                headers=headers,
                json={
                    'filter': {'property': 'object', 'value': 'page'},
                    'page_size': 20
                }
            )
            
            if search_response.status_code != 200:
                print(f"❌ Notion API エラー: {search_response.status_code}")
                return 0
                
            search_results = search_response.json()
            total_pages = 0
            
            conn = self.connect_db()
            cursor = conn.cursor()
            
            for page in search_results.get('results', []):
                page_id = page['id']
                
                # ページタイトルを取得
                title = ''
                if 'properties' in page:
                    for prop_name, prop_value in page['properties'].items():
                        if prop_value.get('type') == 'title':
                            title_array = prop_value.get('title', [])
                            if title_array:
                                title = title_array[0].get('plain_text', '')
                                break
                
                if not title and 'properties' in page:
                    # タイトルが見つからない場合、最初のテキストプロパティを使用
                    for prop_value in page['properties'].values():
                        if prop_value.get('type') in ['rich_text', 'text']:
                            text_array = prop_value.get('rich_text', [])
                            if text_array:
                                title = text_array[0].get('plain_text', '')[:100]
                                break
                
                cursor.execute('''
                    INSERT OR REPLACE INTO messages 
                    (platform, message_id, content, author, channel, timestamp, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'notion',
                    f"notion_{page_id}",
                    title,
                    'Notion User',
                    'Notion Pages',
                    datetime.fromisoformat(page.get('created_time', '').replace('Z', '+00:00')) if page.get('created_time') else datetime.now(),
                    page.get('url', f"https://notion.so/{page_id}")
                ))
                total_pages += 1
            
            conn.commit()
            conn.close()
            print(f"✅ Notion: {total_pages}件のページを同期しました")
            return total_pages
            
        except Exception as e:
            print(f"❌ Notion同期エラー: {str(e)}")
            return 0
    
    def sync_discord_data(self):
        """Discordからデータを同期"""
        print("💬 [Discord] データ取得を開始...")
        
        if not self.discord_token or self.discord_token == 'test_token':
            print("⚠️  Discord APIキーが設定されていません")
            return 0
            
        # Discord APIは複雑なので、今回は簡単な実装
        print("⚠️  Discord同期は今回スキップします（Bot権限設定が必要）")
        return 0
    
    def run_sync(self):
        """すべてのプラットフォームからデータを同期"""
        print("🔄 統合検索システム - データ同期開始")
        print("=" * 50)
        
        total_synced = 0
        
        # Chatwork同期
        total_synced += self.sync_chatwork_data()
        print()
        
        # Notion同期
        total_synced += self.sync_notion_data()
        print()
        
        # Discord同期
        total_synced += self.sync_discord_data()
        print()
        
        # 同期ログを記録
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sync_logs (timestamp, platform, records_synced, status)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now(), 'all', total_synced, 'completed'))
        conn.commit()
        conn.close()
        
        print("=" * 50)
        print(f"🎉 同期完了！ 総件数: {total_synced}件")
        print("ブラウザでhttp://localhost:5000 にアクセスして検索してみてください！")

if __name__ == '__main__':
    sync_manager = DataSyncManager()
    sync_manager.run_sync()
