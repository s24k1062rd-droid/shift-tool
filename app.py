"""
オンラインシフト入力＆作成ツール（Web版）
スマホ対応
"""

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_session import Session
import json
import os
from datetime import datetime, timedelta
import threading
import calendar
import csv
from io import StringIO, BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

app = Flask(__name__)
app.config['SECRET_KEY'] = 'shift-tool-secret-key-2026'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
Session(app)

# 管理者パスワード（環境変数またはデフォルト値）
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# データファイルのパス
DATA_FILE = 'shift_data.json'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSISTENT_STORAGE_PATH = os.getenv('PERSISTENT_STORAGE_PATH', '').strip()

if PERSISTENT_STORAGE_PATH:
    # Render Disk などの永続ストレージを使う場合
    SHIFT_DATA_DIR = os.path.join(PERSISTENT_STORAGE_PATH, 'shift_data')
else:
    SHIFT_DATA_DIR = os.path.join(BASE_DIR, 'shift_data')

os.makedirs(SHIFT_DATA_DIR, exist_ok=True)
print(f"[INFO] SHIFT_DATA_DIR: {SHIFT_DATA_DIR}")

# スタッフ追加のスレッドセーフなロック
staff_lock = threading.Lock()

def get_default_password_for_store(store_code):
    """店舗ごとのデフォルトパスワードを取得（環境変数を優先）"""
    # 環境変数から店舗固有のパスワードを取得
    # 例: PUKU-SMB の場合は ADMIN_PASSWORD_PUKU_SMB
    env_key = f'ADMIN_PASSWORD_{store_code.replace("-", "_").upper()}'
    env_password = os.getenv(env_key)
    if env_password:
        return env_password
    # 環境変数がない場合はデフォルト
    return ADMIN_PASSWORD

# 日本の祝日リスト（2024-2027年の主な祝日）
# 年を超えた場合は適切に拡張してください
JAPAN_HOLIDAYS = {
    # 2024年
    '2024-01-01': '元日',
    '2024-01-08': '成人の日',
    '2024-02-11': '建国記念の日',
    '2024-02-12': '振替休日',
    '2024-03-20': '春分の日',
    '2024-04-29': '昭和の日',
    '2024-05-03': '憲法記念日',
    '2024-05-04': 'みどりの日',
    '2024-05-05': 'こどもの日',
    '2024-05-06': '振替休日',
    '2024-07-15': '海の日',
    '2024-08-11': '山の日',
    '2024-08-12': '振替休日',
    '2024-09-16': '敬老の日',
    '2024-09-22': '秋分の日',
    '2024-09-23': '振替休日',
    '2024-10-14': 'スポーツの日',
    '2024-11-03': '文化の日',
    '2024-11-04': '振替休日',
    '2024-11-23': '勤労感謝の日',
    # 2025年
    '2025-01-01': '元日',
    '2025-01-13': '成人の日',
    '2025-02-11': '建国記念の日',
    '2025-03-20': '春分の日',
    '2025-04-29': '昭和の日',
    '2025-05-03': '憲法記念日',
    '2025-05-04': 'みどりの日',
    '2025-05-05': 'こどもの日',
    '2025-05-06': '振替休日',
    '2025-07-21': '海の日',
    '2025-08-11': '山の日',
    '2025-09-15': '敬老の日',
    '2025-09-23': '秋分の日',
    '2025-10-13': 'スポーツの日',
    '2025-11-03': '文化の日',
    '2025-11-23': '勤労感謝の日',
    '2025-11-24': '振替休日',
    # 2026年
    '2026-01-01': '元日',
    '2026-01-12': '成人の日',
    '2026-02-11': '建国記念の日',
    '2026-03-20': '春分の日',
    '2026-03-21': '振替休日',
    '2026-04-29': '昭和の日',
    '2026-05-03': '憲法記念日',
    '2026-05-04': 'みどりの日',
    '2026-05-05': 'こどもの日',
    '2026-05-06': '振替休日',
    '2026-07-20': '海の日',
    '2026-08-10': '山の日',
    '2026-09-21': '敬老の日',
    '2026-09-22': '秋分の日',
    '2026-10-12': 'スポーツの日',
    '2026-11-03': '文化の日',
    '2026-11-23': '勤労感謝の日',
    # 2027年
    '2027-01-01': '元日',
    '2027-01-11': '成人の日',
    '2027-02-11': '建国記念の日',
    '2027-03-21': '春分の日',
    '2027-04-29': '昭和の日',
    '2027-05-03': '憲法記念日',
    '2027-05-04': 'みどりの日',
    '2027-05-05': 'こどもの日',
    '2027-07-19': '海の日',
    '2027-08-11': '山の日',
    '2027-09-20': '敬老の日',
    '2027-09-23': '秋分の日',
    '2027-10-11': 'スポーツの日',
    '2027-11-03': '文化の日',
    '2027-11-23': '勤労感謝の日',
}

def is_holiday(date_obj):
    """指定日が祝日かどうかを判定"""
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
    elif isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    date_str = date_obj.strftime('%Y-%m-%d')
    return date_str in JAPAN_HOLIDAYS

def is_day_before_holiday(date_obj):
    """指定日が祝日の前日かどうかを判定"""
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
    elif isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    next_day = date_obj + timedelta(days=1)
    next_day_str = next_day.strftime('%Y-%m-%d')
    return next_day_str in JAPAN_HOLIDAYS

