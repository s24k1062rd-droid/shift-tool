"""
外部アクセス対応版 - シフト作成ツール
pyngrokを使用（要：ngrok authtoken設定）
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
from datetime import datetime, timedelta
import calendar
import csv
from io import StringIO, BytesIO
from pyngrok import ngrok
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'shift-tool-secret-key-2026'

# データファイルのパス
DATA_FILE = 'shift_data.json'

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

def load_data():
    """データを読み込み"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 旧データとの互換性のため、staffがリストの場合は辞書に変換
            if isinstance(data.get('staff'), list):
                staff_dict = {}
                for name in data['staff']:
                    staff_dict[name] = {'type': 'アルバイト'}  # デフォルトはアルバイト
                data['staff'] = staff_dict
            return data
    return {
        'staff': {},  # スタッフ情報の辞書 {name: {type: '社員' or 'アルバイト'}}
        'shifts': {},  # {date: {staff: [time_slots]}}
        'requirements': {}  # {date: {time_slot: count}}
    }

def save_data(data):
    """データを保存"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/staff', methods=['GET'])
def get_staff():
    """スタッフ一覧を取得"""
    data = load_data()
    return jsonify(data.get('staff', {}))

@app.route('/api/staff', methods=['POST'])
def add_staff():
    """スタッフを追加"""
    staff_name = request.json.get('name', '').strip()
    staff_type = request.json.get('type', 'アルバイト')  # 社員 or アルバイト
    
    if not staff_name:
        return jsonify({'error': 'スタッフ名を入力してください'}), 400
    
    if staff_type not in ['社員', 'アルバイト']:
        return jsonify({'error': '種別は「社員」または「アルバイト」を指定してください'}), 400
    
    data = load_data()
    
    if staff_name in data['staff']:
        return jsonify({'error': 'このスタッフは既に登録されています'}), 400
    
    data['staff'][staff_name] = {'type': staff_type}
    save_data(data)
    
    return jsonify({'success': True, 'staff': data['staff']})

@app.route('/api/staff/<staff_name>', methods=['DELETE'])
def delete_staff(staff_name):
    """スタッフを削除"""
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
        'staff': data.get('staff', {}),
        'time_slots': SHIFT_TIME_SLOTS,
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
    
    if staff not in data.get('staff', {}):
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
        month_requirements[date_str] = data.get('requirements', {}).get(date_str, {})
    
    return jsonify({
        'requirements': month_requirements,
        'time_slots': SHIFT_TIME_SLOTS,
        'days_in_month': days_in_month
    })

@app.route('/api/requirements', methods=['POST'])
def update_requirement():
    """必要人数を更新"""
    date = request.json.get('date')
    time_slot = request.json.get('time_slot')
    count = request.json.get('count')
    
    if not date or not time_slot:
        return jsonify({'error': 'パラメータが不足しています'}), 400
    
    data = load_data()
    
    if 'requirements' not in data:
        data['requirements'] = {}
    
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

@app.route('/api/data', methods=['GET'])
def get_data():
    """全データを取得"""
    data = load_data()
    return jsonify(data)

@app.route('/api/shift', methods=['POST'])
def save_shift():
    """シフトを保存"""
    req_data = request.json
    date = req_data.get('date')
    time_slot = req_data.get('time_slot')
    names = req_data.get('names', [])
    
    data = load_data()
    
    if date not in data['shifts']:
        data['shifts'][date] = {}
    
    data['shifts'][date][time_slot] = names
    
    save_data(data)
    return jsonify({'success': True})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """設定を保存"""
    req_data = request.json
    month = req_data.get('month')
    
    data = load_data()
    data['settings']['month'] = month
    
    save_data(data)
    return jsonify({'success': True})

@app.route('/api/export', methods=['GET'])
def export_csv():
    """CSVエクスポート"""
    data = load_data()
    shifts = data.get('shifts', {})
    month_str = data.get('settings', {}).get('month', datetime.now().strftime('%Y-%m'))
    
    try:
        year, month = map(int, month_str.split('-'))
    except:
        year = datetime.now().year
        month = datetime.now().month
    
    _, last_day = calendar.monthrange(year, month)
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['日付', '曜日'] + SHIFT_TIME_SLOTS)
    
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    
    for day in range(1, last_day + 1):
        date_obj = datetime(year, month, day)
        date_str = date_obj.strftime('%Y-%m-%d')
        weekday = weekdays[date_obj.weekday()]
        
        row = [date_obj.strftime('%m/%d'), weekday]
        
        for time_slot in SHIFT_TIME_SLOTS:
            names = shifts.get(date_str, {}).get(time_slot, [])
            row.append(', '.join(names) if names else '')
        
        writer.writerow(row)
    
    output.seek(0)
    mem = BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    
    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'shift_{datetime.now().strftime("%Y%m%d")}.csv'
    )

if __name__ == '__main__':
    # ngrokトンネルを開始
    try:
        print("\n" + "=" * 70)
        print("  シフト作成ツール - 外部アクセス版")
        print("=" * 70)
        print("\n📡 ngrokトンネルを作成中...")
        
        # ngrokトンネルを作成
        public_url = ngrok.connect(5000, bind_tls=True)
        
        print("\n✅ 外部アクセスURL:")
        print(f"   {public_url}")
        print("\n" + "=" * 70)
        print("📱 スマホや他のPCからこのURLでアクセスできます")
        print("=" * 70)
        print("\n⚠️  終了する場合は Ctrl+C を押してください\n")
        
    except Exception as e:
        print(f"\n⚠️  ngrokの起動に失敗しました: {e}")
        print("\n解決方法:")
        print("1. https://ngrok.com/signup で無料アカウントを作成")
        print("2. ダッシュボードからauthtokenをコピー")
        print("3. 以下のコマンドを実行:")
        print("   ngrok config add-authtoken <あなたのトークン>")
        print("\nまたは、start_localhostrun.bat を使用してください（認証不要）\n")
        
        # ngrokなしでもローカルで起動
        print("📍 ローカルモードで起動します...")
        print("   http://localhost:5000\n")
    
    # Flaskアプリを起動
    app.run(host='0.0.0.0', port=5000, debug=False)
