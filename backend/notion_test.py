import os
from notion_client import Client
from dotenv import load_dotenv

# .envファイルから設定を読み込み
load_dotenv()

def test_notion_connection():
    """Notionとの接続をテストする関数"""
    
    # APIトークンを取得
    notion_token = os.getenv('NOTION_API_TOKEN')
    
    if not notion_token:
        print("❌ エラー: NOTION_API_TOKENが.envファイルに設定されていません")
        return False
    
    try:
        # Notionクライアントを作成
        notion = Client(auth=notion_token)
        
        # 接続テスト：利用可能なページ一覧を取得
        print("🔄 Notionに接続中...")
        
        # 検索を実行（空の検索で全ページを取得）
        results = notion.search()
        
        print("✅ Notionとの接続に成功しました！")
        print(f"📊 アクセス可能なページ・データベース数: {len(results['results'])}件")
        
        # 取得したページの情報を表示
        if results['results']:
            print("\n📋 アクセス可能なページ一覧:")
            for i, page in enumerate(results['results'][:5]):  # 最初の5件だけ表示
                page_type = "📄 ページ" if page['object'] == 'page' else "🗃️ データベース"
                title = ""
                
                # タイトルを取得（形式が複雑なので安全に取得）
                if 'properties' in page and 'title' in page['properties']:
                    # データベースの場合
                    title_prop = page['properties']['title']
                    if 'title' in title_prop and title_prop['title']:
                        title = title_prop['title'][0]['plain_text']
                elif 'properties' in page:
                    # ページの場合、Name プロパティを探す
                    for prop_name, prop_value in page['properties'].items():
                        if prop_value.get('type') == 'title':
                            if prop_value['title']:
                                title = prop_value['title'][0]['plain_text']
                            break
                
                if not title:
                    title = "（タイトルなし）"
                
                print(f"  {i+1}. {page_type} - {title}")
                print(f"     ID: {page['id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: Notionとの接続に失敗しました")
        print(f"詳細: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Notion接続テスト ===")
    test_notion_connection()

