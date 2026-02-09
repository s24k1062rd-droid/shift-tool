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
    """トップページ"""
    return render_template('index.html')

@app.route('/api/staff', methods=['GET'])
def get_staff():
    """スタッフ一覧を取得"""
    data = load_data()
    return jsonify(data['staff'])

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
        'staff': data['staff'],
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
def update_requirement():
    """必要人数を更新"""
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

@app.route('/api/generate', methods=['GET'])
def generate_shift():
    """シフト表を生成（表形式・最適化機能付き）"""
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
    """時間帯包含を考慮してシフトを最適化（社員は1日1人のみ、アルバイトのみ調整・削除・時間変更）"""
    optimized = {}
    
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
        
        # アルバイトのシフトを収集
        parttime_shifts = {}
        for staff_name, slots in shifts.items():
            staff_info = data['staff'].get(staff_name, {})
            staff_type = staff_info.get('type', 'アルバイト')
            if staff_type == 'アルバイト':
                parttime_shifts[staff_name] = slots[:]
        
        # 各時間帯の必要人数と現在の配置を確認
        time_slot_needs = {}
        for time_slot in SHIFT_TIME_SLOTS:
            req_parttime = get_required_staff(date_str, time_slot)
            time_slot_needs[time_slot] = {
                'required': req_parttime,
                'assigned': []
            }
        
        # 各アルバイトの時間帯を分析し、最適化
        for staff_name, slots in parttime_shifts.items():
            for slot in slots:
                # この時間帯がカバーする時間帯をチェック（アルバイトは単一時間帯のみ）
                covered = get_covered_slots([slot])
                
                # 時間変更を試みる（過剰な時間帯から不足している時間帯へ）
                best_slot = slot
                can_use = False
                
                # まず元の時間帯で使用可能かチェック
                all_covered_ok = True
                for covered_slot in covered:
                    if len(time_slot_needs[covered_slot]['assigned']) >= time_slot_needs[covered_slot]['required']:
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
                                if len(time_slot_needs[covered_slot]['assigned']) >= time_slot_needs[covered_slot]['required']:
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
                        time_slot_needs[covered_slot]['assigned'].append({
                            'staff': staff_name,
                            'slot': best_slot
                        })
        
        # 最適化後にシフトが1つもない日付は削除
        if not optimized[date_str]:
            del optimized[date_str]
    
    return optimized

def get_required_staff(date_str, time_slot):
    """指定日時の必要アルバイト数を計算（社員は通し勤務で固定、調整対象外）"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    weekday = date_obj.weekday()  # 0=月, 6=日
    
    # 祝日判定（簡易版：実際の祝日判定は別途実装が必要）
    is_friday_or_saturday = weekday in [4, 5]  # 金土
    is_sunday_to_thursday = weekday in [6, 0, 1, 2, 3]  # 日～木
    
    required_parttime = 0
    
    if time_slot == '10-15':
        # ランチ：アルバイト1人
        required_parttime = 1
    elif time_slot == '17-23':
        # 17-23の時間帯
        if is_friday_or_saturday:
            # 金土祝前日：アルバイト1人
            required_parttime = 1
        else:
            # 日～木：アルバイト0人（社員のみ）
            required_parttime = 0
    elif time_slot == '18-23':
        # 18-23の時間帯
        if is_friday_or_saturday:
            # 金土祝前日：アルバイト2人
            required_parttime = 2
        else:
            # 日～木：アルバイト1人
            required_parttime = 1
    elif time_slot == '19-23':
        # 19-23の時間帯
        if is_friday_or_saturday:
            # 金土祝前日：アルバイト3人
            required_parttime = 3
        else:
            # 日～木：アルバイト2人
            required_parttime = 2
    
    return required_parttime

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
    
    for time_slot in SHIFT_TIME_SLOTS:
        req_parttime = get_required_staff(date, time_slot)
        
        # 実際に入っている人数を計算（時間帯包含を考慮）
        assigned_staff = 0
        assigned_parttime = 0
        
        for staff_name, slots in shifts.items():
            # スタッフの時間帯が現在の時間帯をカバーしているか
            # 複数の時間帯を持つ場合（社員の通し勤務）を考慮
            covered = get_covered_slots(slots)
            if time_slot in covered:
                staff_info = data['staff'].get(staff_name, {})
                if staff_info.get('type') == '社員':
                    assigned_staff += 1
                else:
                    assigned_parttime += 1
        
        results.append({
            'time_slot': time_slot,
            'required_parttime': req_parttime,
            'assigned_staff': assigned_staff,
            'assigned_parttime': assigned_parttime,
            'parttime_ok': assigned_parttime >= req_parttime
        })
    
    return jsonify(results)

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """CSVファイルをエクスポート"""
    data = load_data()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['日付', 'スタッフ名', '時間帯'])
    
    for date in sorted(data['shifts'].keys()):
        for staff, time_slots in sorted(data['shifts'][date].items()):
            for slot in time_slots:
                writer.writerow([date, staff, slot])
    
    # StringIOをBytesIOに変換
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
        sys.exit(1)
    
    # Flaskアプリを起動
    app.run(host='0.0.0.0', port=5000, debug=False)
