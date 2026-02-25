"""
オンラインシフト入力＆作成ツール（Web版）
スマホ対応
"""

from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_session import Session
import json
import os
from datetime import datetime, timedelta
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

def get_store_data_file(store_code):
    """店舗ごとのデータファイルパスを取得"""
    os.makedirs('shift_data', exist_ok=True)
    return os.path.join('shift_data', f'{store_code}_data.json')

# 固定のシフト時間帯
SHIFT_TIME_SLOTS = [
    '10-15',
    '17-23',
    '18-23',
    '19-23'
]

# 時間帯の変更可能先マップ
SHIFT_CHANGE_MAP = {
    '17-23': ['18-23', '19-23'],
    '18-23': ['19-23']
}

# 時間帯の包含関係（この時間帯はどの時間帯に含まれるか）
SHIFT_COVERAGE = {
    '17-23': ['17-23', '18-23', '19-23'],  # 17-23は18-23, 19-23も含む
    '18-23': ['18-23', '19-23'],  # 18-23は19-23も含む
    '19-23': ['19-23'],
    '10-15': ['10-15']
}

def get_covered_slots(time_slots):
    """指定された時間帯（単一または複数）がカバーする時間帯リストを返す
    10-15と17-23の両方がある場合は、すべての時間帯をカバーする
    """
    if isinstance(time_slots, str):
        time_slots = [time_slots]
    
    # 10-15と17-23の両方がある場合は、すべての時間帯をカバー
    if '10-15' in time_slots and '17-23' in time_slots:
        return ['10-15', '17-23', '18-23', '19-23']
    
    # 単一または通常の組み合わせの場合
    covered = set()
    for slot in time_slots:
        covered.update(SHIFT_COVERAGE.get(slot, [slot]))
    
    return sorted(list(covered))

def get_default_time_slots():
    """デフォルトの時間帯を返す"""
    return ['10-15', '17-23', '18-23', '19-23']

