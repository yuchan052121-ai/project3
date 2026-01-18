import pandas as pd
import sqlite3

DB = "reviews.db"
EXCEL = "社会工学類授業_df.xlsx"

def import_excel():
    df = pd.read_excel(EXCEL)

    # 列名チェック
    required_cols = ["授業科目名", "科目番号", "標準履修年次", "時間割", "専攻区分"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Excelに列 {col} がありません")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    for _, row in df.iterrows():
        try:
            c.execute("""
                INSERT OR IGNORE INTO courses
                (code, title, year, schedule, area)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(row["科目番号"]).strip(),
                str(row["授業科目名"]).strip(),
                str(row["標準履修年次"]).strip(),
                str(row["時間割"]).strip(),
                str(row["専攻区分"]).strip()
            ))
        except Exception as e:
            print("Error:", e)

    conn.commit()
    conn.close()
    print("Excel import finished")

if __name__ == "__main__":
    import_excel()