def get_day_type(date_str):
    """
    指定日の種類を返す
    返り値: 'sunday' (日), 'mon_thu' (月-木), 'friday' (金), 'saturday' (土), 'holiday' (祝日), 'day_before_holiday' (祝日前日)
    
    優先順位: 祝前日 > 曜日（金土日） > 祝日（それ以外の日）> 月-木
    ※ 金曜日が祝日の場合は金曜日として扱い、その前日（木曜日）は祝前日として扱う
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    weekday = date_obj.weekday()  # 0=月, 6=日
    
    # 祝日の前日かどうかをチェック（祝前日は常に優先）
    if is_day_before_holiday(date_obj):
        return 'day_before_holiday'
    
    # 曜日判定（金曜日・土曜日・日曜日は曜日として扱う）
    if weekday == 4:  # 金
        return 'friday'
    elif weekday == 5:  # 土
        return 'saturday'
    elif weekday == 6:  # 日
        return 'sunday'
    
    # 祝日判定（月-木で祝日の場合のみ祝日として扱う）
    if is_holiday(date_obj):
        return 'holiday'
    
    # それ以外は月-木
    return 'mon_thu'

def get_store_data_file(store_code):
    """店舗ごとのデータファイルパスを取得"""
    os.makedirs(SHIFT_DATA_DIR, exist_ok=True)
    return os.path.join(SHIFT_DATA_DIR, f'{store_code}_data.json')

def build_shift_change_map(time_slots):
    """時間帯の並び順に基づいて変更可能先を作成"""
    change_map = {}
    for index, slot in enumerate(time_slots):
        change_map[slot] = time_slots[index + 1:]
    return change_map

def get_covered_slots(time_slots):
    """指定された時間帯（単一または複数）をそのまま返す"""
    if isinstance(time_slots, str):
        return [time_slots]

    # 入力順を保持して重複を除外
    unique_slots = []
    seen = set()
    for slot in time_slots:
        if slot not in seen:
            seen.add(slot)
            unique_slots.append(slot)

    return unique_slots

def get_default_time_slots():
    """デフォルトの時間帯を返す"""
    return ['10-15', '17-23', '18-23', '19-23']

def get_default_shift_settings():
    """デフォルトのシフト設定を返す"""
    # 共通の基本設定
    base_settings = {
        '10-15': {'社員': 1, 'アルバイト': 1},
        '17-23': {'社員': 1, 'アルバイト': 0},
        '18-23': {'社員': 1, 'アルバイト': 1},
        '19-23': {'社員': 1, 'アルバイト': 2}
    }
    
    return {
        'mode': 'weekday_weekend',  # 'weekday_weekend' または 'daily'
        'weekday_weekend': {
            'weekday': {  # 日〜木
                '10-15': {'社員': 1, 'アルバイト': 1},
                '17-23': {'社員': 1, 'アルバイト': 0},
                '18-23': {'社員': 1, 'アルバイト': 1},
                '19-23': {'社員': 1, 'アルバイト': 2}
            },
            'weekend': {  # 金土祝前日
                '10-15': {'社員': 1, 'アルバイト': 1},
                '17-23': {'社員': 1, 'アルバイト': 1},
                '18-23': {'社員': 1, 'アルバイト': 2},
                '19-23': {'社員': 1, 'アルバイト': 3}
            }
        },
        'daily': {  # 曜日ごと：0=日, 1=月, ..., 6=土
            0:  base_settings.copy(),  # 日曜日
            1:  base_settings.copy(),  # 月曜日
            2:  base_settings.copy(),  # 火曜日
            3:  base_settings.copy(),  # 水曜日
            4:  base_settings.copy(),  # 木曜日
            5:  {'10-15': {'社員': 1, 'アルバイト': 1}, '17-23': {'社員': 1, 'アルバイト': 1}, '18-23': {'社員': 1, 'アルバイト': 2}, '19-23': {'社員': 1, 'アルバイト': 3}},  # 金曜日
            6:  {'10-15': {'社員': 1, 'アルバイト': 1}, '17-23': {'社員': 1, 'アルバイト': 1}, '18-23': {'社員': 1, 'アルバイト': 2}, '19-23': {'社員': 1, 'アルバイト': 3}}   # 土曜日
        }
    }

def sort_staff_types(types):
    """スタッフ種別を表示順に並べ替える"""
    priority = {'社員': 0, 'アルバイト': 1}
    return sorted(types, key=lambda t: (priority.get(t, 2), t))

def get_staff_types(data, settings=None):
    """スタッフ種別リストを取得（登録スタッフ優先）"""
    types = set()
    for info in data.get('staff', {}).values():
        staff_type = str(info.get('type', '')).strip()
        if staff_type:
            types.add(staff_type)

    if not types and settings:
        for day_type in ['weekday', 'weekend']:
            for slot_settings in settings.get(day_type, {}).values():
                if isinstance(slot_settings, dict):
                    for key in slot_settings.keys():
                        if key == 'staff':
                            types.add('社員')
                        elif key == 'parttime':
                            types.add('アルバイト')
                        else:
                            types.add(key)

    if not types:
        types.update(['社員', 'アルバイト'])

    return sort_staff_types(types)

def normalize_shift_settings(settings, time_slots, staff_types):
    """シフト設定を正規化（新しいデータ構造に対応）"""
    # 古い形式のデータを新形式に変換
    if isinstance(settings, dict) and 'mode' not in settings:
        # 古い形式: {'weekday': {...}, 'weekend': {...}}
        settings = {
            'mode': 'weekday_weekend',
            'weekday_weekend': settings,
            'daily': {i: {} for i in range(7)}
        }
    
    mode = settings.get('mode', 'weekday_weekend')
    
    if mode == 'weekday_weekend_with_holidays':
        # 祝日別モード（日曜日を独立）
        normalized = {'sunday': {}, 'mon_thu': {}, 'friday': {}, 'saturday': {}, 'holiday': {}, 'day_before_holiday': {}}
        weekday_weekend_extended = settings.get('weekday_weekend_with_holidays', {})
        
        for day_type in ['sunday', 'mon_thu', 'friday', 'saturday', 'holiday', 'day_before_holiday']:
            day_settings = weekday_weekend_extended.get(day_type, {}) if isinstance(weekday_weekend_extended, dict) else {}
            for slot in time_slots:
                raw_settings = day_settings.get(slot, {}) if isinstance(day_settings, dict) else {}
                slot_settings = {}

                if isinstance(raw_settings, dict):
                    if 'staff' in raw_settings:
                        slot_settings['社員'] = raw_settings.get('staff', 0)
                    if 'parttime' in raw_settings:
                        slot_settings['アルバイト'] = raw_settings.get('parttime', 0)

                    for key, value in raw_settings.items():
                        if key in ['staff', 'parttime']:
                            continue
                        slot_settings[key] = value

                fallback_parttime = slot_settings.get('アルバイト', 0)
                for staff_type in staff_types:
                    if staff_type not in slot_settings:
                        if staff_type != '社員' and fallback_parttime:
                            slot_settings[staff_type] = fallback_parttime
                        else:
                            slot_settings[staff_type] = 0

                normalized[day_type][slot] = slot_settings
    elif mode == 'weekday_weekend':
        # 平日・週末モード
        normalized = {'weekday': {}, 'weekend': {}}
        weekday_weekend = settings.get('weekday_weekend', {})
        
        for day_type in ['weekday', 'weekend']:
            day_settings = weekday_weekend.get(day_type, {}) if isinstance(weekday_weekend, dict) else {}
            for slot in time_slots:
                raw_settings = day_settings.get(slot, {}) if isinstance(day_settings, dict) else {}
                slot_settings = {}

                if isinstance(raw_settings, dict):
                    if 'staff' in raw_settings:
                        slot_settings['社員'] = raw_settings.get('staff', 0)
                    if 'parttime' in raw_settings:
                        slot_settings['アルバイト'] = raw_settings.get('parttime', 0)

                    for key, value in raw_settings.items():
                        if key in ['staff', 'parttime']:
                            continue
                        slot_settings[key] = value

                fallback_parttime = slot_settings.get('アルバイト', 0)
                for staff_type in staff_types:
                    if staff_type not in slot_settings:
                        if staff_type != '社員' and fallback_parttime:
                            slot_settings[staff_type] = fallback_parttime
                        else:
                            slot_settings[staff_type] = 0

                normalized[day_type][slot] = slot_settings
    else:
        # 曜日ごとモード
        normalized = {i: {} for i in range(7)}
        daily = settings.get('daily', {})
        
        for day_of_week in range(7):
            # JSONから来たキーは文字列なので、文字列キーでアクセス
            day_key_str = str(day_of_week)
            day_settings = daily.get(day_key_str, {}) if isinstance(daily, dict) else {}
            for slot in time_slots:
                raw_settings = day_settings.get(slot, {}) if isinstance(day_settings, dict) else {}
                slot_settings = {}

                if isinstance(raw_settings, dict):
                    if 'staff' in raw_settings:
                        slot_settings['社員'] = raw_settings.get('staff', 0)
                    if 'parttime' in raw_settings:
                        slot_settings['アルバイト'] = raw_settings.get('parttime', 0)

                    for key, value in raw_settings.items():
                        if key in ['staff', 'parttime']:
                            continue
                        slot_settings[key] = value

                fallback_parttime = slot_settings.get('アルバイト', 0)
                for staff_type in staff_types:
                    if staff_type not in slot_settings:
                        if staff_type != '社員' and fallback_parttime:
                            slot_settings[staff_type] = fallback_parttime
                        else:
                            slot_settings[staff_type] = 0

                normalized[day_of_week][slot] = slot_settings
    
    return normalized

def load_data(store_code=None):
    """データを読み込み"""
    if store_code is None:
        store_code = session.get('store_code', 'default')
    
    print(f"[DEBUG load_data] セッション内の store_code: {session.get('store_code')}, 使用する store_code: {store_code}")
    
    data_file = get_store_data_file(store_code)
    print(f"[DEBUG load_data] データファイルパス: {data_file}")
    print(f"[DEBUG load_data] ファイル存在確認: {os.path.exists(data_file)}")
    
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"[DEBUG load_data] ✅ ファイルから読み込み。スタッフ数: {len(data.get('staff', {}))}")
                print(f"[DEBUG load_data] 登録済みスタッフ: {list(data.get('staff', {}).keys())}")
        except Exception as e:
            print(f"[ERROR load_data] ❌ ファイル読み込みエラー: {str(e)}")
            print(f"[ERROR load_data] ファイルパス: {data_file}")
            raise
        # 旧データとの互換性のため、staffがリストの場合は辞書に変換
        if isinstance(data.get('staff'), list):
            staff_dict = {}
            for name in data['staff']:
                staff_dict[name] = {'type': 'アルバイト'}  # デフォルトはアルバイト
            data['staff'] = staff_dict
        # shift_settingsがない場合はデフォルトを設定
        if 'shift_settings' not in data:
            data['shift_settings'] = get_default_shift_settings()
        # time_slotsがない場合はデフォルトを設定
        if 'time_slots' not in data:
            data['time_slots'] = get_default_time_slots()
        # custom_shiftsがない場合は初期化（自由入力シフト用）
        if 'custom_shifts' not in data:
            data['custom_shifts'] = {}
        # 生成後の手作業上書きシフトがない場合は初期化
        if 'manual_generated_shifts' not in data:
            data['manual_generated_shifts'] = {}
        # 生成シフトの一時保存データがない場合は初期化
        if 'generated_shift_drafts' not in data:
            data['generated_shift_drafts'] = {}
        # 確定済み生成シフトがない場合は初期化
        if 'confirmed_generated_shifts' not in data:
            data['confirmed_generated_shifts'] = {}
        
        # 古い形式のshift_settingsをチェック（mode属性がない場合）
        shift_settings = data.get('shift_settings', {})
        if isinstance(shift_settings, dict) and 'mode' not in shift_settings and ('weekday' in shift_settings or 'weekend' in shift_settings):
            # 古い形式：平日・週末パターンのみ
            shift_settings = {
                'mode': 'weekday_weekend',
                'weekday_weekend': shift_settings,
                'daily': {i: {} for i in range(7)}
            }
            data['shift_settings'] = shift_settings
        
        # 種別ごとの設定に正規化（ただしmodeはそのまま保持）
        staff_types = get_staff_types(data, data.get('shift_settings'))
        raw_settings = data.get('shift_settings', get_default_shift_settings())
        normalized_settings = normalize_shift_settings(
            raw_settings,
            data.get('time_slots', get_default_time_slots()),
            staff_types
        )
        
        # 正規化後もmodeを保持（APIレスポンスで必要）
        data['shift_settings'] = raw_settings  # 元のデータ構造を保持
        # admin_passwordがない場合はデフォルトを設定
        if 'admin_password' not in data:
            data['admin_password'] = ADMIN_PASSWORD
        return data
    return {
        'staff': {},  # スタッフ情報の辞書 {name: {type: '社員' or 'アルバイト' or 任意}}
        'shifts': {},  # {date: {staff: [time_slots]}}
        'custom_shifts': {},  # {date: {staff: [custom_time_slots]}}
        'manual_generated_shifts': {},  # {date: {staff: [time_slots]}} 生成表の手作業上書き
        'generated_shift_drafts': {},  # {YYYY-MM: {'saved_at': str, 'shifts': {date: {staff: [time_slots]}}}}
        'confirmed_generated_shifts': {},  # {YYYY-MM: {'confirmed_at': str, 'shifts': {date: {staff: [time_slots]}}}}
        'requirements': {},  # {date: {time_slot: count}}
        'shift_settings': get_default_shift_settings(),  # シフト詳細設定
        'time_slots': get_default_time_slots(),  # 時間帯リスト
        'admin_password': ADMIN_PASSWORD  # 管理者パスワード（店舗ごと）
    }

def replace_month_shifts(base_shifts, year, month, month_shifts):
    """指定月のシフトを丸ごと置き換える"""
    for date_str in list(base_shifts.keys()):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        if date_obj.year == year and date_obj.month == month:
            del base_shifts[date_str]

    for date_str, staff_map in month_shifts.items():
        base_shifts[date_str] = {
            staff_name: list(slots)
            for staff_name, slots in staff_map.items()
        }

def build_final_generated_shifts(data, year=None, month=None, force_regenerate=False):
    """最適化結果に保存済みシフトと手作業上書きを反映した最終生成シフトを返す"""
    optimized_shifts = optimize_shifts(data)

    if year is not None and month is not None and not force_regenerate:
        month_key = f"{year:04d}-{month:02d}"
        confirmed_entry = data.get('confirmed_generated_shifts', {}).get(month_key, {})
        draft_entry = data.get('generated_shift_drafts', {}).get(month_key, {})

        confirmed_shifts = confirmed_entry.get('shifts') if isinstance(confirmed_entry, dict) else None
        draft_shifts = draft_entry.get('shifts') if isinstance(draft_entry, dict) else None

        # 優先順位: 確定済み > 一時保存
        if confirmed_shifts:
            replace_month_shifts(optimized_shifts, year, month, confirmed_shifts)
        elif draft_shifts:
            replace_month_shifts(optimized_shifts, year, month, draft_shifts)

    manual_generated_shifts = data.get('manual_generated_shifts', {})

    for date_str, staff_map in manual_generated_shifts.items():
        if date_str not in optimized_shifts:
            optimized_shifts[date_str] = {}

        for staff_name, manual_slots in staff_map.items():
            if manual_slots:
                optimized_shifts[date_str][staff_name] = manual_slots
            else:
                # 空指定は「その日の生成シフトなし」として扱う
                if staff_name in optimized_shifts[date_str]:
                    del optimized_shifts[date_str][staff_name]

        if not optimized_shifts[date_str]:
            del optimized_shifts[date_str]

    return optimized_shifts

def extract_month_generated_shifts(shifts_by_date, year, month):
    """指定月の生成シフトのみを抽出する"""
    result = {}
    for date_str, staff_map in shifts_by_date.items():
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        if date_obj.year == year and date_obj.month == month:
            # 参照共有を避けるために浅いコピーを作成
            result[date_str] = {
                staff_name: list(slots)
                for staff_name, slots in staff_map.items()
            }
    return result

def replace_month_manual_generated_shifts(data, year, month, month_shifts):
    """指定月の手作業上書きシフトを丸ごと置き換える"""
    if 'manual_generated_shifts' not in data:
        data['manual_generated_shifts'] = {}

    # 対象月の既存上書きを削除
    for date_str in list(data['manual_generated_shifts'].keys()):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        if date_obj.year == year and date_obj.month == month:
            del data['manual_generated_shifts'][date_str]

    # 新しい確定内容を反映
    for date_str, staff_map in month_shifts.items():
        data['manual_generated_shifts'][date_str] = {
            staff_name: list(slots)
            for staff_name, slots in staff_map.items()
        }

def save_data(data, store_code=None):
    """データを保存"""
    if store_code is None:
        store_code = session.get('store_code', 'default')
    
    data_file = get_store_data_file(store_code)
    try:
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG save_data] ✅ {store_code} のデータを保存しました: {data_file}")
    except Exception as e:
        print(f"[ERROR save_data] ❌ {store_code} のデータ保存に失敗しました: {str(e)}")
        print(f"[ERROR save_data] ファイルパス: {data_file}")
        raise

@app.route('/')
def index():
    """トップページ（ログイン状態確認）"""
    if 'role' in session:
        return render_template('index.html', role=session['role'])
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET'])
def login_page():
    """ログイン画面"""
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    """ログイン処理"""
    data_request = request.json
    password = data_request.get('password', '')
    store_code = data_request.get('store_code', '').strip()
    role = data_request.get('role', 'user')
    staff_name = data_request.get('staff_name', '').strip()  # スタッフ名を取得
    
    print(f"[DEBUG api_login] ログイン試行 - 店舗: {store_code}, ロール: {role}")
    
    if not store_code:
        print(f"[ERROR api_login] 店舗コードが入力されていません")
        return jsonify({'success': False, 'error': '店舗コードを入力してください'}), 400
    
    # スタッフロールの場合、スタッフ名を確認
    if role == 'user' and not staff_name:
        print(f"[ERROR api_login] スタッフロール: スタッフ名が入力されていません")
        return jsonify({'success': False, 'error': 'スタッフ名を入力してください'}), 400
    
    # 店舗データを読み込み（セッション設定前なので直接指定）
    data_file = get_store_data_file(store_code)
    print(f"[DEBUG api_login] データファイルパス: {data_file}")
    print(f"[DEBUG api_login] ファイル存在: {os.path.exists(data_file)}")
    
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                store_data = json.load(f)
            store_password = store_data.get('admin_password', ADMIN_PASSWORD)
            print(f"[DEBUG api_login] ✅ 既存店舗データを読み込みました")
        except Exception as e:
            print(f"[ERROR api_login] ❌ 店舗データの読み込みに失敗: {str(e)}")
            return jsonify({'success': False, 'error': '店舗データの読み込みに失敗しました: ' + str(e)}), 500
    else:
        # 新規店舗の場合はデフォルトパスワード（環境変数を優先）
        print(f"[DEBUG api_login] 新規店舗です（ファイルが存在しません）")
        store_password = get_default_password_for_store(store_code)
    
    # 管理者パスワード確認
    if role == 'admin' and password != store_password:
        print(f"[ERROR api_login] 管理者: パスワードが違います")
        return jsonify({'success': False, 'error': 'パスワードが違います'}), 401
    
    # セッションに情報を保存
    session['role'] = role
    session['store_code'] = store_code
    if role == 'user':
        session['staff_name'] = staff_name  # スタッフロールの場合、スタッフ名を保存
    session.permanent = True
    
    print(f"[DEBUG api_login] ✅ セッション設定完了 - store_code: {store_code}, role: {role}")
    
    # 新規店舗の場合、ログイン時に店舗ファイルを自動作成
    if not os.path.exists(data_file):
        try:
            print(f"[DEBUG api_login] 新規店舗 '{store_code}' の初期ファイルを作成します")
            initial_data = {
                'staff': {},
                'shifts': {},
                'requirements': {},
                'shift_settings': get_default_shift_settings(),
                'time_slots': get_default_time_slots(),
                'admin_password': store_password  # 環境変数またはデフォルトパスワードを使用
            }
            dir_path = os.path.dirname(data_file)
            print(f"[DEBUG api_login] ディレクトリ作成: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
            
            print(f"[DEBUG api_login] ファイル作成開始: {data_file}")
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG api_login] ✅ 新規店舗ファイル作成完了: {data_file}")
            
            # ファイルが本当に作成されたか確認
            if os.path.exists(data_file):
                print(f"[DEBUG api_login] ✅ ファイルの存在確認: {data_file} (サイズ: {os.path.getsize(data_file)} bytes)")
            else:
                print(f"[ERROR api_login] ❌ ファイルが見当たりません: {data_file}")
        except Exception as e:
            print(f"[ERROR api_login] ❌ 新規店舗ファイル作成に失敗しました: {str(e)}")
            print(f"[ERROR api_login] ファイルパス: {data_file}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': '店舗データの作成に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True, 'role': role, 'store_code': store_code})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """ログアウト処理"""
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """認証状態確認"""
    if 'role' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({
        'role': session['role'],
        'store_code': session.get('store_code', 'default'),
        'success': True
    })

@app.route('/api/current-staff', methods=['GET'])
def get_current_staff():
    """ログイン中のスタッフ情報を取得"""
    if 'role' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # ユーザーロールの場合のみ、スタッフ名を返す
    if session.get('role') != 'user':
        return jsonify({'error': 'ユーザーロードのみアクセス可能'}), 403
    
    data = load_data()
    staff_name = session.get('staff_name')
    
    # セッションにスタッフ名がない場合は、最初のスタッフを返す（デフォルト）
    if not staff_name:
        # 本来はログイン時にスタッフ名を保存するべき
        # ここでは、'staff_name'がセッションに含まれていない場合は、
        # ユーザーが特定のスタッフとして登録されていないということ
        return jsonify({
            'success': False,
            'staff_name': None,
            'staff_type': None
        }), 200
    
    staff_info = data['staff'].get(staff_name, {})
    return jsonify({
        'success': True,
        'staff_name': staff_name,
        'staff_type': staff_info.get('type', 'アルバイト')
    })

def require_admin(f):
    """管理者専用エンドポイント用デコレータ"""
    def decorated(*args, **kwargs):
        print(f"[DEBUG require_admin] セッション情報: {dict(session)}")
        print(f"[DEBUG require_admin] role: {session.get('role')}")
        if session.get('role') != 'admin':
            print(f"[ERROR require_admin] 管理者権限がありません")
            return jsonify({'error': '管理者のみアクセス可能です'}), 403
        print(f"[DEBUG require_admin] 管理者権限OK")
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/api/store-data/export', methods=['GET'])
@require_admin
def export_store_data():
    """現在ログイン中の店舗データをエクスポート（管理者のみ）"""
    data = load_data()
    return jsonify({
        'success': True,
        'store_code': session.get('store_code', 'default'),
        'data': data
    })

@app.route('/api/store-data/import', methods=['POST'])
@require_admin
def import_store_data():
    """現在ログイン中の店舗データをインポート（管理者のみ）"""
    payload = request.json or {}
    imported_data = payload.get('data')

    if not isinstance(imported_data, dict):
        return jsonify({'error': 'インポートデータが不正です'}), 400

    required_keys = ['staff', 'shifts', 'requirements']
    missing_keys = [key for key in required_keys if key not in imported_data]
    if missing_keys:
        return jsonify({'error': f'必須キーが不足しています: {", ".join(missing_keys)}'}), 400

    try:
        # 現在のデータを読み込んで、admin_passwordを保持
        current_data = load_data()
        current_password = current_data.get('admin_password', ADMIN_PASSWORD)
        
        # インポートデータを保存
        save_data(imported_data)
        
        # admin_passwordを元に戻す
        imported_data['admin_password'] = current_password
        save_data(imported_data)
        
        print(f"[DEBUG import_store_data] ✅ インポート完了。admin_passwordは保持しました。")
    except Exception as e:
        print(f"[ERROR import_store_data] インポート保存に失敗: {str(e)}")
        return jsonify({'error': 'インポート保存に失敗しました: ' + str(e)}), 500

    return jsonify({
        'success': True,
        'store_code': session.get('store_code', 'default')
    })

@app.route('/api/staff', methods=['GET'])
def get_staff():
    """スタッフ一覧を取得"""
    data = load_data()
    return jsonify(data['staff'])

@app.route('/api/staff', methods=['POST'])
@require_admin
def add_staff():
    """スタッフを追加（管理者のみ）"""
    staff_name = request.json.get('name', '').strip()
    staff_type = request.json.get('type', 'アルバイト').strip()
    priority = request.json.get('priority')  # 優先度を取得
    
    print(f"[DEBUG] スタッフ追加リクエスト - 名前: {repr(staff_name)}, 種別: {repr(staff_type)}, 優先度: {priority}")
    
    if not staff_name:
        return jsonify({'error': 'スタッフ名を入力してください'}), 400
    
    if not staff_type:
        return jsonify({'error': '種別を入力してください'}), 400
    
    # スレッドセーフなロック処理
    with staff_lock:
        print(f"[DEBUG] ロック取得 - スタッフ '{staff_name}' の追加処理開始")
        
        data = load_data()
        print(f"[DEBUG] 現在登録されているスタッフ: {list(data['staff'].keys())}")
        print(f"[DEBUG] スタッフ '{staff_name}' は登録済みか？ {staff_name in data['staff']}")
        
        if staff_name in data['staff']:
            print(f"[DEBUG] スタッフ '{staff_name}' は既に登録されています")
            return jsonify({'error': 'このスタッフは既に登録されています'}), 400
        
        # 優先度情報を含める
        staff_info = {'type': staff_type}
        if priority is not None:
            staff_info['priority'] = priority
        
        data['staff'][staff_name] = staff_info
        try:
            save_data(data)
            print(f"[DEBUG] ✅ スタッフ '{staff_name}' を追加しました")
            print(f"[DEBUG] ロック解放 - スタッフ '{staff_name}' の追加処理完了")
        except Exception as e:
            print(f"[ERROR] ❌ スタッフ '{staff_name}' の保存に失敗しました: {str(e)}")
            return jsonify({'error': 'スタッフの保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True, 'staff': data['staff']})

@app.route('/api/staff/<staff_name>', methods=['DELETE'])
@require_admin
def delete_staff(staff_name):
    """スタッフを削除（管理者のみ）"""
    data = load_data()
    
    if staff_name not in data['staff']:
        return jsonify({'error': 'スタッフが見つかりません'}), 404
    
    del data['staff'][staff_name]
    
    # シフトデータからも削除
    for date in list(data['shifts'].keys()):
        if staff_name in data['shifts'][date]:
            del data['shifts'][date][staff_name]
        if not data['shifts'][date]:
            del data['shifts'][date]
    
    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] スタッフ '{staff_name}' の削除保存に失敗: {str(e)}")
        return jsonify({'error': 'スタッフの削除保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True, 'staff': data['staff']})

@app.route('/api/shifts/<year>/<month>', methods=['GET'])
def get_shifts(year, month):
    """指定月のシフト希望を取得"""
    data = load_data()
    year = int(year)
    month = int(month)
    
    # 月の日数を取得
    days_in_month = calendar.monthrange(year, month)[1]
    
    # 月のシフトデータを整形
    month_shifts = {}
    month_custom_shifts = {}
    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        month_shifts[date_str] = data['shifts'].get(date_str, {})
        month_custom_shifts[date_str] = data.get('custom_shifts', {}).get(date_str, {})
    
    return jsonify({
        'shifts': month_shifts,
        'custom_shifts': month_custom_shifts,
        'staff': data['staff'],
        'time_slots': data.get('time_slots', get_default_time_slots()),
        'change_map': build_shift_change_map(data.get('time_slots', get_default_time_slots())),
        'days_in_month': days_in_month
    })

@app.route('/api/shifts', methods=['POST'])
def update_shift():
    """シフト希望を更新"""
    date = request.json.get('date')
    staff = request.json.get('staff')
    time_slots = request.json.get('time_slots', [])
    custom_time_slots = request.json.get('custom_time_slots', [])
    
    if not date or not staff:
        return jsonify({'error': 'パラメータが不足しています'}), 400
    
    data = load_data()
    
    if staff not in data['staff']:
        return jsonify({'error': 'スタッフが登録されていません'}), 400
    
    if date not in data['shifts']:
        data['shifts'][date] = {}
    if 'custom_shifts' not in data:
        data['custom_shifts'] = {}
    if date not in data['custom_shifts']:
        data['custom_shifts'][date] = {}
    
    if time_slots:
        data['shifts'][date][staff] = time_slots
    else:
        # 空の場合は削除
        if staff in data['shifts'][date]:
            del data['shifts'][date][staff]
        if not data['shifts'][date]:
            del data['shifts'][date]

    if custom_time_slots:
        data['custom_shifts'][date][staff] = custom_time_slots
    else:
        if date in data['custom_shifts'] and staff in data['custom_shifts'][date]:
            del data['custom_shifts'][date][staff]
        if date in data['custom_shifts'] and not data['custom_shifts'][date]:
            del data['custom_shifts'][date]
    
    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] シフト情報の保存に失敗: {str(e)}")
        return jsonify({'error': 'シフト情報の保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True})

@app.route('/api/update-shift', methods=['POST'])
@require_admin
def update_shift_inline():
    """生成シフト表の手作業上書きを更新（管理者のみ）"""
    staff_name = request.json.get('staff_name')
    date = request.json.get('date')
    shifts = request.json.get('shifts', [])
    
    if not date or not staff_name:
        return jsonify({'error': 'パラメータが不足しています', 'success': False}), 400
    
    data = load_data()
    
    if staff_name not in data['staff']:
        return jsonify({'error': 'スタッフが登録されていません', 'success': False}), 400

    if 'manual_generated_shifts' not in data:
        data['manual_generated_shifts'] = {}

    if date not in data['manual_generated_shifts']:
        data['manual_generated_shifts'][date] = {}

    # 空配列も有効な上書き値として保存（生成結果を空にしたいケース）
    data['manual_generated_shifts'][date][staff_name] = shifts
    
    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] シフト更新の保存に失敗: {str(e)}")
        return jsonify({'error': 'シフト更新の保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True})

@app.route('/api/update-custom-shift', methods=['POST'])
@require_admin
def update_custom_shift():
    """自由入力シフトを更新（管理者のみ）"""
    staff_name = request.json.get('staff_name')
    date = request.json.get('date')
    custom_shifts = request.json.get('custom_shifts', [])
    
    if not date or not staff_name:
        return jsonify({'error': 'パラメータが不足しています', 'success': False}), 400
    
    data = load_data()
    
    # custom_shiftsキーが存在しない場合は初期化
    if 'custom_shifts' not in data:
        data['custom_shifts'] = {}
    
    if custom_shifts:
        # 日付キーが存在しない場合は初期化
        if date not in data['custom_shifts']:
            data['custom_shifts'][date] = {}
        data['custom_shifts'][date][staff_name] = custom_shifts
    else:
        # 空の場合は削除
        if date in data['custom_shifts'] and staff_name in data['custom_shifts'][date]:
            del data['custom_shifts'][date][staff_name]
            if not data['custom_shifts'][date]:
                del data['custom_shifts'][date]
    
    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] カスタムシフト更新の保存に失敗: {str(e)}")
        return jsonify({'error': 'カスタムシフト更新の保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True})

@app.route('/api/delete-generated-shift', methods=['POST'])
@require_admin
def delete_generated_shift():
    """生成シフト（選択シフト）を削除し、カスタムシフトは保持（管理者のみ）"""
    staff_name = request.json.get('staff_name')
    date = request.json.get('date')
    
    if not date or not staff_name:
        return jsonify({'error': 'パラメータが不足しています', 'success': False}), 400
    
    data = load_data()
    
    # カスタムシフトを事前に保存（削除対象ではない）
    preserved_custom_shifts = None
    if 'custom_shifts' in data and date in data['custom_shifts'] and staff_name in data['custom_shifts'][date]:
        preserved_custom_shifts = data['custom_shifts'][date][staff_name].copy()
    
    # 生成シフト（shifts）から削除
    if date in data['shifts'] and staff_name in data['shifts'][date]:
        del data['shifts'][date][staff_name]
        if not data['shifts'][date]:
            del data['shifts'][date]

    # 手作業上書きシフトからも削除
    if date in data.get('manual_generated_shifts', {}) and staff_name in data['manual_generated_shifts'][date]:
        del data['manual_generated_shifts'][date][staff_name]
        if not data['manual_generated_shifts'][date]:
            del data['manual_generated_shifts'][date]
    
    # カスタムシフトが保存されていたら復元（実装上は常に保持すること）
    # ただし、上記で削除しないので実装上の余剰処理
    
    try:
        save_data(data)
        print(f"[INFO] 生成シフト削除完了: staff={staff_name}, date={date}, custom_shifts保持={preserved_custom_shifts is not None}")
    except Exception as e:
        print(f"[ERROR] 生成シフト削除の保存に失敗: {str(e)}")
        return jsonify({'error': '生成シフト削除の保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True})

@app.route('/api/requirements/<year>/<month>', methods=['GET'])
def get_requirements(year, month):
    """指定月の必要人数を取得"""
    data = load_data()
    year = int(year)
    month = int(month)
    
    # 月の日数を取得
    days_in_month = calendar.monthrange(year, month)[1]
    
    # 月の必要人数データを整形
    month_requirements = {}
    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        month_requirements[date_str] = data['requirements'].get(date_str, {})
    
    return jsonify({
        'requirements': month_requirements,
        'time_slots': data.get('time_slots', get_default_time_slots()),
        'days_in_month': days_in_month
    })

@app.route('/api/requirements', methods=['POST'])
@require_admin
def update_requirement():
    """必要人数を更新（管理者のみ）"""
    date = request.json.get('date')
    time_slot = request.json.get('time_slot')
    count = request.json.get('count')
    
    if not date or not time_slot:
        return jsonify({'error': 'パラメータが不足しています'}), 400
    
    data = load_data()
    
    if date not in data['requirements']:
        data['requirements'][date] = {}
    
    if count is not None and count != '':
        try:
            data['requirements'][date][time_slot] = int(count)
        except ValueError:
            return jsonify({'error': '数値を入力してください'}), 400
    else:
        # 空の場合は削除
        if time_slot in data['requirements'][date]:
            del data['requirements'][date][time_slot]
        if not data['requirements'][date]:
            del data['requirements'][date]
    
    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] 必要人数の保存に失敗: {str(e)}")
        return jsonify({'error': '必要人数の保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True})

@app.route('/api/shift-settings', methods=['GET'])
@require_admin
def get_shift_settings():
    """シフト詳細設定を取得（管理者のみ）"""
    data = load_data()
    time_slots = data.get('time_slots', get_default_time_slots())
    staff_types = get_staff_types(data, data.get('shift_settings'))
    raw_settings = data.get('shift_settings', get_default_shift_settings())
    settings = normalize_shift_settings(raw_settings, time_slots, staff_types)
    
    # モード情報を追加
    mode = raw_settings.get('mode', 'weekday_weekend') if isinstance(raw_settings, dict) else 'weekday_weekend'
    
    return jsonify({
        'success': True,
        'settings': settings,
        'time_slots': time_slots,
        'staff_types': staff_types,
        'mode': mode,
        'raw_settings': raw_settings
    })

@app.route('/api/shift-settings', methods=['POST'])
@require_admin
def update_shift_settings():
    """シフト詳細設定を更新（管理者のみ）"""
    raw_settings = request.json.get('settings')
    mode = request.json.get('mode', 'weekday_weekend')
    
    if not raw_settings:
        return jsonify({'error': '設定データが不足しています'}), 400
    
    data = load_data()
    time_slots = data.get('time_slots', get_default_time_slots())
    staff_types = get_staff_types(data, raw_settings)
    
    # 既存の設定から現在のモード以外のデータを保持
    existing_settings = data.get('shift_settings', {})
    if not isinstance(existing_settings, dict):
        existing_settings = {}
    
    # 元の設定構造を保存（mode + weekday_weekend or daily or weekday_weekend_with_holidays）
    # 現在のモードのデータのみを更新し、他のモードのデータは保持する
    updated_settings = {
        'mode': mode,
        'weekday_weekend': existing_settings.get('weekday_weekend', get_default_shift_settings().get('weekday_weekend', {})),
        'daily': existing_settings.get('daily', get_default_shift_settings().get('daily', {})),
        'weekday_weekend_with_holidays': existing_settings.get('weekday_weekend_with_holidays', {})
    }
    
    # 現在のモードのデータのみを上書き
    if mode == 'weekday_weekend_with_holidays':
        updated_settings['weekday_weekend_with_holidays'] = raw_settings.get('weekday_weekend_with_holidays', {})
    elif mode == 'daily':
        updated_settings['daily'] = raw_settings.get('daily', {})
    else:  # weekday_weekend
        updated_settings['weekday_weekend'] = raw_settings.get('weekday_weekend', {})
    
    data['shift_settings'] = updated_settings
    save_data(data)
    
    return jsonify({'success': True})

@app.route('/api/time-slots', methods=['GET'])
@require_admin
def get_time_slots():
    """時間帯リストを取得（管理者のみ）"""
    data = load_data()
    time_slots = data.get('time_slots', get_default_time_slots())
    return jsonify({'success': True, 'time_slots': time_slots})

@app.route('/api/time-slots', methods=['POST'])
@require_admin
def update_time_slots():
    """時間帯リストを更新（管理者のみ）"""
    time_slots = request.json.get('time_slots')
    
    if not time_slots or not isinstance(time_slots, list):
        return jsonify({'error': '時間帯データが不正です'}), 400
    
    data = load_data()
    
    # 古い時間帯データとの整合性を保つため、shift_settingsも更新
    old_slots = data.get('time_slots', [])
    staff_types = get_staff_types(data, data.get('shift_settings'))
    new_settings = normalize_shift_settings(
        data.get('shift_settings', get_default_shift_settings()),
        time_slots,
        staff_types
    )

    # 追加された時間帯にデフォルト値を入れる
    new_slots = [slot for slot in time_slots if slot not in old_slots]
    if new_slots:
        for day_type in ['weekday', 'weekend']:
            for slot in new_slots:
                slot_settings = new_settings.get(day_type, {}).get(slot, {})
                for staff_type in staff_types:
                    if staff_type in ['社員', 'アルバイト'] and slot_settings.get(staff_type, 0) == 0:
                        slot_settings[staff_type] = 1
    
    # 削除された時間帯の設定を削除
    for day_type in ['weekday', 'weekend']:
        slots_to_remove = [s for s in new_settings.get(day_type, {}).keys() if s not in time_slots]
        for slot in slots_to_remove:
            del new_settings[day_type][slot]
    
    data['time_slots'] = time_slots
    data['shift_settings'] = new_settings
    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] 時間帯の保存に失敗: {str(e)}")
        return jsonify({'error': '時間帯の保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True})

@app.route('/api/change-password', methods=['POST'])
@require_admin
def change_password():
    """管理者パスワードを変更（管理者のみ）"""
    print(f"[DEBUG change_password] セッション情報: {dict(session)}")
    print(f"[DEBUG change_password] role: {session.get('role')}")
    print(f"[DEBUG change_password] store_code: {session.get('store_code')}")
    current_password = request.json.get('current_password', '')
    new_password = request.json.get('new_password', '')
    
    print(f"[DEBUG change_password] リクエスト - current_password: {current_password[:2]}..., new_password: {new_password[:2]}...")
    
    if not new_password:
        return jsonify({'error': '新しいパスワードを入力してください'}), 400
    
    if len(new_password) < 4:
        return jsonify({'error': 'パスワードは4文字以上にしてください'}), 400
    
    data = load_data()
    print(f"[DEBUG change_password] データ読み込み完了")
    
    # 現在のパスワード確認
    current_stored_password = data.get('admin_password', ADMIN_PASSWORD)
    print(f"[DEBUG change_password] 現在保存されているパスワード: {current_stored_password[:2]}...")
    
    if current_password != current_stored_password:
        print(f"[ERROR change_password] パスワード不一致")
        return jsonify({'error': '現在のパスワードが違います'}), 401
    
    # 新しいパスワードを保存
    print(f"[DEBUG change_password] パスワード変更前: {data.get('admin_password', '')[:2]}...")
    data['admin_password'] = new_password
    print(f"[DEBUG change_password] パスワード変更後: {data.get('admin_password', '')[:2]}...")
    
    try:
        save_data(data)
        print(f"[DEBUG change_password] ✅ パスワード保存成功")
        
        # 保存後、実際にファイルから読み込んで確認
        store_code = session.get('store_code', 'default')
        data_file = get_store_data_file(store_code)
        with open(data_file, 'r', encoding='utf-8') as f:
            verify_data = json.load(f)
        print(f"[DEBUG change_password] 保存後の確認 - ファイルのパスワード: {verify_data.get('admin_password', '')[:2]}...")
    except Exception as e:
        print(f"[ERROR change_password] パスワード変更の保存に失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'パスワード変更の保存に失敗しました: ' + str(e)}), 500
    
    return jsonify({'success': True, 'message': 'パスワードを変更しました'})

@app.route('/api/generate', methods=['GET'])
@require_admin
def generate_shift():
    """シフト表を生成（表形式・最適化機能付き）（管理者のみ）"""
    data = load_data()
    
    # クエリパラメーターから年月を取得
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    force_regenerate = request.args.get('force_regenerate', default='0') == '1'
    
    # 日付を収集してソート（通常シフト + 自由入力シフト）
    dates = sorted(set(list(data['shifts'].keys()) + list(data.get('custom_shifts', {}).keys())))
    
    if not dates:
        return jsonify([])
    
    # 年月が指定されている場合、その月のみにフィルタリング
    if year is not None and month is not None:
        filtered_dates = []
        for date_str in dates:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            if date_obj.year == year and date_obj.month == month:
                filtered_dates.append(date_str)
        dates = filtered_dates
    
    if not dates:
        return jsonify([])
    
    # シフトを最適化し、手作業上書きを反映
    optimized_shifts = build_final_generated_shifts(
        data,
        year=year,
        month=month,
        force_regenerate=force_regenerate
    )
    
    # 月別にグループ化
    monthly_data = {}
    for date_str in dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        month_key = f"{date_obj.year}-{date_obj.month:02d}"
        if month_key not in monthly_data:
            monthly_data[month_key] = []
        monthly_data[month_key].append(date_str)
    
    result = []
    
    for month_key, month_dates in sorted(monthly_data.items()):
        # 月の情報
        first_date = datetime.strptime(month_dates[0], '%Y-%m-%d')
        month_info = {
            'month': f"{first_date.year}年{first_date.month}月",
            'dates': [],
            'staff_list': [],
            'shift_table': []
        }
        
        # 日付情報（日、曜日）
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        for date_str in month_dates:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            weekday_jp = weekday_names[date_obj.weekday()]
            
            # この日の充足状況をチェック
            is_insufficient = False
            time_slots = data.get('time_slots', get_default_time_slots())
            settings = data.get('shift_settings', get_default_shift_settings())
            staff_types = get_staff_types(data, settings)
            
            for time_slot in time_slots:
                required_by_type = {}
                assigned_by_type = {staff_type: 0 for staff_type in staff_types}
                
                for staff_type in staff_types:
                    required_by_type[staff_type] = get_required_staff(
                        date_str,
                        time_slot,
                        staff_type,
                        settings
                    )
                
                # 実際に入っている人数を計算（時間帯包含を考慮）
                shifts = optimized_shifts.get(date_str, {})
                for staff_name, slots in shifts.items():
                    covered = get_covered_slots(slots)
                    if time_slot in covered:
                        staff_info = data['staff'].get(staff_name, {})
                        staff_type = staff_info.get('type', 'アルバイト')
                        if staff_type in assigned_by_type:
                            assigned_by_type[staff_type] += 1
                
                # 不足をチェック
                for staff_type in staff_types:
                    if assigned_by_type[staff_type] < required_by_type[staff_type]:
                        is_insufficient = True
                        break
                
                if is_insufficient:
                    break
            
            month_info['dates'].append({
                'date': date_str,
                'day': date_obj.day,
                'weekday': weekday_jp,
                'insufficient': is_insufficient
            })
        
        # スタッフリストを取得（シフトに含まれるスタッフも含める）
        staff_set = set(data['staff'].keys())
        # シフトに含まれるスタッフを追加
        for date_str in month_dates:
            if date_str in optimized_shifts:
                staff_set.update(optimized_shifts[date_str].keys())
            if date_str in data.get('custom_shifts', {}):
                staff_set.update(data['custom_shifts'][date_str].keys())
        
        staff_list = sorted(staff_set)
        
        # 各スタッフのシフトを表形式に（最適化されたシフトを使用）
        for staff_name in staff_list:
            staff_info = data['staff'].get(staff_name, {})
            row = {
                'name': staff_name,
                'type': staff_info.get('type', 'アルバイト'),  # 未登録スタッフはアルバイト扱い
                'shifts': [],  # 選択シフト（詳細設定に従って生成）
                'input_shifts': [],  # 入力されたシフト希望（最適化前）
                'custom_shifts': []  # 自由入力シフト（手作業で管理）
            }
            
            for date_str in month_dates:
                time_slots = []
                if date_str in optimized_shifts and staff_name in optimized_shifts[date_str]:
                    time_slots = optimized_shifts[date_str][staff_name]
                row['shifts'].append(time_slots)
                
                # 入力されたシフト希望（最適化前）を取得
                input_slots = []
                if date_str in data['shifts'] and staff_name in data['shifts'][date_str]:
                    input_slots = data['shifts'][date_str][staff_name]
                row['input_shifts'].append(input_slots)
                
                # 自由入力シフトを抽出（時間帯リストに存在しない）
                custom_slots = []
                if date_str in data.get('custom_shifts', {}) and staff_name in data['custom_shifts'][date_str]:
                    custom_slots = data['custom_shifts'][date_str][staff_name]
                elif date_str in data['shifts'] and staff_name in data['shifts'][date_str]:
                    # 旧データ互換: custom_shifts導入前はshifts内の未定義時間帯を自由入力として扱う
                    all_slots = data['shifts'][date_str][staff_name]
                    time_slots_list = data.get('time_slots', get_default_time_slots())
                    custom_slots = [s for s in all_slots if s not in time_slots_list]
                row['custom_shifts'].append(custom_slots)
            
            month_info['staff_list'].append(row)
        
        result.append(month_info)
    
    return jsonify(result)

@app.route('/api/generated-shift/status', methods=['GET'])
@require_admin
def generated_shift_status():
    """指定月の生成シフト保存状態（下書き/確定）を返す（管理者のみ）"""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if year is None or month is None:
        return jsonify({'success': False, 'error': '年月が必要です'}), 400

    if month < 1 or month > 12:
        return jsonify({'success': False, 'error': '月の指定が不正です'}), 400

    data = load_data()
    month_key = f"{year:04d}-{month:02d}"

    draft_entry = data.get('generated_shift_drafts', {}).get(month_key, {})
    confirmed_entry = data.get('confirmed_generated_shifts', {}).get(month_key, {})

    has_draft = isinstance(draft_entry, dict) and bool(draft_entry.get('shifts'))
    has_confirmed = isinstance(confirmed_entry, dict) and bool(confirmed_entry.get('shifts'))

    return jsonify({
        'success': True,
        'month': month_key,
        'has_draft': has_draft,
        'draft_saved_at': draft_entry.get('saved_at') if isinstance(draft_entry, dict) else None,
        'has_confirmed': has_confirmed,
        'confirmed_at': confirmed_entry.get('confirmed_at') if isinstance(confirmed_entry, dict) else None
    })

@app.route('/api/generated-shift/temp-save', methods=['POST'])
@require_admin
def temp_save_generated_shift():
    """指定月の生成シフトを一時保存する（管理者のみ）"""
    year = request.json.get('year') if request.json else None
    month = request.json.get('month') if request.json else None

    try:
        year = int(year)
        month = int(month)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '年月が不正です'}), 400

    if month < 1 or month > 12:
        return jsonify({'success': False, 'error': '月の指定が不正です'}), 400

    data = load_data()
    final_generated = build_final_generated_shifts(data, year=year, month=month, force_regenerate=False)
    month_shifts = extract_month_generated_shifts(final_generated, year, month)

    if not month_shifts:
        return jsonify({'success': False, 'error': '一時保存対象の生成シフトがありません'}), 400

    if 'generated_shift_drafts' not in data:
        data['generated_shift_drafts'] = {}

    month_key = f"{year:04d}-{month:02d}"
    data['generated_shift_drafts'][month_key] = {
        'saved_at': datetime.now().isoformat(timespec='seconds'),
        'shifts': month_shifts
    }

    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] 生成シフト一時保存の保存に失敗: {str(e)}")
        return jsonify({'success': False, 'error': '生成シフト一時保存に失敗しました: ' + str(e)}), 500

    return jsonify({
        'success': True,
        'month': month_key,
        'saved_dates': len(month_shifts)
    })

@app.route('/api/generated-shift/confirm', methods=['POST'])
@require_admin
def confirm_generated_shift():
    """指定月の生成シフトを確定する（管理者のみ）"""
    year = request.json.get('year') if request.json else None
    month = request.json.get('month') if request.json else None

    try:
        year = int(year)
        month = int(month)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '年月が不正です'}), 400

    if month < 1 or month > 12:
        return jsonify({'success': False, 'error': '月の指定が不正です'}), 400

    data = load_data()
    month_key = f"{year:04d}-{month:02d}"

    draft_entry = data.get('generated_shift_drafts', {}).get(month_key, {})
    month_shifts = draft_entry.get('shifts') if isinstance(draft_entry, dict) else None

    # 一時保存が未作成の場合は、現時点の生成結果を直接確定
    if not month_shifts:
        final_generated = build_final_generated_shifts(data, year=year, month=month, force_regenerate=False)
        month_shifts = extract_month_generated_shifts(final_generated, year, month)

    if not month_shifts:
        return jsonify({'success': False, 'error': '確定対象の生成シフトがありません'}), 400

    if 'confirmed_generated_shifts' not in data:
        data['confirmed_generated_shifts'] = {}

    data['confirmed_generated_shifts'][month_key] = {
        'confirmed_at': datetime.now().isoformat(timespec='seconds'),
        'shifts': month_shifts
    }

    # 確定結果を生成表に反映（以降の表示で再現される）
    replace_month_manual_generated_shifts(data, year, month, month_shifts)

    try:
        save_data(data)
    except Exception as e:
        print(f"[ERROR] 生成シフト確定の保存に失敗: {str(e)}")
        return jsonify({'success': False, 'error': '生成シフト確定に失敗しました: ' + str(e)}), 500

    return jsonify({
        'success': True,
        'month': month_key,
        'confirmed_dates': len(month_shifts)
    })

def optimize_shifts(data):
    """時間帯包含を考慮してシフトを最適化（詳細設定に従って社員・アルバイトを配置）"""
    optimized = {}
    settings = data.get('shift_settings', get_default_shift_settings())
    staff_types = get_staff_types(data, settings)
    time_slots = data.get('time_slots', get_default_time_slots())
    change_map = build_shift_change_map(time_slots)
    
    for date_str, shifts in data['shifts'].items():
        optimized[date_str] = {}
        
        # 各時間帯の必要人数と現在の配置を確認
        time_slot_needs = {}
        for time_slot in time_slots:
            required_by_type = {}
            assigned_by_type = {}
            for staff_type in staff_types:
                required_by_type[staff_type] = get_required_staff(
                    date_str,
                    time_slot,
                    staff_type,
                    settings
                )
                assigned_by_type[staff_type] = []

            time_slot_needs[time_slot] = {
                'required_by_type': required_by_type,
                'assigned_by_type': assigned_by_type
            }
        
        # スタッフを種別ごとに分類（社員優先）
        staff_by_type = {}
        for staff_type in staff_types:
            staff_by_type[staff_type] = []
        
        for staff_name, slots in shifts.items():
            staff_info = data['staff'].get(staff_name, {})
            staff_type = staff_info.get('type', 'アルバイト')
            if slots:  # 希望時間帯がある場合のみ
                # スロットを選択シフトと自由入力シフトに分離
                selected_slots = [s for s in slots if s in time_slots]  # 時間帯リストに存在するシフト
                
                # 選択シフトのみを配置処理の対象にする
                if selected_slots:
                    staff_by_type[staff_type].append((staff_name, selected_slots))
        
        # 社員を優先的に配置（複数の時間帯を選択可能）
        for staff_type in ['社員'] + [t for t in staff_types if t != '社員']:
            for staff_name, slots in staff_by_type.get(staff_type, []):
                for slot in slots:
                    # この時間帯がカバーする時間帯をチェック
                    covered = get_covered_slots([slot])
                    
                    best_slot = slot
                    can_use = False
                    
                    # まず元の時間帯で使用可能かチェック
                    all_covered_ok = True
                    for covered_slot in covered:
                        slot_needs = time_slot_needs.get(covered_slot, {})
                        assigned = slot_needs.get('assigned_by_type', {}).get(staff_type, [])
                        required = slot_needs.get('required_by_type', {}).get(staff_type, 0)
                        if len(assigned) >= required:
                            all_covered_ok = False
                            break
                    
                    if all_covered_ok:
                        # 元の時間帯で問題なし
                        can_use = True
                        best_slot = slot
                    else:
                        # アルバイトの場合のみ時間変更を試みる（社員は固定）
                        if staff_type != '社員' and slot in change_map:
                            for alternative_slot in change_map[slot]:
                                alt_covered = get_covered_slots([alternative_slot])
                                alt_ok = True
                                for covered_slot in alt_covered:
                                    slot_needs = time_slot_needs.get(covered_slot, {})
                                    assigned = slot_needs.get('assigned_by_type', {}).get(staff_type, [])
                                    required = slot_needs.get('required_by_type', {}).get(staff_type, 0)
                                    if len(assigned) >= required:
                                        alt_ok = False
                                        break
                                
                                if alt_ok:
                                    # この代替時間帯が使える
                                    can_use = True
                                    best_slot = alternative_slot
                                    break
                    
                    # シフトを配置（必要人数に達していなければ配置）
                    if can_use:
                        if staff_name not in optimized[date_str]:
                            optimized[date_str][staff_name] = []
                        optimized[date_str][staff_name].append(best_slot)
                        
                        # 配置を記録
                        best_covered = get_covered_slots([best_slot])
                        for covered_slot in best_covered:
                            time_slot_needs[covered_slot]['assigned_by_type'][staff_type].append({
                                'staff': staff_name,
                                'slot': best_slot
                            })
        
        # 最適化後にシフトが1つもない日付は削除
        if not optimized[date_str]:
            del optimized[date_str]
    
    return optimized

def get_required_staff(date_str, time_slot, staff_type, settings=None):
    """指定日時の必要人数を計算（種別ごと、設定モード対応、祝日判定対応）"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    weekday = date_obj.weekday()  # 0=月, 1=火, ..., 5=土, 6=日
    
    # 設定を取得
    if settings is None:
        data = load_data()
        settings = data.get('shift_settings', get_default_shift_settings())
    
    # 設定モードを確認
    mode = settings.get('mode', 'weekday_weekend') if isinstance(settings, dict) else 'weekday_weekend'
    
    if mode == 'daily':
        # 曜日ごとモード：Pythonの weekday を JSON の day_of_week に変換
        # Pythonの weekday: 0=月, 6=日
        # JSONの day_index: 0=日, 6=土
        day_of_week = (weekday + 1) % 7  # 月(0) -> 1, 日(6) -> 0 に変換
        daily_settings = settings.get('daily', {}) if isinstance(settings, dict) else {}
        # JSONから来たキーは文字列なので、文字列キーでアクセス
        day_key_str = str(day_of_week)
        time_settings = daily_settings.get(day_key_str, {}).get(time_slot, {}) if isinstance(daily_settings, dict) else {}
    elif mode == 'weekday_weekend_with_holidays':
        # 祝日対応モード（日-木、金、土、祝日、祝前日に分けて設定）
        day_type = get_day_type(date_str)
        weekday_weekend_extended = settings.get('weekday_weekend_with_holidays', {}) if isinstance(settings, dict) else {}
        time_settings = weekday_weekend_extended.get(day_type, {}).get(time_slot, {}) if isinstance(weekday_weekend_extended, dict) else {}
    else:
        # 平日・週末モード（デフォルト）
        # 祝前日の場合は週末扱いにする（祝日は祝日別パターンでのみ対応）
        is_weekend = weekday in [4, 5] or is_day_before_holiday(date_obj)  # 金(4)土(5)または祝前日
        day_type = 'weekend' if is_weekend else 'weekday'
        weekday_weekend = settings.get('weekday_weekend', {}) if isinstance(settings, dict) else settings
        time_settings = weekday_weekend.get(day_type, {}).get(time_slot, {}) if isinstance(weekday_weekend, dict) else {}
    
    return time_settings.get(staff_type, 0)

