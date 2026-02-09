"""
アルバイト先のシフト入力＆適正シフト情報作成ツール
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
from datetime import datetime, timedelta
from typing import List, Dict
import csv
import calendar

class ShiftTool:
    def __init__(self, root):
        self.root = root
        self.root.title("シフト作成ツール")
        self.root.geometry("1200x750")
        
        # データ保存用
        self.staff_data = {}  # {スタッフ名: {max_hours: int}}
        self.shift_requests = {}  # {日付: {スタッフ名: 希望時間帯}}
        self.requirements = {}  # {日付: {時間帯: 必要人数}}
        
        # 表示用の日付範囲
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        
        self.create_widgets()
        
    def create_widgets(self):
        """ウィジェットの作成"""
        # タブの作成
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # タブ1: スタッフ管理
        self.staff_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.staff_frame, text="スタッフ管理")
        self.create_staff_tab()
        
        # タブ2: シフト希望入力（表形式）
        self.request_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.request_frame, text="シフト希望入力")
        self.create_table_request_tab()
        
        # タブ3: 必要人数設定（表形式）
        self.requirement_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.requirement_frame, text="必要人数設定")
        self.create_table_requirement_tab()
        
        # タブ4: シフト生成・表示
        self.generate_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.generate_frame, text="シフト生成")
        self.create_generate_tab()
        
    def create_staff_tab(self):
        """スタッフ管理タブ"""
        # 上部: 入力フォーム
        input_frame = ttk.LabelFrame(self.staff_frame, text="新規スタッフ追加", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="スタッフ名:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.staff_name_entry = ttk.Entry(input_frame, width=30)
        self.staff_name_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="週最大勤務時間:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.max_hours_entry = ttk.Entry(input_frame, width=30)
        self.max_hours_entry.grid(row=1, column=1, padx=5)
        
        ttk.Button(input_frame, text="追加", command=self.add_staff).grid(row=2, column=0, columnspan=2, pady=10)
        
        # 下部: スタッフリスト
        list_frame = ttk.LabelFrame(self.staff_frame, text="登録済みスタッフ", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # スクロールバー付きのリストボックス
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.staff_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15)
        self.staff_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.staff_listbox.yview)
        
        # 削除ボタン
        ttk.Button(list_frame, text="選択したスタッフを削除", command=self.delete_staff).pack(pady=5)
        
    def create_table_request_tab(self):
        """シフト希望入力タブ（表形式）"""
        # 上部: 月選択と操作ボタン
        control_frame = ttk.Frame(self.request_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="◀ 前月", command=self.prev_month_request).pack(side=tk.LEFT, padx=5)
        
        self.month_label_request = ttk.Label(control_frame, text="", font=("", 12, "bold"))
        self.month_label_request.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(control_frame, text="次月 ▶", command=self.next_month_request).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="表を更新", command=self.update_request_table).pack(side=tk.LEFT, padx=20)
        
        # 表形式の入力エリア
        table_frame = ttk.LabelFrame(self.request_frame, text="シフト希望（日付をダブルクリックして時間帯を入力）", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # スクロールバー
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview（表）
        self.request_tree = ttk.Treeview(table_frame, 
                                         yscrollcommand=scrollbar_y.set,
                                         xscrollcommand=scrollbar_x.set,
                                         selectmode='browse')
        self.request_tree.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.request_tree.yview)
        scrollbar_x.config(command=self.request_tree.xview)
        
        # ダブルクリックイベント
        self.request_tree.bind("<Double-1>", self.on_request_cell_double_click)
        
        self.update_request_table()
    
    def create_table_requirement_tab(self):
        """必要人数設定タブ（表形式）"""
        # 上部: 月選択と操作ボタン
        control_frame = ttk.Frame(self.requirement_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="◀ 前月", command=self.prev_month_requirement).pack(side=tk.LEFT, padx=5)
        
        self.month_label_requirement = ttk.Label(control_frame, text="", font=("", 12, "bold"))
        self.month_label_requirement.pack(side=tk.LEFT, padx=20)
        
        ttk.Button(control_frame, text="次月 ▶", command=self.next_month_requirement).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="表を更新", command=self.update_requirement_table).pack(side=tk.LEFT, padx=20)
        
        # 表形式の入力エリア
        table_frame = ttk.LabelFrame(self.requirement_frame, text="必要人数（日付をダブルクリックして時間帯と人数を入力）", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # スクロールバー
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview（表）
        self.requirement_tree = ttk.Treeview(table_frame,
                                             yscrollcommand=scrollbar_y.set,
                                             xscrollcommand=scrollbar_x.set,
                                             selectmode='browse')
        self.requirement_tree.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.requirement_tree.yview)
        scrollbar_x.config(command=self.requirement_tree.xview)
        
        # ダブルクリックイベント
        self.requirement_tree.bind("<Double-1>", self.on_requirement_cell_double_click)
        
        self.update_requirement_table()
        
    def create_generate_tab(self):
        """シフト生成タブ"""
        control_frame = ttk.Frame(self.generate_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="シフトを生成", command=self.generate_shift, 
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="CSV出力", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="データ保存", command=self.save_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="データ読込", command=self.load_data).pack(side=tk.LEFT, padx=5)
        
        # 結果表示エリア
        result_frame = ttk.LabelFrame(self.generate_frame, text="生成されたシフト", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # スクロールバー付きテキストエリア
        scrollbar_y = ttk.Scrollbar(result_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        scrollbar_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.result_text = tk.Text(result_frame, wrap=tk.NONE,
                                   yscrollcommand=scrollbar_y.set,
                                   xscrollcommand=scrollbar_x.set)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_y.config(command=self.result_text.yview)
        scrollbar_x.config(command=self.result_text.xview)
        
    # 表形式関連のメソッド
    def prev_month_request(self):
        """前月に移動（シフト希望）"""
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.update_request_table()
    
    def next_month_request(self):
        """次月に移動（シフト希望）"""
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.update_request_table()
    
    def prev_month_requirement(self):
        """前月に移動（必要人数）"""
        self.current_month -= 1
        if self.current_month < 1:
            self.current_month = 12
            self.current_year -= 1
        self.update_requirement_table()
    
    def next_month_requirement(self):
        """次月に移動（必要人数）"""
        self.current_month += 1
        if self.current_month > 12:
            self.current_month = 1
            self.current_year += 1
        self.update_requirement_table()
    
    def update_request_table(self):
        """シフト希望表を更新"""
        # 表をクリア
        for item in self.request_tree.get_children():
            self.request_tree.delete(item)
        
        # 月表示を更新
        self.month_label_request.config(text=f"{self.current_year}年{self.current_month}月")
        
        # カラム設定（日付列）
        days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]
        columns = ["スタッフ名"] + [f"{d}日" for d in range(1, days_in_month + 1)]
        
        self.request_tree['columns'] = columns
        self.request_tree['show'] = 'tree headings'
        
        # カラム幅設定
        self.request_tree.column('#0', width=0, stretch=tk.NO)
        self.request_tree.column('スタッフ名', width=120, anchor=tk.W)
        for col in columns[1:]:
            self.request_tree.column(col, width=100, anchor=tk.CENTER)
        
        # ヘッダー設定
        for col in columns:
            self.request_tree.heading(col, text=col)
        
        # スタッフごとに行を追加
        if not self.staff_data:
            self.request_tree.insert('', tk.END, values=["(スタッフを登録してください)",] + [""] * days_in_month)
        else:
            for staff_name in sorted(self.staff_data.keys()):
                values = [staff_name]
                for day in range(1, days_in_month + 1):
                    date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
                    
                    # この日のシフト希望を取得
                    time_slot = ""
                    if date_str in self.shift_requests:
                        if staff_name in self.shift_requests[date_str]:
                            slots = self.shift_requests[date_str][staff_name]
                            time_slot = ", ".join(slots) if isinstance(slots, list) else slots
                    
                    values.append(time_slot)
                
                self.request_tree.insert('', tk.END, values=values)
    
    def update_requirement_table(self):
        """必要人数表を更新"""
        # 表をクリア
        for item in self.requirement_tree.get_children():
            self.requirement_tree.delete(item)
        
        # 月表示を更新
        self.month_label_requirement.config(text=f"{self.current_year}年{self.current_month}月")
        
        # カラム設定（日付列）
        days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]
        columns = ["時間帯"] + [f"{d}日" for d in range(1, days_in_month + 1)]
        
        self.requirement_tree['columns'] = columns
        self.requirement_tree['show'] = 'tree headings'
        
        # カラム幅設定
        self.requirement_tree.column('#0', width=0, stretch=tk.NO)
        self.requirement_tree.column('時間帯', width=120, anchor=tk.W)
        for col in columns[1:]:
            self.requirement_tree.column(col, width=80, anchor=tk.CENTER)
        
        # ヘッダー設定
        for col in columns:
            self.requirement_tree.heading(col, text=col)
        
        # すべての時間帯を収集
        time_slots = set()
        for date_reqs in self.requirements.values():
            time_slots.update(date_reqs.keys())
        
        if not time_slots:
            time_slots = ["09:00-13:00", "13:00-17:00", "17:00-21:00"]  # デフォルト
        
        # 時間帯ごとに行を追加
        for time_slot in sorted(time_slots):
            values = [time_slot]
            for day in range(1, days_in_month + 1):
                date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
                
                # この日の必要人数を取得
                count = ""
                if date_str in self.requirements:
                    if time_slot in self.requirements[date_str]:
                        count = str(self.requirements[date_str][time_slot])
                
                values.append(count)
            
            self.requirement_tree.insert('', tk.END, values=values)
    
    def on_request_cell_double_click(self, event):
        """シフト希望セルのダブルクリックイベント"""
        item = self.request_tree.selection()
        if not item:
            return
        
        # クリックされた列を特定
        column = self.request_tree.identify_column(event.x)
        if column == '#0' or column == '#1':  # スタッフ名列
            return
        
        # 列番号から日付を計算
        col_index = int(column.replace('#', '')) - 1
        if col_index < 1:
            return
        
        day = col_index
        date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
        
        # スタッフ名を取得
        values = self.request_tree.item(item[0])['values']
        staff_name = values[0]
        
        # 現在の値を取得
        current_value = values[col_index] if col_index < len(values) else ""
        
        # 入力ダイアログ
        new_value = simpledialog.askstring(
            "シフト希望入力",
            f"スタッフ: {staff_name}\n日付: {date_str}\n\n時間帯を入力してください\n（例: 09:00-13:00、複数ある場合はカンマ区切り）\n空欄で削除",
            initialvalue=current_value
        )
        
        if new_value is None:  # キャンセル
            return
        
        # データを更新
        if date_str not in self.shift_requests:
            self.shift_requests[date_str] = {}
        
        if new_value.strip():
            # 時間帯を保存（カンマ区切りをリストに変換）
            time_slots = [t.strip() for t in new_value.split(',') if t.strip()]
            self.shift_requests[date_str][staff_name] = time_slots
        else:
            # 空欄の場合は削除
            if staff_name in self.shift_requests[date_str]:
                del self.shift_requests[date_str][staff_name]
            if not self.shift_requests[date_str]:
                del self.shift_requests[date_str]
        
        # 表を更新
        self.update_request_table()
    
    def on_requirement_cell_double_click(self, event):
        """必要人数セルのダブルクリックイベント"""
        item = self.requirement_tree.selection()
        if not item:
            return
        
        # クリックされた列を特定
        column = self.requirement_tree.identify_column(event.x)
        if column == '#0' or column == '#1':  # 時間帯列
            return
        
        # 列番号から日付を計算
        col_index = int(column.replace('#', '')) - 1
        if col_index < 1:
            return
        
        day = col_index
        date_str = f"{self.current_year:04d}-{self.current_month:02d}-{day:02d}"
        
        # 時間帯を取得
        values = self.requirement_tree.item(item[0])['values']
        time_slot = values[0]
        
        # 現在の値を取得
        current_value = values[col_index] if col_index < len(values) else ""
        
        # 入力ダイアログ
        new_value = simpledialog.askstring(
            "必要人数入力",
            f"時間帯: {time_slot}\n日付: {date_str}\n\n必要人数を入力してください\n（空欄で削除）",
            initialvalue=current_value
        )
        
        if new_value is None:  # キャンセル
            return
        
        # データを更新
        if date_str not in self.requirements:
            self.requirements[date_str] = {}
        
        if new_value.strip():
            try:
                count = int(new_value.strip())
                self.requirements[date_str][time_slot] = count
            except ValueError:
                messagebox.showerror("エラー", "数値を入力してください")
                return
        else:
            # 空欄の場合は削除
            if time_slot in self.requirements[date_str]:
                del self.requirements[date_str][time_slot]
            if not self.requirements[date_str]:
                del self.requirements[date_str]
        
        # 表を更新
        self.update_requirement_table()
        
    # データ操作メソッド
    def add_staff(self):
        """スタッフを追加"""
        name = self.staff_name_entry.get().strip()
        max_hours = self.max_hours_entry.get().strip()
        
        if not name:
            messagebox.showwarning("警告", "スタッフ名を入力してください")
            return
        
        try:
            max_hours = int(max_hours) if max_hours else 40
        except ValueError:
            messagebox.showerror("エラー", "週最大勤務時間は数値で入力してください")
            return
        
        if name in self.staff_data:
            messagebox.showwarning("警告", "このスタッフは既に登録されています")
            return
        
        self.staff_data[name] = {"max_hours": max_hours}
        self.update_staff_list()
        
        self.staff_name_entry.delete(0, tk.END)
        self.max_hours_entry.delete(0, tk.END)
        messagebox.showinfo("成功", f"{name}を追加しました")
        
    def delete_staff(self):
        """選択したスタッフを削除"""
        selection = self.staff_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "削除するスタッフを選択してください")
            return
        
        staff_info = self.staff_listbox.get(selection[0])
        name = staff_info.split(" - ")[0]
        
        if messagebox.askyesno("確認", f"{name}を削除しますか？"):
            del self.staff_data[name]
            self.update_staff_list()
            self.update_staff_combo()
            
    def update_staff_list(self):
        """スタッフリストを更新"""
        self.staff_listbox.delete(0, tk.END)
        for name, data in sorted(self.staff_data.items()):
            self.staff_listbox.insert(tk.END, f"{name} - 週最大{data['max_hours']}時間")
        
        # 表も更新
        try:
            self.update_request_table()
        except:
            pass
            
    def update_staff_combo(self):
        """スタッフコンボボックスを更新"""
        # 削除（もう使わない）
        pass
    
    def add_shift_request(self):
        """シフト希望を追加"""
        # 削除（もう使わない）
        pass
        
    def delete_request(self):
        """選択したシフト希望を削除"""
        # 削除（もう使わない）
        pass
            
    def update_request_list(self):
        """シフト希望リストを更新"""
        # 削除（もう使わない）
        pass
                    
    def add_requirement(self):
        """必要人数を追加"""
        # 削除（もう使わない）
        pass
        
    def delete_requirement(self):
        """選択した必要人数設定を削除"""
        # 削除（もう使わない）
        pass
            
    def update_requirement_list(self):
        """必要人数リストを更新"""
        # 削除（もう使わない）
        pass
                
    def generate_shift(self):
        """シフトを生成"""
        if not self.staff_data:
            messagebox.showwarning("警告", "スタッフが登録されていません")
            return
        
        if not self.shift_requests:
            messagebox.showwarning("警告", "シフト希望が入力されていません")
            return
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "=" * 80 + "\n")
        self.result_text.insert(tk.END, "シフト表\n")
        self.result_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # 日付ごとにシフトを生成
        for date in sorted(self.shift_requests.keys()):
            self.result_text.insert(tk.END, f"【{date}】\n")
            self.result_text.insert(tk.END, "-" * 80 + "\n")
            
            # この日の希望を表示
            if date in self.shift_requests:
                for staff, time_slots in sorted(self.shift_requests[date].items()):
                    for slot in time_slots:
                        status = "✓"
                        self.result_text.insert(tk.END, f"  {status} {staff}: {slot}\n")
            
            # この日の必要人数を表示
            if date in self.requirements:
                self.result_text.insert(tk.END, "\n  必要人数:\n")
                for time_slot, count in sorted(self.requirements[date].items()):
                    # 実際に入った人数を計算
                    assigned = 0
                    if date in self.shift_requests:
                        for staff, slots in self.shift_requests[date].items():
                            for slot in slots:
                                if self.time_overlap(slot, time_slot):
                                    assigned += 1
                    
                    status_mark = "✓" if assigned >= count else "⚠"
                    self.result_text.insert(tk.END, f"  {status_mark} {time_slot}: {assigned}/{count}人\n")
            
            self.result_text.insert(tk.END, "\n")
        
        messagebox.showinfo("完了", "シフトを生成しました")
        
    def time_overlap(self, slot1: str, slot2: str) -> bool:
        """2つの時間帯が重なっているかチェック"""
        try:
            # 簡易的な実装：完全一致または包含関係をチェック
            return slot1 == slot2 or slot1 in slot2 or slot2 in slot1
        except:
            return False
            
    def export_csv(self):
        """CSVファイルに出力"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["日付", "スタッフ名", "時間帯"])
                
                for date in sorted(self.shift_requests.keys()):
                    for staff, time_slots in sorted(self.shift_requests[date].items()):
                        for slot in time_slots:
                            writer.writerow([date, staff, slot])
            
            messagebox.showinfo("成功", f"CSVファイルを保存しました:\n{filename}")
        except Exception as e:
            messagebox.showerror("エラー", f"CSV出力中にエラーが発生しました:\n{e}")
            
    def save_data(self):
        """データをJSONファイルに保存"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            data = {
                "staff_data": self.staff_data,
                "shift_requests": self.shift_requests,
                "requirements": self.requirements
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"データを保存しました:\n{filename}")
        except Exception as e:
            messagebox.showerror("エラー", f"保存中にエラーが発生しました:\n{e}")
            
    def load_data(self):
        """JSONファイルからデータを読み込み"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.staff_data = data.get("staff_data", {})
            self.shift_requests = data.get("shift_requests", {})
            self.requirements = data.get("requirements", {})
            
            self.update_staff_list()
            self.update_staff_combo()
            self.update_request_list()
            self.update_requirement_list()
            
            messagebox.showinfo("成功", f"データを読み込みました:\n{filename}")
        except Exception as e:
            messagebox.showerror("エラー", f"読み込み中にエラーが発生しました:\n{e}")


def main():
    root = tk.Tk()
    app = ShiftTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
