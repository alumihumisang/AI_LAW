"""
prepare_lawyer_input_6057.py
切分並合併6057筆律師輸入（2995 + 3062）

輸入：
  - 09_輸入輸出資料/整合_模擬律師輸入_2995.xlsx
  - 09_輸入輸出資料/3062律師輸入.xlsx

輸出：
  - 09_輸入輸出資料/整合_律師輸入_6057_三段切分.xlsx
"""

import pandas as pd
import re

def split_lawyer_input_three_sections(text):
    """
    切分律師輸入為三段

    Returns:
        dict: {
            "AccidentCause": "事故發生緣由內容",
            "InjuryDescription": "原告受傷情形內容",
            "CompensationBasis": "請求賠償的事實根據內容"
        }
    """
    if pd.isna(text):
        return {
            "AccidentCause": "",
            "InjuryDescription": "",
            "CompensationBasis": ""
        }

    text = str(text)

    # 找到三個段落的位置
    match_1 = re.search(r'一、', text)
    match_2 = re.search(r'二、', text)
    match_3 = re.search(r'三、', text)

    result = {
        "AccidentCause": "",
        "InjuryDescription": "",
        "CompensationBasis": ""
    }

    # 如果找不到基本結構，返回空
    if not match_1:
        return result

    # 提取第一段（從「一、」到「二、」之前）
    if match_2:
        result["AccidentCause"] = text[match_1.end():match_2.start()].strip()
    else:
        result["AccidentCause"] = text[match_1.end():].strip()
        return result

    # 提取第二段（從「二、」到「三、」之前）
    if match_3:
        result["InjuryDescription"] = text[match_2.end():match_3.start()].strip()
    else:
        result["InjuryDescription"] = text[match_2.end():].strip()
        return result

    # 提取第三段（從「三、」到結尾）
    result["CompensationBasis"] = text[match_3.end():].strip()

    return result


def process_2995():
    """處理2995筆律師輸入"""
    print("=" * 70)
    print(" 處理 2995 筆律師輸入")
    print("=" * 70)

    file_path = "09_輸入輸出資料/整合_模擬律師輸入_2995.xlsx"
    df = pd.read_excel(file_path)

    print(f"\n📊 讀取: {len(df)} 筆")
    print(f"📋 欄位: {list(df.columns)}")

    results = []

    for idx, row in df.iterrows():
        if idx % 500 == 0:
            print(f"  處理中... {idx}/{len(df)}")

        case_id = row["case_id"]
        full_text = row["律師輸入"] if pd.notna(row["律師輸入"]) else ""

        # 切分三段
        sections = split_lawyer_input_three_sections(full_text)

        results.append({
            "case_id": case_id,
            "律師輸入": full_text,
            "一、事故發生緣由": sections["AccidentCause"],
            "二、原告受傷情形": sections["InjuryDescription"],
            "三、請求賠償的事實根據": sections["CompensationBasis"]
        })

    df_result = pd.DataFrame(results)

    # 統計
    print(f"\n📊 切分統計:")
    print(f"  有「一、」內容: {(df_result['一、事故發生緣由'].str.len() > 10).sum()} 筆")
    print(f"  有「二、」內容: {(df_result['二、原告受傷情形'].str.len() > 10).sum()} 筆")
    print(f"  有「三、」內容: {(df_result['三、請求賠償的事實根據'].str.len() > 10).sum()} 筆")

    return df_result


def process_3062():
    """處理3062筆律師輸入"""
    print("\n" + "=" * 70)
    print(" 處理 3062 筆律師輸入")
    print("=" * 70)

    file_path = "09_輸入輸出資料/3062律師輸入.xlsx"
    df = pd.read_excel(file_path)

    print(f"\n📊 讀取: {len(df)} 筆")
    print(f"📋 欄位: {list(df.columns)}")

    results = []

    for idx, row in df.iterrows():
        if idx % 500 == 0:
            print(f"  處理中... {idx}/{len(df)}")

        case_id = row["case_id"]
        full_text = row["律師輸入"] if pd.notna(row["律師輸入"]) else ""

        # 切分三段
        sections = split_lawyer_input_three_sections(full_text)

        results.append({
            "case_id": case_id,
            "律師輸入": full_text,
            "一、事故發生緣由": sections["AccidentCause"],
            "二、原告受傷情形": sections["InjuryDescription"],
            "三、請求賠償的事實根據": sections["CompensationBasis"]
        })

    df_result = pd.DataFrame(results)

    # 統計
    print(f"\n📊 切分統計:")
    print(f"  有「一、」內容: {(df_result['一、事故發生緣由'].str.len() > 10).sum()} 筆")
    print(f"  有「二、」內容: {(df_result['二、原告受傷情形'].str.len() > 10).sum()} 筆")
    print(f"  有「三、」內容: {(df_result['三、請求賠償的事實根據'].str.len() > 10).sum()} 筆")

    return df_result


if __name__ == "__main__":
    print("=" * 70)
    print(" 合併6057筆律師輸入（三段切分）")
    print("=" * 70)

    # 處理2995
    df_2995 = process_2995()

    # 處理3062
    df_3062 = process_3062()

    # 合併
    print("\n" + "=" * 70)
    print(" 合併2995 + 3062")
    print("=" * 70)

    df_6057 = pd.concat([df_2995, df_3062], ignore_index=True)

    print(f"\n📊 合併結果:")
    print(f"  總筆數: {len(df_6057)}")
    print(f"  case_id範圍: {df_6057['case_id'].min()} ~ {df_6057['case_id'].max()}")

    # 最終統計
    print(f"\n📊 最終統計:")
    for col in ['一、事故發生緣由', '二、原告受傷情形', '三、請求賠償的事實根據']:
        count = (df_6057[col].notna() & (df_6057[col].str.len() > 10)).sum()
        print(f"  {col}: {count} / {len(df_6057)} 筆有內容")

    # 儲存
    output_file = "09_輸入輸出資料/整合_律師輸入_6057_三段切分.xlsx"
    df_6057.to_excel(output_file, index=False)
    print(f"\n✅ 已儲存: {output_file}")

    print("\n" + "=" * 70)
    print(" 完成！")
    print("=" * 70)
    print(f"\n下一步：")
    print(f"  1. 檢查輸出檔案確認切分正確")
    print(f"  2. 刪除Neo4j中舊的LawyerInput節點（2995筆）")
    print(f"  3. 執行新的KG_500v2腳本導入6057筆（三段結構）")
