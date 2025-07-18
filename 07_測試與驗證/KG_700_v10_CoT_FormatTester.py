import pandas as pd
from KG_700_BatchSemanticSearcher_v7_for_excel import process_query
import re
from collections import defaultdict
import requests
import json
import time

# 角色辨識模組 v9（保留）
def extract_parties_v9(user_query: str) -> dict:
    result = {"原告": set(), "被告": set()}
    match = re.search(r"一[、.． ]?事故發生緣由[:：]?\s*(.*?)(二|$)", user_query, re.S)
    incident_text = match.group(1) if match else user_query
    patterns = [
        (r"原告[、:：]?\s*([^\n，。；、 ]+)", "原告"),
        (r"被告[、:：]?\s*([^\n，。；、 ]+)", "被告"),
        (r"查被告\s*([^\n，。；、 ]+)", "被告"),
    ]
    for pattern, role in patterns:
        for m in re.finditer(pattern, incident_text):
            name = m.group(1).strip()
            if name and len(name) > 1:
                result[role].add(name)
    if not result["原告"]:
        if "原告" in incident_text:
            result["原告"].add("原告")
    if not result["被告"]:
        if "被告" in incident_text:
            result["被告"].add("被告")
    return {
        "原告": "、".join(sorted(result["原告"])) if result["原告"] else "未提及",
        "被告": "、".join(sorted(result["被告"])) if result["被告"] else "未提及",
        "原告數量": len(result["原告"]),
        "被告數量": len(result["被告"])
    }

# 格式清理模組 (升級版)
def format_cleaner(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r'(一、事實概述：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(二、法律依據：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(三、損害項目：)', '三、損害賠償項目：', cleaned)
    cleaned = re.sub(r'(三、損害賠償項目：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(四、結論：)\s*\1+', r'\1', cleaned)
    cleaned = re.sub(r'(二、)\s*\n\s*(二、法律依據：)', r'\2', cleaned)
    cleaned = re.sub(r"精神賠償金", "慰撫金", cleaned)
    cleaned = re.sub(r"精神損害賠償", "慰撫金", cleaned)
    cleaned = re.sub(r'(\d{4,})元', lambda m: "{:,}元".format(int(m.group(1).replace(",", ""))), cleaned)
    cleaned = re.sub(r'\n+', '\n', cleaned).strip()
    return cleaned

# Hybrid Law Filter v2 (角色數量補強)
def hybrid_law_filter(base_laws: list, parties: dict) -> list:
    laws = set(base_laws)
    if parties["被告數量"] > 1:
        laws.add("民法第185條")  # 數人共同侵權
    return sorted(laws)

# 法律依據段落插入模組 (新增)
def update_law_section(cleaned_result: str, final_laws: list) -> str:
    new_law_section = f"二、法律依據：按「{'」、「'.join(final_laws)}」分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任："
    updated = re.sub(r"(二、法律依據：).*?(?=三、損害賠償項目：)", f"{new_law_section}\n\n", cleaned_result, flags=re.S)
    return updated

# CoT 版加總模組（強化版）
def cot_sum_v2(compensation_text: str) -> str:
    cot_prompt = f"""
請依照下列損害項目，列出每項金額，進行精確加總（請使用計算式），最後產出正式法律結論段：
- 金額格式皆為阿拉伯數字，禁止中文數字
- 僅輸出最終結論段文字，前置計算可保留作驗算參考

=== 損害項目條列 ===
{compensation_text}
"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma3:27b", "prompt": cot_prompt, "stream": False}
    )
    return response.json()["response"].strip() if response.ok else "❌ LLM請求失敗"

# 結論覆寫拼接模組（修正版）
def replace_conclusion_with_cot(cleaned_result: str, cot_result: str) -> str:
    match_cot = re.search(r"(綜上所(?:述|陳).*)", cot_result, re.S)
    if not match_cot:
        print("⚠ 無法擷取 CoT 結論句子，無法覆寫")
        return cleaned_result
    new_conclusion = match_cot.group(1).strip()

    match_original = re.search(r"(一、事實概述：.*?)(二、法律依據：.*?)(三、損害賠償項目：.*?)(四、結論：)(.*)", cleaned_result, re.S)
    if not match_original:
        print("⚠ 無法拆解起訴書四段格式")
        return cleaned_result

    part1 = match_original.group(1).strip()
    part2 = match_original.group(2).strip()
    part3 = match_original.group(3).strip()
    part4_header = match_original.group(4).strip()

    merged = f"{part1}\n\n{part2}\n\n{part3}\n\n{part4_header} {new_conclusion}"
    return merged

# 讀入資料
df = pd.read_excel("2995_測試用50筆_2025.6.xlsx", sheet_name="Sheet1")
sample_row = df.iloc[18]
query_text = sample_row["律師輸入"]

# 角色判定
parties = extract_parties_v9(query_text)
print("【角色辨識】 原告:", parties["原告"], "｜被告:", parties["被告"])

# 呼叫主 pipeline (保留你原本process_query)
result_text = process_query(query_text, return_text=True)
cleaned_result = format_cleaner(result_text)
print("====== KG_700 v11 清理後 ======")
print(cleaned_result)

# Hybrid 法條補強示範
base_laws = ["民法第184條第1項前段", "民法第191-2條", "民法第193條第1項", "民法第195條第1項前段"]
final_laws = hybrid_law_filter(base_laws, parties)
print("====== 補強後法條適用清單 ======")
print(final_laws)

# 插入補強後法條進入二、法律依據段落
updated_result = update_law_section(cleaned_result, final_laws)

# COT 加總測試
match = re.search(r"三、損害賠償項目：(.*?)四、結論：", updated_result, re.S)
if match:
    compensation_block = match.group(1)
    cot_result = cot_sum_v2(compensation_block)
    print("====== COT加總結果 ======")
    print(cot_result)
    final_result = replace_conclusion_with_cot(updated_result, cot_result)
    print("====== 拼接後完整起訴書 ======")
    print(final_result)
else:
    print("⚠ 無法擷取三段損害項目")