def get_default_shift_settings():
    """デフォルトのシフト設定を返す"""
    return {
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
    """シフト設定を種別ごとの形式に正規化"""
    normalized = {'weekday': {}, 'weekend': {}}

    for day_type in ['weekday', 'weekend']:
        day_settings = settings.get(day_type, {}) if isinstance(settings, dict) else {}
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

    return normalized

def load_data(store_code=None):
    """データを読み込み"""
    if store_code is None:
        store_code = session.get('store_code', 'default')
    
    data_file = get_store_data_file(store_code)
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
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
            # 種別ごとの設定に正規化
            staff_types = get_staff_types(data, data.get('shift_settings'))
            data['shift_settings'] = normalize_shift_settings(
                data.get('shift_settings', {}),
                data.get('time_slots', get_default_time_slots()),
                staff_types
            )
            # admin_passwordがない場合はデフォルトを設定
            if 'admin_password' not in data:
                data['admin_password'] = ADMIN_PASSWORD
            return data
    return {
        'staff': {},  # スタッフ情報の辞書 {name: {type: '社員' or 'アルバイト' or 任意}}
        'shifts': {},  # {date: {staff: [time_slots]}}
        'requirements': {},  # {date: {time_slot: count}}
        'shift_settings': get_default_shift_settings(),  # シフト詳細設定
        'time_slots': get_default_time_slots(),  # 時間帯リスト
        'admin_password': ADMIN_PASSWORD  # 管理者パスワード（店舗ごと）
    }

def save_data(data, store_code=None):
    """データを保存"""
    if store_code is None:
        store_code = session.get('store_code', 'default')
    
    data_file = get_store_data_file(store_code)
    os.makedirs(os.path.dirname(data_file), exist_ok=True)
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    
    if not store_code:
        return jsonify({'success': False, 'error': '店舗コードを入力してください'}), 400
    
    # 店舗データを読み込み（セッション設定前なので直接指定）
    data_file = get_store_data_file(store_code)
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            store_data = json.load(f)
        store_password = store_data.get('admin_password', ADMIN_PASSWORD)
    else:
        # 新規店舗の場合はデフォルトパスワード
        store_password = ADMIN_PASSWORD
    
    # 管理者パスワード確認
    if role == 'admin' and password != store_password:
        return jsonify({'success': False, 'error': 'パスワードが違います'}), 401
    
    # セッションに情報を保存
    session['role'] = role
    session['store_code'] = store_code
    session.permanent = True
    
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

def require_admin(f):
    """管理者専用エンドポイント用デコレータ"""
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': '管理者のみアクセス可能です'}), 403
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

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
    
    if not staff_name:
        return jsonify({'error': 'スタッフ名を入力してください'}), 400
    
    if not staff_type:
        return jsonify({'error': '種別を入力してください'}), 400
    
    data = load_data()
    
    if staff_name in data['staff']:
        return jsonify({'error': 'このスタッフは既に登録されています'}), 400
    
    data['staff'][staff_name] = {'type': staff_type}
    save_data(data)
    
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
    
    save_data(data)
    
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
    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        month_shifts[date_str] = data['shifts'].get(date_str, {})
    
    return jsonify({
        'shifts': month_shifts,
        'staff': data['staff'],
        'time_slots': data.get('time_slots', SHIFT_TIME_SLOTS),
        'change_map': SHIFT_CHANGE_MAP,
        'days_in_month': days_in_month
    })

@app.route('/api/shifts', methods=['POST'])
def update_shift():
    """シフト希望を更新"""
    date = request.json.get('date')
    staff = request.json.get('staff')
    time_slots = request.json.get('time_slots', [])
    
    if not date or not staff:
        return jsonify({'error': 'パラメータが不足しています'}), 400
    
    data = load_data()
    
    if staff not in data['staff']:
        return jsonify({'error': 'スタッフが登録されていません'}), 400
    
    if date not in data['shifts']:
        data['shifts'][date] = {}
    
    if time_slots:
        data['shifts'][date][staff] = time_slots
    else:
        # 空の場合は削除
        if staff in data['shifts'][date]:
            del data['shifts'][date][staff]
        if not data['shifts'][date]:
            del data['shifts'][date]
    
    save_data(data)
    
    return jsonify({'success': True})

@app.route('/api/update-shift', methods=['POST'])
@require_admin
def update_shift_inline():
    """シフト表から手作業でシフトを更新（管理者のみ）"""
    staff_name = request.json.get('staff_name')
    date = request.json.get('date')
    shifts = request.json.get('shifts', [])
    
    if not date or not staff_name:
        return jsonify({'error': 'パラメータが不足しています', 'success': False}), 400
    
    data = load_data()
    
    if staff_name not in data['staff']:
        return jsonify({'error': 'スタッフが登録されていません', 'success': False}), 400
    
    if date not in data['shifts']:
        data['shifts'][date] = {}
    
    if shifts:
        data['shifts'][date][staff_name] = shifts
    else:
        # 空の場合は削除
        if staff_name in data['shifts'][date]:
            del data['shifts'][date][staff_name]
        if not data['shifts'][date]:
            del data['shifts'][date]
    
    save_data(data)
    
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
        'time_slots': SHIFT_TIME_SLOTS,
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
    
    save_data(data)
    
    return jsonify({'success': True})

@app.route('/api/shift-settings', methods=['GET'])
@require_admin
def get_shift_settings():
    """シフト詳細設定を取得（管理者のみ）"""
    data = load_data()
    time_slots = data.get('time_slots', get_default_time_slots())
    staff_types = get_staff_types(data, data.get('shift_settings'))
    settings = normalize_shift_settings(
        data.get('shift_settings', get_default_shift_settings()),
        time_slots,
        staff_types
    )
    return jsonify({'success': True, 'settings': settings, 'time_slots': time_slots, 'staff_types': staff_types})

@app.route('/api/shift-settings', methods=['POST'])
@require_admin
def update_shift_settings():
    """シフト詳細設定を更新（管理者のみ）"""
    settings = request.json.get('settings')
    
    if not settings:
        return jsonify({'error': '設定データが不足しています'}), 400
    
    data = load_data()
    time_slots = data.get('time_slots', get_default_time_slots())
    staff_types = get_staff_types(data, settings)
    data['shift_settings'] = normalize_shift_settings(settings, time_slots, staff_types)
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
    save_data(data)
    
    return jsonify({'success': True})

@app.route('/api/change-password', methods=['POST'])
@require_admin
def change_password():
    """管理者パスワードを変更（管理者のみ）"""
    current_password = request.json.get('current_password', '')
    new_password = request.json.get('new_password', '')
    
    if not new_password:
        return jsonify({'error': '新しいパスワードを入力してください'}), 400
    
    if len(new_password) < 4:
        return jsonify({'error': 'パスワードは4文字以上にしてください'}), 400
    
    data = load_data()
    
    # 現在のパスワード確認
    current_stored_password = data.get('admin_password', ADMIN_PASSWORD)
    if current_password != current_stored_password:
        return jsonify({'error': '現在のパスワードが違います'}), 401
    
    # 新しいパスワードを保存
    data['admin_password'] = new_password
    save_data(data)
    
    return jsonify({'success': True, 'message': 'パスワードを変更しました'})
    
    return jsonify({'success': True})

@app.route('/api/generate', methods=['GET'])
@require_admin
def generate_shift():
    """シフト表を生成（表形式・最適化機能付き）（管理者のみ）"""
    data = load_data()
    
    # 日付を収集してソート
    dates = sorted(set(list(data['shifts'].keys())))
    
    if not dates:
        return jsonify({'dates': [], 'staff_list': [], 'shift_table': []})
    
    # シフトを最適化（必要人数に合わせて調整）
    optimized_shifts = optimize_shifts(data)
    
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
            month_info['dates'].append({
                'date': date_str,
                'day': date_obj.day,
                'weekday': weekday_jp
            })
        
        # スタッフリストを取得（シフトに含まれるスタッフも含める）
        staff_set = set(data['staff'].keys())
        # シフトに含まれるスタッフを追加
        for date_str in month_dates:
            if date_str in optimized_shifts:
                staff_set.update(optimized_shifts[date_str].keys())
        
        staff_list = sorted(staff_set)
        
        # 各スタッフのシフトを表形式に（最適化されたシフトを使用）
        for staff_name in staff_list:
            staff_info = data['staff'].get(staff_name, {})
            row = {
                'name': staff_name,
                'type': staff_info.get('type', 'アルバイト'),  # 未登録スタッフはアルバイト扱い
                'shifts': []
            }
            
            for date_str in month_dates:
                time_slots = []
                if date_str in optimized_shifts and staff_name in optimized_shifts[date_str]:
                    time_slots = optimized_shifts[date_str][staff_name]
                row['shifts'].append(time_slots)
            
            month_info['staff_list'].append(row)
        
        result.append(month_info)
    
    return jsonify(result)

def optimize_shifts(data):
    """時間帯包含を考慮してシフトを最適化（社員は1日1人のみ、社員以外を調整・削除・時間変更）"""
    optimized = {}
    settings = data.get('shift_settings', get_default_shift_settings())
    staff_types = get_staff_types(data, settings)
    time_slots = data.get('time_slots', SHIFT_TIME_SLOTS)
    
    for date_str, shifts in data['shifts'].items():
        optimized[date_str] = {}
        
        # 社員のシフトを確認し、1日1人のみに制限
        staff_employees = []
        for staff_name, slots in shifts.items():
            staff_info = data['staff'].get(staff_name, {})
            staff_type = staff_info.get('type', 'アルバイト')
            if staff_type == '社員' and slots:
                staff_employees.append((staff_name, slots))
        
        # 社員が複数いる場合は、最も多くの時間帯を入れている社員を選択
        if staff_employees:
            # 時間帯の数でソート（降順）、同数の場合は名前順
            staff_employees.sort(key=lambda x: (-len(x[1]), x[0]))
            selected_staff, selected_slots = staff_employees[0]
            optimized[date_str][selected_staff] = selected_slots[:]
        
        # 社員以外のシフトを収集
        parttime_shifts = {}
        for staff_name, slots in shifts.items():
            staff_info = data['staff'].get(staff_name, {})
            staff_type = staff_info.get('type', 'アルバイト')
            if staff_type != '社員':
                parttime_shifts[staff_name] = slots[:]
        
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
        
        # 各アルバイトの時間帯を分析し、最適化
        for staff_name, slots in parttime_shifts.items():
            staff_info = data['staff'].get(staff_name, {})
            staff_type = staff_info.get('type', 'アルバイト')
            for slot in slots:
                # この時間帯がカバーする時間帯をチェック（アルバイトは単一時間帯のみ）
                covered = get_covered_slots([slot])
                
                # 時間変更を試みる（過剰な時間帯から不足している時間帯へ）
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
                    # 時間変更を試みる
                    if slot in SHIFT_CHANGE_MAP:
                        for alternative_slot in SHIFT_CHANGE_MAP[slot]:
                            alt_covered = get_covered_slots(alternative_slot)
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
                
                # シフトを配置
                if can_use:
                    if staff_name not in optimized[date_str]:
                        optimized[date_str][staff_name] = []
                    optimized[date_str][staff_name].append(best_slot)
                    
                    # 配置を記録（アルバイトは単一時間帯のみ）
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
    """指定日時の必要人数を計算（種別ごと）"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    weekday = date_obj.weekday()  # 0=月, 6=日
    
    # 設定を取得
    if settings is None:
        data = load_data()
        settings = data.get('shift_settings', get_default_shift_settings())
    
    # 金土判定
    is_weekend = weekday in [4, 5]  # 金土
    
    # 曜日に応じた設定を選択
    day_type = 'weekend' if is_weekend else 'weekday'
    time_settings = settings.get(day_type, {}).get(time_slot, {})
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
    time_slots = data.get('time_slots', SHIFT_TIME_SLOTS)
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
