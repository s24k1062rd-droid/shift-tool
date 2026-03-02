"""
シンプルなテストスクリプト（外部ライブラリなしで実装）
"""

import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:5000"
TEST_STORE_CODE = "test_new_store_003"

print(f"テスト開始: {TEST_STORE_CODE}")

login_data = {
    "role": "admin",
    "password": "admin123",
    "store_code": TEST_STORE_CODE,
    "staff_name": ""
}

try:
    # ログインリクエスト
    req = urllib.request.Request(
        f"{BASE_URL}/api/login",
        data=json.dumps(login_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print(f"✅ ログイン成功: {result}")
        
except urllib.error.HTTPError as e:
    error_msg = e.read().decode('utf-8')
    print(f"❌ HTTPエラー ({e.code}): {error_msg}")
except Exception as e:
    print(f"❌ エラー: {str(e)}")

# ファイル確認
import os
from pathlib import Path

data_file = Path("shift_data") / f"{TEST_STORE_CODE}_data.json"
print()
print(f"ファイル確認: {data_file}")
if data_file.exists():
    print(f"✅ ファイルが存在します")
    with open(data_file, 'r', encoding='utf-8') as f:
        content = json.load(f)
        print(f"📊 キー: {list(content.keys())}")
else:
    print(f"❌ ファイルが存在しません")
