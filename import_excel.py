import sqlite3
import pandas as pd

# ===== 設定 =====
EXCEL_PATH = "社会工学類授業_df.xlsx"   # Excelファイル名
DB_PATH = "reviews.db"                  # project3 のDB
SHEET_NAME = 0                           # 0なら最初のシート

# ===== Excel 読み込み =====
df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

# 列名を確認（デバッグ用）
print("Excel columns:", df.columns.tolist())

# ===== 必要な列だけ取り出す =====
df = df[[
    "授業科目名",
    "科目番号",
    "標準履修年次",
    "時間割",
    "専攻区分"
]]

# ===== 列名をDB用に変更 =====
df = df.rename(columns={
    "授業科目名": "title",
    "科目番号": "code",
    "標準履修年次": "year",
    "時間割": "schedule",
    "専攻区分": "area"
})

# NaN → 空文字
df = df.fillna("")

# ===== SQLite に接続 =====
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ===== 1行ずつ INSERT =====
inserted = 0
skipped = 0

for _, row in df.iterrows():
    try:
        cur.execute("""
            INSERT INTO courses (code, title, area, year, schedule)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(row["code"]).strip(),
            row["title"].strip(),
            row["area"].strip(),
            row["year"].strip(),
            row["schedule"].strip()
        ))
        inserted += 1
    except sqlite3.IntegrityError:
        # code（科目番号）が重複したらスキップ
        skipped += 1

conn.commit()
conn.close()

print(f"完了: {inserted} 件追加, {skipped} 件スキップ")