@app.route('/api/check_requirements', methods=['POST'])
def check_requirements():
    """必要人数チェック・時間帯包含考慮"""
    date = request.json.get('date')
    
    if not date:
        return jsonify({'error': 'パラメータが不足しています'}), 400
    
    data = load_data()
    
    # シフトを最適化
    optimized_shifts = optimize_shifts(data)
    
    # この日のシフトを取得（最適化後）
    shifts = optimized_shifts.get(date, {})
    
    # 各時間帯の充足状況をチェック
    results = []
    time_slots = data.get('time_slots', get_default_time_slots())
    settings = data.get('shift_settings', get_default_shift_settings())
    staff_types = get_staff_types(data, settings)
    
    for time_slot in time_slots:
        required_by_type = {}
        assigned_by_type = {staff_type: 0 for staff_type in staff_types}

        for staff_type in staff_types:
            required_by_type[staff_type] = get_required_staff(
                date,
                time_slot,
                staff_type,
                settings
            )

        # 実際に入っている人数を計算（時間帯包含を考慮）
        for staff_name, slots in shifts.items():
            covered = get_covered_slots(slots)
            if time_slot in covered:
                staff_info = data['staff'].get(staff_name, {})
                staff_type = staff_info.get('type', 'アルバイト')
                if staff_type in assigned_by_type:
                    assigned_by_type[staff_type] += 1

        ok_by_type = {}
        for staff_type in staff_types:
            ok_by_type[staff_type] = assigned_by_type[staff_type] >= required_by_type[staff_type]

        results.append({
            'time_slot': time_slot,
            'required_by_type': required_by_type,
            'assigned_by_type': assigned_by_type,
            'ok_by_type': ok_by_type
        })
    
    return jsonify(results)

