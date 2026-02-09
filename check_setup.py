#!/usr/bin/env python3
"""
Cloudflare Tunnel セットアップヘルパー
cloudflared をインストール後、このスクリプトで接続確認ができます
"""

import subprocess
import sys
import os

def check_cloudflared():
    """cloudflared がインストールされているか確認"""
    try:
        result = subprocess.run(['cloudflared', '--version'], 
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ Cloudflared がインストールされています: {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("✗ Cloudflared がインストールされていません")
    return False

def check_flask():
    """Flask がインストールされているか確認"""
    try:
        import flask
        print(f"✓ Flask がインストールされています: {flask.__version__}")
        return True
    except ImportError:
        print("✗ Flask がインストールされていません")
        return False

def check_python():
    """Python バージョン確認"""
    print(f"✓ Python バージョン: {sys.version.split()[0]}")
    return True

def main():
    print("=" * 50)
    print("  シフト作成ツール - セットアップ確認")
    print("=" * 50)
    print()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # チェック実行
    checks = [
        ("Python", check_python),
        ("Flask", check_flask),
        ("Cloudflare Tunnel", check_cloudflared),
    ]
    
    all_ok = True
    for name, check_func in checks:
        try:
            if not check_func():
                all_ok = False
        except Exception as e:
            print(f"✗ {name} チェックエラー: {e}")
            all_ok = False
        print()
    
    if all_ok:
        print("✓ すべてのセットアップが完了しました！")
        print()
        print("起動コマンド:")
        print("  1. Flask サーバーを起動:")
        print("     python app.py")
        print()
        print("  2. 別のターミナルで Tunnel を起動:")
        print("     cloudflared tunnel --url http://localhost:5000")
        print()
        print("  または、バッチファイルを使用:")
        print("     run_external.bat をダブルクリック")
    else:
        print("✗ セットアップが完了していない項目があります")
        print("詳細は SETUP_EXTERNAL.md を参照してください")
        sys.exit(1)

if __name__ == '__main__':
    main()
