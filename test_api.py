#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
アプリケーション起動確認スクリプト
"""

import sys
import json
from io import StringIO

# アプリケーションのインポート
try:
    from app import app, load_data, get_default_shift_settings
    print("✅ app.py のインポート成功")
except Exception as e:
    print(f"❌ app.py のインポート失敗: {e}")
    sys.exit(1)

# テストクライアントを使用して、管理者ログインをシミュレート
try:
    with app.app_context():
        # テスト用のクライアントを作成
        client = app.test_client()
        
        # テストセッション用の環境設定
        with client:
            # まず、ログインして セッション情報を設定
            print("\n" + "="*50)
            print("テスト1: ログイン機能確認")
            print("="*50)
            
            # ログインエンドポイントへのリクエスト（POST）
            response = client.post('/login', json={
                'store_code': 'test_store',
                'role': 'admin',
                'password': 'admin123'
            })
            
            print(f"ログインレスポンス: {response.status_code}")
            if response.status_code == 200:
                print("✅ ログイン成功")
            else:
                print(f"⚠️ ログイン状態コード: {response.status_code}")
            
            # 詳細設定の取得テスト
            print("\n" + "="*50)
            print("テスト2: /api/shift-settings GET")
            print("="*50)
            
            response = client.get('/api/shift-settings')
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"✅ レスポンス取得成功")
                print(f"   - mode: {data.get('mode')}")
                print(f"   - time_slots: {len(data.get('time_slots', []))} 個")
                print(f"   - staff_types: {data.get('staff_types', [])}")
                print(f"   - settings キー: {list(data.get('settings', {}).keys())}")
            else:
                print(f"❌ エラー: {response.status_code}")
            
            # 詳細設定の更新テスト
            print("\n" + "="*50)
            print("テスト3: /api/shift-settings POST（平日・週末モード）")
            print("="*50)
            
            settings_payload = {
                "settings": {
                    "weekday_weekend": {
                        "weekday": {
                            "10-15": {"社員": 1, "アルバイト": 1},
                            "17-23": {"社員": 1, "アルバイト": 0},
                            "18-23": {"社員": 1, "アルバイト": 1},
                            "19-23": {"社員": 1, "アルバイト": 2}
                        },
                        "weekend": {
                            "10-15": {"社員": 1, "アルバイト": 1},
                            "17-23": {"社員": 1, "アルバイト": 1},
                            "18-23": {"社員": 1, "アルバイト": 2},
                            "19-23": {"社員": 1, "アルバイト": 3}
                        }
                    },
                    "daily": {}
                },
                "mode": "weekday_weekend"
            }
            
            response = client.post('/api/shift-settings',
                                 data=json.dumps(settings_payload),
                                 content_type='application/json')
            
            print(f"ステータスコード: {response.status_code}")
            if response.status_code == 200:
                print("✅ 設定保存成功")
                data = json.loads(response.data)
                print(f"   - レスポンス: {data}")
            else:
                print(f"❌ エラー: {response.status_code}")
                print(f"   - レスポンス: {response.data}")
            
            # 曜日ごとモードへの更新テスト
            print("\n" + "="*50)
            print("テスト4: /api/shift-settings POST（曜日ごとモード）")
            print("="*50)
            
            daily_settings = {
                "settings": {
                    "weekday_weekend": {},
                    "daily": {
                        str(i): {
                            "10-15": {"社員": 1, "アルバイト": 1},
                            "17-23": {"社員": 1, "アルバイト": 0},
                        }
                        for i in range(7)
                    }
                },
                "mode": "daily"
            }
            
            response = client.post('/api/shift-settings',
                                 data=json.dumps(daily_settings),
                                 content_type='application/json')
            
            print(f"ステータスコード: {response.status_code}")
            if response.status_code == 200:
                print("✅ 曜日ごと設定保存成功")
                data = json.loads(response.data)
                print(f"   - レスポンス: {data}")
            else:
                print(f"❌ エラー: {response.status_code}")
            
            print("\n" + "="*50)
            print("🎉 アプリケーション動作確認完了！")
            print("="*50)

except Exception as e:
    print(f"❌ テスト実行中にエラーが発生: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
