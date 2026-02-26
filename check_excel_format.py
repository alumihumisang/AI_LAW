"""
檢查Excel檔案的欄位結構
"""
import pandas as pd
import sys

if len(sys.argv) < 2:
    print("使用方式: python check_excel_format.py <excel檔案路徑>")
    sys.exit(1)

file_path = sys.argv[1]

try:
    # 讀取第一個sheet
    df = pd.read_excel(file_path, nrows=2)

    print(f"\n📂 檔案: {file_path}")
    print(f"📊 筆數: {len(pd.read_excel(file_path))}")
    print(f"\n欄位列表 ({len(df.columns)}個):")
    print("="*60)

    for i, col in enumerate(df.columns, 1):
        # 顯示範例值
        sample = df[col].iloc[0] if not pd.isna(df[col].iloc[0]) else "(空值)"
        if isinstance(sample, str) and len(sample) > 50:
            sample = sample[:50] + "..."
        print(f"{i:2d}. {col:30s} | 範例: {sample}")

    print("="*60)

    # 檢查KG_100-500需要的欄位
    print("\n✅ KG腳本所需欄位檢查:")
    required_fields = {
        "KG_100": ["case_id", "事實概述", "法條引用", "損害賠償項目", "結論"],
        "KG_500": ["case_id", "律師輸入", "緣由", "後果"]
    }

    for script, fields in required_fields.items():
        print(f"\n  {script}:")
        for field in fields:
            if field in df.columns:
                print(f"    ✅ {field}")
            else:
                print(f"    ❌ {field} (缺少)")

except Exception as e:
    print(f"❌ 錯誤: {e}")
