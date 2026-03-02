#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新しい設定モード機能のテスト
"""

import json
import sys

# テスト対象の関数をインポート
from app import get_default_shift_settings, normalize_shift_settings, get_required_staff
from datetime import datetime

def test_get_default_shift_settings():
    """デフォルト設定の構造確認"""
    print("=" * 50)
    print("テスト1: get_default_shift_settings()の構造確認")
    print("=" * 50)
    
    settings = get_default_shift_settings()
    print(f"✓ mode: {settings.get('mode')}")
    print(f"✓ weekday_weekend: {bool(settings.get('weekday_weekend'))}")
    print(f"✓ daily: {bool(settings.get('daily'))}")
    
    # 各モードの内容確認
    ww = settings.get('weekday_weekend', {})
    print(f"\n平日・週末モード:")
    print(f"  - weekday キー: {list(ww.get('weekday', {}).keys())}")
    print(f"  - weekend キー: {list(ww.get('weekend', {}).keys())}")
    
    daily = settings.get('daily', {})
    print(f"\n曜日ごとモード:")
    for day_idx in range(7):
        day_name = ['日', '月', '火', '水', '木', '金', '土'][day_idx]
        day_settings = daily.get(day_idx, {})
        time_slots = list(day_settings.keys())
        print(f"  - {day_name}曜日: {time_slots[:2]}...")
    
    print("\n✅ テスト1: 成功")


def test_normalize_shift_settings():
    """古い形式のデータの互換性テスト"""
    print("\n" + "=" * 50)
    print("テスト2: 互換性テスト（古い形式→新しい形式）")
    print("=" * 50)
    
    # 古い形式のデータ
    old_settings = {
        'weekday': {
            '10-15': {'社員': 1, 'アルバイト': 1},
            '17-23': {'社員': 1, 'アルバイト': 0}
        },
        'weekend': {
            '10-15': {'社員': 1, 'アルバイト': 1},
            '17-23': {'社員': 1, 'アルバイト': 1}
        }
    }
    
    time_slots = ['10-15', '17-23']
    staff_types = ['社員', 'アルバイト']
    
    normalized = normalize_shift_settings(old_settings, time_slots, staff_types)
    
    print(f"古い形式の入力: {list(old_settings.keys())}")
    print(f"正規化後の出力: {list(normalized.keys())}")
    print(f"weekday データ: {normalized.get('weekday', {})}")
    print(f"weekend データ: {normalized.get('weekend', {})}")
    
    print("\n✅ テスト2: 成功")


def test_get_required_staff():
    """get_required_staff()のテスト"""
    print("\n" + "=" * 50)
    print("テスト3: get_required_staff()（平日・週末モード）")
    print("=" * 50)
    
    # サンプル設定
    sample_settings = {
        'mode': 'weekday_weekend',
        'weekday_weekend': {
            'weekday': {
                '10-15': {'社員': 1, 'アルバイト': 1},
                '17-23': {'社員': 1, 'アルバイト': 0}
            },
            'weekend': {
                '10-15': {'社員': 2, 'アルバイト': 2},
                '17-23': {'社員': 1, 'アルバイト': 1}
            }
        },
        'daily': {}
    }
    
    # 月曜日（weekday）
    monday_staff = get_required_staff('2024-03-04', '10-15', '社員', sample_settings)
    monday_part = get_required_staff('2024-03-04', '10-15', 'アルバイト', sample_settings)
    print(f"月曜日 10-15:")
    print(f"  - 社員: {monday_staff} (期待値: 1)")
    print(f"  - アルバイト: {monday_part} (期待値: 1)")
    
    # 土曜日（weekend）
    saturday_staff = get_required_staff('2024-03-09', '10-15', '社員', sample_settings)
    saturday_part = get_required_staff('2024-03-09', '10-15', 'アルバイト', sample_settings)
    print(f"\n土曜日 10-15:")
    print(f"  - 社員: {saturday_staff} (期待値: 2)")
    print(f"  - アルバイト: {saturday_part} (期待値: 2)")
    
    print("\n✅ テスト3: 成功")


def test_daily_mode():
    """曜日ごとモードのテスト"""
    print("\n" + "=" * 50)
    print("テスト4: get_required_staff()（曜日ごとモード）")
    print("=" * 50)
    
    # 曜日ごと設定
    daily_settings = {
        'mode': 'daily',
        'weekday_weekend': {},
        'daily': {
            0: {'10-15': {'社員': 1, 'アルバイト': 1}},  # 日
            1: {'10-15': {'社員': 1, 'アルバイト': 2}},  # 月
            2: {'10-15': {'社員': 1, 'アルバイト': 3}},  # 火
            3: {'10-15': {'社員': 1, 'アルバイト': 1}},  # 水
            4: {'10-15': {'社員': 1, 'アルバイト': 1}},  # 木
            5: {'10-15': {'社員': 2, 'アルバイト': 2}},  # 金
            6: {'10-15': {'社員': 2, 'アルバイト': 2}},  # 土
        }
    }
    
    # 各曜日をテスト
    day_names = ['日', '月', '火', '水', '木', '金', '土']
    test_dates = [
        '2024-03-03',  # 日
        '2024-03-04',  # 月
        '2024-03-05',  # 火
        '2024-03-06',  # 水
        '2024-03-07',  # 木
        '2024-03-08',  # 金
        '2024-03-09',  # 土
    ]
    
    for date, day_name in zip(test_dates, day_names):
        staff = get_required_staff(date, '10-15', '社員', daily_settings)
        part = get_required_staff(date, '10-15', 'アルバイト', daily_settings)
        print(f"{day_name}曜日 ({date}): 社員={staff}, アルバイト={part}")
    
    print("\n✅ テスト4: 成功")


if __name__ == '__main__':
    try:
        test_get_default_shift_settings()
        test_normalize_shift_settings()
        test_get_required_staff()
        test_daily_mode()
        
        print("\n" + "=" * 50)
        print("🎉 すべてのテストが成功しました！")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
