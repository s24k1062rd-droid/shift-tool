"""
包括的なテストスクリプト
新規店舗作成、スタッフ追加、削除などの一連の操作をテスト
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
import os
from pathlib import Path

BASE_URL = "http://localhost:5000"
TEST_STORE = "test_comprehensive_001"
TEST_STAFF = "テストスタッフ太郎"

# Cookie管理
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

def make_request(method, url, data=None):
    """リクエスト送信のヘルパー関数"""
    try:
        if data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method=method
            )
        else:
            req = urllib.request.Request(url, method=method)
        
        with urllib.request.urlopen(req) as response:
            return 'success', json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        return 'error', f"HTTP {e.code}: {error_msg}"
    except Exception as e:
        return 'error', str(e)

print("=" * 60)
print("包括的テスト開始")
print("=" * 60)

# テスト1: 新規店舗にログイン
print("\n【テスト1】新規店舗ログイン")
print(f"店舗コード: {TEST_STORE}")

status, result = make_request('POST', f"{BASE_URL}/api/login", {
    "role": "admin",
    "password": "admin123",
    "store_code": TEST_STORE,
    "staff_name": ""
})

if status == 'success' and result.get('success'):
    print("✅ ログイン成功")
    
    # ファイル確認
    data_file = Path("shift_data") / f"{TEST_STORE}_data.json"
    if data_file.exists():
        print(f"✅ 店舗ファイル作成確認: {data_file}")
    else:
        print(f"❌ 店舗ファイルが見当たりません: {data_file}")
else:
    print(f"❌ ログイン失敗: {result}")
    exit(1)

# テスト2: スタッフを追加
print("\n【テスト2】スタッフ追加")
print(f"スタッフ名: {TEST_STAFF}")

status, result = make_request('POST', f"{BASE_URL}/api/staff", {
    "name": TEST_STAFF,
    "type": "社員",
    "priority": 1
})

if status == 'success' and result.get('success'):
    print("✅ スタッフ追加成功")
    
    # ファイル内容確認
    data_file = Path("shift_data") / f"{TEST_STORE}_data.json"
    with open(data_file, 'r', encoding='utf-8') as f:
        content = json.load(f)
    
    if TEST_STAFF in content.get('staff', {}):
        print(f"✅ ファイルにスタッフが保存されています")
        print(f"   スタッフ情報: {content['staff'][TEST_STAFF]}")
    else:
        print(f"❌ ファイルにスタッフが保存されていません")
else:
    print(f"❌ スタッフ追加失敗: {result}")

# テスト3: スタッフリスト取得
print("\n【テスト3】スタッフリスト取得")

status, result = make_request('GET', f"{BASE_URL}/api/staff")

if status == 'success':
    if TEST_STAFF in result:
        print(f"✅ スタッフリストから確認: {result[TEST_STAFF]}")
    else:
        print(f"⚠️ スタッフがリストにありません")
        print(f"   取得されたスタッフ: {list(result.keys())}")
else:
    print(f"❌ スタッフリスト取得失敗: {result}")

# テスト4: スタッフを削除
print("\n【テスト4】スタッフ削除")

status, result = make_request('DELETE', f"{BASE_URL}/api/staff/{urllib.parse.quote(TEST_STAFF)}")

if status == 'success' and result.get('success'):
    print("✅ スタッフ削除成功")
    
    # ファイル内容確認
    data_file = Path("shift_data") / f"{TEST_STORE}_data.json"
    with open(data_file, 'r', encoding='utf-8') as f:
        content = json.load(f)
    
    if TEST_STAFF not in content.get('staff', {}):
        print(f"✅ ファイルからスタッフが削除されています")
    else:
        print(f"❌ ファイルにスタッフがまだ存在しています")
else:
    print(f"❌ スタッフ削除失敗: {result}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)
