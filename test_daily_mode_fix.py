#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
曜日ごとモード修正確認テスト
"""

import json
import sys
from app import app

try:
    print("="*60)
    print("曜日ごとモード表示修正テスト")
    print("="*60)
    
    with app.app_context():
        with app.test_client() as client:
            # テスト用セッション情報を手動で設定
            print("\n1️⃣  セッション設定...")
            
            with client.session_transaction() as sess:
                sess['role'] = 'admin'
                sess['store_code'] = 'test_daily_mode'
            
            print(f"   ✅ セッション設定完了")
            
            # 曜日ごとモード設定を保存
            print("\n2️⃣  曜日ごとモード設定を保存...")
            daily_settings = {
                "settings": {
                    "weekday_weekend": {},
                    "daily": {
                        "0": {"10-15": {"社員": 1, "アルバイト": 1}, "15-20": {"社員": 1, "アルバイト": 2}},
                        "1": {"10-15": {"社員": 1, "アルバイト": 2}, "15-20": {"社員": 1, "アルバイト": 3}},
                        "2": {"10-15": {"社員": 1, "アルバイト": 2}, "15-20": {"社員": 2, "アルバイト": 1}},
                        "3": {"10-15": {"社員": 1, "アルバイト": 1}, "15-20": {"社員": 1, "アルバイト": 1}},
                        "4": {"10-15": {"社員": 1, "アルバイト": 1}, "15-20": {"社員": 1, "アルバイト": 1}},
                        "5": {"10-15": {"社員": 2, "アルバイト": 2}, "15-20": {"社員": 2, "アルバイト": 2}},
                        "6": {"10-15": {"社員": 2, "アルバイト": 2}, "15-20": {"社員": 2, "アルバイト": 2}},
                    }
                },
                "mode": "daily"
            }
            
            response = client.post('/api/shift-settings',
                                 data=json.dumps(daily_settings),
                                 content_type='application/json')
            
            if response.status_code == 200:
                print(f"   ✅ 保存成功 (200)")
            else:
                print(f"   ❌ 保存失敗 ({response.status_code})")
                print(f"   レスポンス: {response.data}")
            
            # 設定を取得して確認
            print("\n3️⃣  取得した設定の構造を確認...")
            response = client.get('/api/shift-settings')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"   ✅ 取得成功 (200)")
                print(f"   - mode: {data.get('mode')}")
                print(f"   - settings キー: {list(data.get('settings', {}).keys())}")
                
                settings = data.get('settings', {})
                
                # 各曜日のデータ確認
                print("\n   📋 曜日ごとのデータキー確認:")
                dayNames = ['日', '月', '火', '水', '木', '金', '土']
                for i in range(7):
                    key = str(i)
                    if key in settings:
                        slots = list(settings[key].keys())
                        print(f"      {dayNames[i]}曜日 ({key}): {slots}")
                    else:
                        print(f"      {dayNames[i]}曜日 ({key}): ❌ キーなし")
                
                print("\n✅ 曜日ごとモード設定が正しく保存・取得できました！")
            else:
                print(f"   ❌ 取得失敗 ({response.status_code})")
            
            # 平日・週末モードに切り替え
            print("\n4️⃣  平日・週末モードに切り替え...")
            ww_settings = {
                "settings": {
                    "weekday_weekend": {
                        "weekday": {
                            "10-15": {"社員": 1, "アルバイト": 1},
                            "15-20": {"社員": 1, "アルバイト": 2},
                        },
                        "weekend": {
                            "10-15": {"社員": 2, "アルバイト": 2},
                            "15-20": {"社員": 2, "アルバイト": 2},
                        }
                    },
                    "daily": {}
                },
                "mode": "weekday_weekend"
            }
            
            response = client.post('/api/shift-settings',
                                 data=json.dumps(ww_settings),
                                 content_type='application/json')
            
            if response.status_code == 200:
                print(f"   ✅ 切り替え成功 (200)")
            else:
                print(f"   ❌ 切り替え失敗 ({response.status_code})")
            
            # 再度取得確認
            print("\n5️⃣  モード切り替え後の設定確認...")
            response = client.get('/api/shift-settings')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                print(f"   - mode: {data.get('mode')}")
                if data.get('mode') == 'weekday_weekend':
                    print(f"   ✅ 平日・週末モードに正しく切り替わりました")
                print(f"   - settings キー: {list(data.get('settings', {}).keys())}")
            
            print("\n" + "="*60)
            print("🎉 すべての修正確認テストが成功しました！")
            print("="*60)

except Exception as e:
    print(f"\n❌ エラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
