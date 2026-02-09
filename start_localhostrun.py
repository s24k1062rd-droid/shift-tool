"""
localhost.runを使用してシフト作成ツールを外部アクセス可能にするスクリプト
認証不要で即座に使えます
"""

import subprocess
import sys
import threading
import time
import re

def run_flask():
    """Flaskアプリをバックグラウンドで実行"""
    import os
    venv_python = os.path.join(os.path.dirname(__file__), '.venv', 'Scripts', 'python.exe')
    app_file = os.path.join(os.path.dirname(__file__), 'app.py')
    subprocess.run([venv_python, app_file])

def main():
    print("=" * 60)
    print("  シフト作成ツール - 外部アクセス起動")
    print("  （localhost.run使用・認証不要）")
    print("=" * 60)
    print()
    
    # Flaskをバックグラウンドで起動
    print("🚀 Flaskサーバーを起動中...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Flaskの起動を待機
    time.sleep(3)
    print("✅ Flaskサーバーが起動しました")
    print()
    
    # localhost.runトンネルを作成
    print("📡 SSH tunnelを作成中...")
    print("   （初回起動時は少し時間がかかる場合があります）")
    print()
    
    try:
        # SSHコマンドでlocalhost.runに接続
        # -R 80:localhost:5000 でリモートポート80をローカル5000に転送
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ServerAliveInterval=60', 
               '-R', '80:localhost:5000', 'nokey@localhost.run']
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 出力を監視してURLを抽出
        url_found = False
        for line in process.stdout:
            print(line.rstrip())
            
            # URLを検出
            if not url_found and 'https://' in line:
                # URLを抽出
                match = re.search(r'https://[a-zA-Z0-9.-]+\.lhr\.life', line)
                if match:
                    url = match.group(0)
                    print()
                    print("=" * 60)
                    print("✅ 外部アクセスURL:")
                    print(f"   {url}")
                    print("=" * 60)
                    print()
                    print("📱 このURLをスマホやPCのブラウザで開いてください")
                    print()
                    print("=" * 60)
                    print()
                    print("⚠️  注意: このURLは毎回変わります")
                    print("終了する場合は Ctrl+C を押してください")
                    print()
                    url_found = True
        
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  サーバーを停止しています...")
        print("✅ 停止しました")
    except FileNotFoundError:
        print("\n❌ エラー: SSHが見つかりません")
        print("\nWindows 10/11の場合、以下の手順でSSHを有効化してください:")
        print("1. 設定 > アプリ > オプション機能")
        print("2. 'OpenSSH クライアント' を追加")
        print()
        print("または、ngrokを使用してください（無料アカウントが必要）")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
