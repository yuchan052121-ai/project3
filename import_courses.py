import pandas as pd
import sqlite3
import os
import re

# 設定
DB_FILE = "reviews.db"
KEYWORD_FILE = "キーワード_拡大版_社会工学類.csv" 
SYLLABUS_FILE = "kdb_20251220100333_社会工学類.csv"

def rebuild_and_import():
    # 1. 既存DBの削除（Flaskが動いていると失敗するので注意）
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"既存の {DB_FILE} を削除しました。")
        except PermissionError:
            print("エラー: reviews.db が使用中です。Flaskを止めて（Ctrl+C）から再実行してください。")
            return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # 2. テーブル作成（yearを文字列としても受け入れられるよう柔軟に設定）
    cur.execute("""
        CREATE TABLE courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            title TEXT,
            area TEXT,
            year INTEGER,
            semester TEXT,
            schedule TEXT,
            credits REAL
        )
    """)
    cur.execute("""
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER,
            user_id TEXT,
            difficulty INTEGER,
            recommend INTEGER,
            attendance_required INTEGER,
            assessment TEXT,
            comment TEXT,
            created_at TIMESTAMP,
            active INTEGER DEFAULT 1
        )
    """)
    print("テーブルの作成が完了しました。")

    try:
        # 3. データの読み込みと「nan」の一括除去
        # キーワードファイル
        df_kw = pd.read_csv(KEYWORD_FILE, encoding='utf-8')
        df_kw.columns = [c.strip() for c in df_kw.columns]
        if '科目名' in df_kw.columns:
            df_kw = df_kw.rename(columns={'科目名': '授業科目名'})
        
        # シラバスファイル（5行目からデータが始まる想定）
        df_syllabus = pd.read_csv(SYLLABUS_FILE, encoding='utf-8', skiprows=4)
        df_syllabus.columns = [c.strip() for c in df_syllabus.columns]
        
        # --- ここが重要：nanを一括で空文字に変換 ---
        df_syllabus = df_syllabus.fillna('')
        
        # 列名の名寄せ
        if '科目名' in df_syllabus.columns:
            df_syllabus = df_syllabus.rename(columns={'科目名': '授業科目名'})
        
        # 「標準履修」という列名の場合があるため「標準履修年次」に統一
        if '標準履修' in df_syllabus.columns and '標準履修年次' not in df_syllabus.columns:
            df_syllabus = df_syllabus.rename(columns={'標準履修': '標準履修年次'})

        # 4. 統合（キーワードにある授業だけをDBに入れる）
        df_integrated = pd.merge(
            df_kw[['授業科目名']], 
            df_syllabus,
            on='授業科目名', 
            how='left'
        ).drop_duplicates(subset=['授業科目名'])

        # 5. DBへの挿入ループ
        for _, row in df_integrated.iterrows():
            # 年次の抽出ロジック（"1・2" などの表記から最初の数字だけ取る）
            year_raw = str(row.get('標準履修年次', ''))
            year_match = re.search(r'\d', year_raw)
            year_val = int(year_match.group()) if year_match else None
            
            # 補助関数：個別の値に対しても念のためnan除去をかける
            def clean_str(val):
                s = str(val).strip()
                return "" if s.lower() == 'nan' or s == 'none' else s
            
            cur.execute("""
                INSERT OR IGNORE INTO courses (code, title, area, year, semester, schedule, credits)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                clean_str(row.get('科目番号')), 
                row['授業科目名'], 
                "社会工学類",
                year_val,
                clean_str(row.get('実施学期')), 
                clean_str(row.get('曜時限')), 
                row.get('単位数', 0)
            ))
            
        conn.commit()
        print(f"インポート成功: {len(df_integrated)}件の授業をDBに登録しました。")
        
    except Exception as e:
        print(f"実行中にエラーが発生しました: {e}")
    finally:
        conn.close()

rebuild_and_import()