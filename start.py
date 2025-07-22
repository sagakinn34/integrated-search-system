#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 統合検索システム - 簡単起動スクリプト

このスクリプトを実行すると、システムを簡単に起動できます。
初回実行時は自動的にデータベースの初期化も行います。
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path

def check_python_version():
    """Pythonバージョンをチェック"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7以上が必要です")
        print(f"現在のバージョン: {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} - OK")
    return True

def check_requirements():
    """必要なパッケージがインストールされているかチェック"""
    required_packages = ['flask', 'requests', 'python-dotenv']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} - インストール済み")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - 未インストール")

    return missing_packages

def install_requirements():
    """必要なパッケージをインストール"""
    print("📦 必要なパッケージをインストールしています...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "-r", "requirements.txt", "--quiet"
        ])
        print("✅ パッケージのインストールが完了しました")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ パッケージインストールエラー: {e}")
        return False

def check_env_file():
    """環境ファイルをチェック"""
    if not os.path.exists('.env'):
        print("⚠️  .envファイルが見つかりません")
        print("👉 .env.sampleをコピーして.envファイルを作成してください")

        # .env.sampleから.envを自動作成
        if os.path.exists('.env.sample'):
            print("📋 .env.sampleから.envファイルを作成しています...")
            import shutil
            shutil.copy('.env.sample', '.env')
            print("✅ .envファイルを作成しました")
            print("🔑 APIトークンを設定してください")
        return False
    else:
        print("✅ .envファイル - 見つかりました")
        return True

def initialize_database():
    """データベースを初期化"""
    if not os.path.exists('database/integrated_search.db'):
        print("🗄️ データベースを初期化しています...")
        try:
            subprocess.check_call([sys.executable, "database/init_db.py"])
            print("✅ データベースの初期化が完了しました")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ データベース初期化エラー: {e}")
            return False
    else:
        print("✅ データベース - 存在します")
        return True

def create_logs_folder():
    """ログフォルダを作成"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("✅ logsフォルダを作成しました")

def check_port_availability(port=5000):
    """ポートが使用可能かチェック"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            print(f"✅ ポート {port} - 使用可能")
            return True
    except OSError:
        print(f"⚠️  ポート {port} は既に使用されています")
        return False

def start_application():
    """アプリケーションを起動"""
    print("🌐 Webサーバーを起動しています...")
    print("=" * 60)
    print("📍 ブラウザで http://localhost:5000 にアクセスしてください")
    print("🛑 停止するには Ctrl+C を押してください")
    print("=" * 60)

    try:
        subprocess.run([sys.executable, "backend/app.py"])
    except KeyboardInterrupt:
        print("\n✋ アプリケーションを停止しました")
    except Exception as e:
        print(f"❌ アプリケーション起動エラー: {e}")

def main():
    """メイン処理"""
    print("🚀 統合検索システム - 起動チェック")
    print("=" * 50)

    # 1. Pythonバージョンチェック
    if not check_python_version():
        return

    # 2. 必要パッケージのチェック
    missing_packages = check_requirements()
    if missing_packages:
        print("\n📦 不足しているパッケージをインストールします...")
        if not install_requirements():
            print("❌ パッケージインストールに失敗しました")
            print("手動で以下のコマンドを実行してください:")
            print("pip install -r requirements.txt")
            return

    # 3. 環境ファイルチェック
    env_exists = check_env_file()

    # 4. ログフォルダ作成
    create_logs_folder()

    # 5. データベース初期化
    if not initialize_database():
        return

    # 6. ポート使用可能性チェック
    if not check_port_availability():
        print("別のポートを使用するか、既存のプロセスを停止してください")

    print("\n✅ 全ての前提条件がクリアされました！")

    if not env_exists:
        print("\n⚠️  APIトークンが設定されていません")
        print("現在はテストデータのみで動作します")
        print("実際のデータを取得するには.envファイルでAPIトークンを設定してください")

    print("\n🎉 システムを起動します...")

    # アプリケーション起動
    start_application()

if __name__ == "__main__":
    main()
