# KG_700_v9_FormatTester_Full.py

import pandas as pd
from KG_700_BatchSemanticSearcher_v7_for_excel import process_query
import re
from collections import defaultdict

# 格式清理模組 v1
def format_cleaner(text: str) -> str:
    cleaned = text

    # 1️⃣ 段標重複去除
    cleaned = re.sub(r'(一、事實概述：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(二、法律依據：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(三、損害項目：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(四、結論：)\s*\1+', r'\1', cleaned)

    # 2️⃣ 金額千分位格式化
    def money_formatter(match):
        num = match.group(1).replace(",", "")
        try:
            formatted = "{:,}".format(int(num))
            return f"{formatted}元"
        except:
            return match.group(0)

    cleaned = re.sub(r'(\d{4,})元', money_formatter, cleaned)

    # 3️⃣ 移除多餘重複標題
    cleaned = re.sub(r'(事實概述：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(法律依據：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(損害項目：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(結論：)\s*\1+', r'\1', cleaned)

    # 4️⃣ 清理多餘空行
    cleaned = re.sub(r'\n+', '\n', cleaned).strip()

    return cleaned

# 加總模組 v2：容錯版
def sum_compensation_totals_v2(cleaned_text: str) -> str:
    match = re.search(r"三、損害項目：(.*?)四、結論：", cleaned_text, re.S)
    if not match:
        return "⚠ 無法擷取損害項目段落，無法計算總金額。"

    compensation_block = match.group(1)
    items = re.split(r'[\（(][一二三四五六七八九十]+[\）)]', compensation_block)
    items = [item.strip() for item in items if item.strip()]

    plaintiff_totals = defaultdict(int)
    plaintiff_items = defaultdict(list)

    for item_text in items:
        name_match = re.search(r"(林肜宇|吳彩雲)", item_text)
        if not name_match:
            continue
        plaintiff_name = name_match.group(1)

        amount_matches = re.findall(r'([\d,]+)元', item_text)
        if not amount_matches:
            continue

        final_amount_str = amount_matches[-1].replace(",", "")
        try:
            amount = int(final_amount_str)
        except:
            continue

        item_title_match = re.search(r'^[：:、]?(.*?費用|慰撫金|休業損失|交通費|修復費|工作損失)', item_text)
        if item_title_match:
            item_title = item_title_match.group(1)
        else:
            item_title = "損害項目"

        plaintiff_totals[plaintiff_name] += amount
        plaintiff_items[plaintiff_name].append((item_title.strip(), amount))

    result_lines = []
    grand_total = 0

    for plaintiff, total in plaintiff_totals.items():
        items_text = "、".join([
            f"{item_name}{amount:,}元" for item_name, amount in plaintiff_items[plaintiff]
        ])
        result_lines.append(
            f"被告應賠償原告{plaintiff}之損害，包含{items_text}，總計{total:,}元。"
        )
        grand_total += total

    if len(plaintiff_totals) > 1:
        result_lines.append(
            f"兩原告之請求金額合計{grand_total:,}元，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。"
        )
    else:
        result_lines.append(
            f"請求總計{grand_total:,}元，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。"
        )

    return "\n".join(result_lines)


# 讀取你測試用的 Excel 律師輸入
df = pd.read_excel("2995_測試用50筆_2025.6.xlsx", sheet_name="Sheet1")

# 先挑要測試的單筆
sample_row = df.iloc[18]  # <— 你可自行修改不同筆數測試

query_text = sample_row["律師輸入"]

# 單筆執行完整流程
result_text = process_query(query_text, return_text=True)
cleaned_result = format_cleaner(result_text)

print("====== 清理前 ======")
print(result_text)
print("====== 清理後 ======")
print(cleaned_result)

# 執行加總模組 v2
summary_result = sum_compensation_totals_v2(cleaned_result)
print("====== 自動加總結論段 (V2容錯版) ======")
print(summary_result)
