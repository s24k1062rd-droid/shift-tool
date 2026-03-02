"""
ログイン機能のテストスクリプト
新規店舗コードでログインして、ファイルが作成されることを確認
"""

import requests
import json
import os
from pathlib import Path

# テスト対象のURL
BASE_URL = "http://localhost:5000"
TEST_STORE_CODE = "test_new_store_001"
DATA_FILE_PATH = Path("c:/Users/81808/Desktop/シフト作成ツール2_dev/shift_data") / f"{TEST_STORE_CODE}_data.json"

print(f"テスト開始")
print(f"テスト店舗コード: {TEST_STORE_CODE}")
print(f"予期されるファイルパス: {DATA_FILE_PATH}")
print()

# 既存ファイルを削除（テスト環境用）
if DATA_FILE_PATH.exists():
    print(f"⚠️ 既存ファイルを削除します: {DATA_FILE_PATH}")
    os.remove(DATA_FILE_PATH)
    print(f"✅ 削除完了")
else:
    print(f"ℹ️ 既存ファイルはありません")

print()

# ログインリクエスト
print("📝 ログインリクエストを送信します...")
login_data = {
    "role": "admin",
    "password": "admin123",  # デフォルトパスワード
    "store_code": TEST_STORE_CODE,
    "staff_name": ""
}

try:
    response = requests.post(f"{BASE_URL}/api/login", json=login_data, timeout=5)
    print(f"📨 レスポンスステータス: {response.status_code}")
    
    result = response.json()
    print(f"📄 レスポンス内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print()
    
    if response.status_code == 200 and result.get('success'):
        print("✅ ログイン成功")
        
        # ファイル確認
        print()
        print("🔍 ファイル確認...")
        
        # 1. ファイル存在確認
        if DATA_FILE_PATH.exists():
            print(f"✅ ファイルが作成されました: {DATA_FILE_PATH}")
            
            # 2. ファイル内容確認
            try:
                with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                    file_content = json.load(f)
                print(f"✅ ファイル内容読み込み成功")
                print(f"📊 内容: {json.dumps(file_content, ensure_ascii=False, indent=2)}")
                
                # 3. 初期データ確認
                required_keys = ['staff', 'shifts', 'requirements', 'shift_settings', 'time_slots', 'admin_password']
                missing_keys = [k for k in required_keys if k not in file_content]
                
                if not missing_keys:
                    print(f"✅ すべての必要なキーが存在します")
                else:
                    print(f"⚠️ 不足しているキー: {missing_keys}")
                
            except Exception as e:
                print(f"❌ ファイル内容の読み込みに失敗: {str(e)}")
        else:
            print(f"❌ ファイルが作成されていません: {DATA_FILE_PATH}")
            print(f"期待される場所: {DATA_FILE_PATH}")
            print(f"親ディレクトリ内容: {list(Path(DATA_FILE_PATH).parent.glob('*'))}")
    else:
        print(f"❌ ログインに失敗しました")
        
except requests.exceptions.RequestException as e:
    print(f"❌ リクエストエラー: {str(e)}")
except Exception as e:
    print(f"❌ 予期しないエラー: {str(e)}")

print()
print("テスト完了")
