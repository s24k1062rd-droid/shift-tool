"""
ngrokを使用してシフト作成ツールを外部アクセス可能にするスクリプト
"""

from pyngrok import ngrok
import subprocess
import sys
import time
import os

def main():
    print("=" * 60)
    print("  シフト作成ツール - 外部アクセス起動")
    print("=" * 60)
    print()
    
    # ngrokトンネルを作成
    print("📡 ngrokトンネルを作成中...")
    try:
        # ポート5000へのHTTPトンネルを作成
        public_url = ngrok.connect(5000, bind_tls=True)
        print()
        print("✅ 外部アクセスURL:")
        print(f"   {public_url}")
        print()
        print("=" * 60)
        print("📱 このURLをスマホやPCのブラウザで開いてください")
        print("=" * 60)
        print()
        print("終了する場合は Ctrl+C を押してください")
        print()
        
        # Flaskアプリを起動
        venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')
        app_file = os.path.join(os.path.dirname(__file__), 'app.py')
        
        process = subprocess.Popen([venv_python, app_file])
        
        # プロセスが終了するまで待機
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  サーバーを停止しています...")
        ngrok.kill()
        print("✅ 停止しました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("\nngrokのインストールと設定を確認してください")
        print("詳細: https://ngrok.com/")
        sys.exit(1)

if __name__ == "__main__":
    main()
