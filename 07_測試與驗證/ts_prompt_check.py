# ts_prompt_check.py
# This file contains all quality check prompts used in the retrieval system

# Fact quality check prompt
def get_fact_quality_check_prompt(generated_fact, summary):
    return f"""請評估生成的事故事實段落是否與摘要一致，並檢查是否遺漏重要資訊。

    摘要：
    {summary}

    生成的事故事實段落：
    {generated_fact}

    評估標準：
    1. 輸入跟摘要內容是否一致，如事故緣由，受傷情形等資訊
    2. 是否遺漏任何重要資訊
    3. 是否符合法律文書的格式和語言要求
    4. 是否包含摘要中的所有關鍵要素
    5. 不可包含赔偿金

    請僅回答 "pass" 或 "fail"，並提供簡短的理由。格式：
    [結果]: [pass/fail]
    [理由]: [簡短說明為何通過或失敗]
    """

def get_law_content_check_prompt(accident_facts, injuries, law_number, law_content):
    return f"""請評估以下法條是否適用於給定的案件事實與受傷情形。

案件事實：
{accident_facts}

受傷情形：
{injuries}

法條：
第{law_number}條：{law_content}

評估標準：
1. 法條內容是否與案件事實相關
2. 法條是否適用於描述的侵權行為或受傷情形
3. 是否有明確的法律適用基礎

請僅回答 "pass" 或 "fail"，並提供簡短的理由。格式：
[結果]: [pass/fail]
[理由]: [簡短說明為何通過或失敗]
"""

def get_compensation_part1_check_prompt(compensation_part1, injuries, compensation_facts, plaintiffs_info):
    plaintiff_text = f"原告資訊：{plaintiffs_info}\n\n" if plaintiffs_info else ""
    return f"""請評估生成的賠償請求第一部分是否與傷情資訊和損失情況一致，並檢查是否遺漏重要資訊。

{plaintiff_text}
受傷情形：
{injuries}

損失情況：
{compensation_facts}

生成的賠償請求第一部分：
{compensation_part1}

評估標準：
1. 是否包含所有原告的賠償項目（如果有多位原告）
2. 賠償項目是否與傷情資訊和損失情況一致
3. 是否遺漏任何重要的賠償項目
4. 賠償項目要有金額，并非僅是描述
5. 不包含總結，評語，分析，及建議等等(嚴格檢查此項)

請僅回答 "pass" 或 "fail"，並提供簡短的理由。格式：
[結果]: [pass/fail]
[理由]: [簡短說明為何通過或失敗]
"""


# Add this to ts_prompt_check.py
def get_calculation_tags_check_prompt(compensation_part1, compensation_part2):
    return f"""請評估生成的計算標籤是否完整涵蓋所有賠償項目。

評估標準:
1. 是否為每位原告生成一個計算標籤
2. 標籤中的金額是否與賠償項目中的金額一致
3. 計算標籤格式是否正確 (<calculate>原告名稱/代稱 金額1 金額2 金額3</calculate>)，代稱可以是"default"
4. 標籤內是否只包含數字，不包含文字描述、加號、等號、逗號或其他分隔符
5. 一位原告只能有一個標簽，多個原告則多個標簽

賠償項目:
{compensation_part1}

生成的計算標籤:
{compensation_part2}


請僅回答 "pass" 或 "fail"，並提供簡短的理由。格式：
[結果]: [pass/fail]
[理由]: [簡短說明為何通過或失敗]
"""