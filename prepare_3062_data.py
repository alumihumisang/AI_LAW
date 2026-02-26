"""
處理3062筆新資料，轉換成KG_100-500所需格式
"""
import pandas as pd
import re

def split_indictment_by_numbers(text):
    """
    精確切分起訴書 (3062筆新資料格式)

    規則：
    1. 事實概述：從第一個"一、"開始 → 到"二、"之前
    2. 法條引用：從"二、"開始 → 到第一個左括號(或（)之前
    3. 損害賠償項目：從第一個左括號開始 → 到"綜上所陳"或"綜上所述"之前
    4. 結論：從"綜上所陳"或"綜上所述"開始 → 到結尾
    """
    sections = {
        "事實概述": "",
        "法條引用": "",
        "損害賠償項目": "",
        "結論": ""
    }

    # 1. 找到"一、"的位置
    match_one = re.search(r'一、', text)
    if not match_one:
        # 沒有"一、"，整段放事實
        sections["事實概述"] = text
        return sections

    # 2. 找到"二、"的位置
    match_two = re.search(r'二、', text)
    if not match_two:
        # 沒有"二、"，從"一、"到結尾都是事實
        sections["事實概述"] = text[match_one.start():]
        return sections

    # 事實概述：從"一、"開始到"二、"之前
    sections["事實概述"] = text[match_one.start():match_two.start()].strip()

    # 3. 找到第一個左括號（全形或半形）的位置（在"二、"之後）
    text_after_two = text[match_two.start():]
    match_bracket = re.search(r'[（(]', text_after_two)

    if not match_bracket:
        # 沒有找到左括號，"二、"到結尾都是法條
        sections["法條引用"] = text_after_two.strip()
        return sections

    # 法條引用：從"二、"開始到第一個左括號之前
    sections["法條引用"] = text_after_two[:match_bracket.start()].strip()

    # 4. 找到"綜上所陳"或"綜上所述"的位置
    text_after_bracket = text_after_two[match_bracket.start():]
    match_conclusion = re.search(r'(綜上所陳|綜上所述)', text_after_bracket)

    if not match_conclusion:
        # 沒有找到結論標記，從左括號到結尾都是賠償
        sections["損害賠償項目"] = text_after_bracket.strip()
        return sections

    # 5. 找到"綜上所陳/述"之前的最後一個左括號
    # 這個左括號到"綜上所陳/述"之間的題號要刪除，不放在任何欄位中
    text_before_conclusion = text_after_bracket[:match_conclusion.start()]
    last_bracket_before_conclusion = None
    for match in re.finditer(r'[（(]', text_before_conclusion):
        last_bracket_before_conclusion = match

    if last_bracket_before_conclusion:
        # 損害賠償項目：從第一個左括號到"綜上"前面的最後一個題號之前
        sections["損害賠償項目"] = text_after_bracket[:last_bracket_before_conclusion.start()].strip()

        # 結論：直接從"綜上所陳/述"開始（刪掉中間的題號）
        sections["結論"] = text_after_bracket[match_conclusion.start():].strip()
    else:
        # 找不到"綜上"前的左括號，直接在"綜上"處切分
        sections["損害賠償項目"] = text_before_conclusion.strip()
        sections["結論"] = text_after_bracket[match_conclusion.start():].strip()

    return sections

def split_lawyer_input(text):
    """
    從律師輸入提取緣由和後果

    假設格式：
    一、事故發生緣由: [內容]
    二、原告受傷情形: [內容]
    或其他變體
    """
    # 嘗試用「一、二、」分段
    parts = re.split(r'[一二三四]、', text)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 2:
        return {
            "緣由": parts[0],
            "後果": parts[1] if len(parts) > 1 else ""
        }
    else:
        # fallback: 整段都是緣由
        return {
            "緣由": text,
            "後果": ""
        }

def process_indictment_file(input_file, output_file):
    """處理起訴書檔案"""
    print(f"\n📂 處理起訴書: {input_file}")

    df = pd.read_excel(input_file)
    print(f"📊 筆數: {len(df)}")

    results = []

    for idx, row in df.iterrows():
        if idx % 100 == 0:
            print(f"  處理中... {idx}/{len(df)}")

        case_id = row["case_id"]
        full_text = row["Indictment Response"] if pd.notna(row["Indictment Response"]) else ""

        # 切分成四段
        sections = split_indictment_by_numbers(full_text)

        results.append({
            "case_id": case_id,
            "事實概述": sections["事實概述"],
            "法條引用": sections["法條引用"],
            "損害賠償項目": sections["損害賠償項目"],
            "結論": sections["結論"]
        })

    df_output = pd.DataFrame(results)
    df_output.to_excel(output_file, index=False)
    print(f"✅ 已儲存: {output_file}")

    # 統計
    print(f"\n📊 統計資訊:")
    print(f"  - 有事實概述: {(df_output['事實概述'].str.len() > 10).sum()} 筆")
    print(f"  - 有法條引用: {(df_output['法條引用'].str.len() > 10).sum()} 筆")
    print(f"  - 有損害賠償: {(df_output['損害賠償項目'].str.len() > 10).sum()} 筆")
    print(f"  - 有結論: {(df_output['結論'].str.len() > 10).sum()} 筆")

    return df_output

def process_lawyer_input_file(input_file, output_file):
    """處理律師輸入檔案"""
    print(f"\n📂 處理律師輸入: {input_file}")

    df = pd.read_excel(input_file)
    print(f"📊 筆數: {len(df)}")

    results = []

    for idx, row in df.iterrows():
        if idx % 100 == 0:
            print(f"  處理中... {idx}/{len(df)}")

        case_id = row["case_id"]
        full_text = row["律師輸入"] if pd.notna(row["律師輸入"]) else ""

        # 切分成緣由和後果
        parts = split_lawyer_input(full_text)

        results.append({
            "case_id": case_id,
            "律師輸入": full_text,
            "緣由": parts["緣由"],
            "後果": parts["後果"]
        })

    df_output = pd.DataFrame(results)
    df_output.to_excel(output_file, index=False)
    print(f"✅ 已儲存: {output_file}")

    # 統計
    print(f"\n📊 統計資訊:")
    print(f"  - 有律師輸入: {(df_output['律師輸入'].str.len() > 10).sum()} 筆")
    print(f"  - 有緣由: {(df_output['緣由'].str.len() > 10).sum()} 筆")
    print(f"  - 有後果: {(df_output['後果'].str.len() > 10).sum()} 筆")

    return df_output

if __name__ == "__main__":
    print("=" * 70)
    print(" 處理3062筆新資料")
    print("=" * 70)

    # 處理起訴書
    df_indictment = process_indictment_file(
        "09_輸入輸出資料/3062起訴書.xlsx",
        "09_輸入輸出資料/整合_起訴書_3062_已切分.xlsx"
    )

    # 處理律師輸入
    df_lawyer = process_lawyer_input_file(
        "09_輸入輸出資料/3062律師輸入.xlsx",
        "09_輸入輸出資料/整合_律師輸入_3062_已切分.xlsx"
    )

    print("\n" + "=" * 70)
    print(" 完成！生成的檔案：")
    print("=" * 70)
    print("1. 整合_起訴書_3062_已切分.xlsx")
    print("2. 整合_律師輸入_3062_已切分.xlsx")
    print("\n請檢查這兩個檔案，確認切分結果無誤後再執行KG_100-500")
    print("=" * 70)