@app.route('/api/export/csv', methods=['GET'])
@require_admin
def export_csv():
    """PDFファイルをエクスポート（表形式）（管理者のみ）"""
    data = load_data()
    
    # クエリパラメータからスタッフ順序を取得
    order_param = request.args.get('order', None)
    staff_order = {}
    if order_param:
        try:
            import urllib.parse
            staff_order = json.loads(urllib.parse.unquote(order_param))
        except:
            staff_order = {}
    
    # シフトを最適化
    optimized_shifts = optimize_shifts(data)
    
    # 日付を収集
    dates = sorted(set(list(data['shifts'].keys())))
    
    if not dates:
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        styles = getSampleStyleSheet()
        empty_style = ParagraphStyle(
            "Empty",
            parent=styles["Normal"],
            fontName="HeiseiKakuGo-W5",
            fontSize=12
        )
        doc.build([Paragraph("シフトデータがありません", empty_style)])
        pdf_buffer.seek(0)
    else:
        # 月別にグループ化
        monthly_data = {}
        for date_str in dates:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month_key = f"{date_obj.year}-{date_obj.month:02d}"
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(date_str)
        
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=landscape(A4),
            leftMargin=20,
            rightMargin=20,
            topMargin=20,
            bottomMargin=20
        )
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
        styles = getSampleStyleSheet()
        base_style = ParagraphStyle(
            "Base",
            parent=styles["Normal"],
            fontName="HeiseiKakuGo-W5",
            fontSize=8,
            leading=10
        )
        header_style = ParagraphStyle(
            "Header",
            parent=base_style,
            textColor=colors.white,
            alignment=1
        )
        name_style = ParagraphStyle(
            "Name",
            parent=base_style,
            alignment=0
        )
        center_style = ParagraphStyle(
            "Center",
            parent=base_style,
            alignment=1
        )
        title_style = ParagraphStyle(
            "Title",
            parent=base_style,
            fontSize=12,
            leading=14
        )
        story = []
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        
        # 月ごとにテーブルを生成
        month_items = list(sorted(monthly_data.items()))
        for idx, (month_key, month_dates) in enumerate(month_items):
            first_date = datetime.strptime(month_dates[0], '%Y-%m-%d')
            month_label = f"{first_date.year}年{first_date.month}月"
            story.append(Paragraph(month_label, title_style))
            story.append(Spacer(1, 8))
            
            # スタッフリストを取得
            staff_set = set(data['staff'].keys())
            for date_str in month_dates:
                if date_str in optimized_shifts:
                    staff_set.update(optimized_shifts[date_str].keys())
            
            staff_list = sorted(staff_set)
            
            # スタッフ順序があれば適用
            if month_label in staff_order and staff_order[month_label]:
                # 指定された順序で並べ替え、存在しないスタッフは末尾に追加
                ordered_list = []
                for name in staff_order[month_label]:
                    if name in staff_list:
                        ordered_list.append(name)
                # 順序リストにない残りのスタッフを追加
                for name in staff_list:
                    if name not in ordered_list:
                        ordered_list.append(name)
                staff_list = ordered_list
            
            header_row = [Paragraph("名前", header_style)]
            for date_str in month_dates:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                weekday_jp = weekday_names[date_obj.weekday()]
                header_row.append(Paragraph(f"{date_obj.day}日<br/>({weekday_jp})", header_style))
            
            table_data = [header_row]
            for staff_name in staff_list:
                row = [Paragraph(staff_name, name_style)]
                for date_str in month_dates:
                    time_slots = []
                    if date_str in optimized_shifts and staff_name in optimized_shifts[date_str]:
                        time_slots = optimized_shifts[date_str][staff_name]
                    cell_text = "<br/>".join(time_slots) if time_slots else "-"
                    row.append(Paragraph(cell_text, center_style))
                table_data.append(row)
            
            available_width = landscape(A4)[0] - doc.leftMargin - doc.rightMargin
            first_col_width = 70
            if len(month_dates) > 0:
                other_width = max(35, (available_width - first_col_width) / len(month_dates))
            else:
                other_width = 50
            col_widths = [first_col_width] + [other_width] * len(month_dates)
            
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3)
            ]))
            story.append(table)
            
            if idx < len(month_items) - 1:
                story.append(PageBreak())
        
        doc.build(story)
        pdf_buffer.seek(0)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'shift_{datetime.now().strftime("%Y%m%d")}.pdf'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
