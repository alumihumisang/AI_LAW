# ts_prompt.py
# This file contains all prompts used in the retrieval system

# Facts generation prompt
def get_facts_prompt(accident_facts, fact_text_reference):
    return f"""你是一個台灣原告律師，你現在要幫忙完成車禍起訴狀裏的案件事實陳述的部分，你只需要根據下列格式進行輸出，並確保每個段落內容完整** 禁止輸出格式以外的任何東西 **： 
            一、事實概述：完整描述事故經過，案件過程盡量越詳細越好，要使用"緣被告"做開頭，並且在這段中都要以"原告""被告"作人物代稱，如果我給你的案件事實中沒有出現原告或被告的姓名，則請直接使用"原告""被告"作為代稱，請絕對不要自己憑空杜撰被告的姓名 
            備註:請記得在"事實概述"前面加上"一、", 把這部分以一段就完成，不要空行 ** 禁止輸出格式以外的任何東西 **   
            
            ###  案件事實：  {accident_facts}
            
            ### 參考案件格式（僅供格式參考，不要使用其內容）： {fact_text_reference}"""


#及其對原告生活工作的影響
# Single plaintiff compensation prompt template
def get_compensation_prompt_part1_single_plaintiff(injuries, compensation_facts, average_compensation=None, plaintiffs_info=""):
    avg_compensation_text = f"請注意：類似案件的平均賠償金額為 {average_compensation:.0f} 元。這僅供參考，不應直接使用此金額，而應根據本案受傷情形和損失明細進行合理估算。\n\n" if average_compensation else ""
    plaintiff_text = f"原告資訊：{plaintiffs_info}\n\n" if plaintiffs_info else ""
    return f"""你是一個台灣原告律師，你需要根據“格式範例”填寫車禍起訴狀中的賠償請求部分。請根據以下提供的受傷情形和損失情況，列出所有賠償項目，每個項目需要有明確的金額和原因。
            **不要生成總結或者結論。**

{plaintiff_text}
格式要求：
- 使用（一）、（二）等標記不同賠償項目
- 每個項目需包含標題、金額、事實根據說明
- 金額應以阿拉伯數字呈現，並加上「元」字
- 詳細說明受傷情形、治療過程
- 相關賠償項目可包括但不限於：醫療費用、看護費用、交通費用、工作損失、修車費用、精神慰撫金、修理費用等等
- 嚴格按照範本，不要添加額外資訊如分析建議，總結等等

格式範例：
（一）[損害項目]：[金額]元
[詳細說明該項損害的原因、計算基礎及相關證據]
（二）[損害項目]：[金額]元
[詳細說明該項損害的原因、計算基礎及相關證據]

{avg_compensation_text}
請根據下列受傷情形和損失情況，列出詳細賠償請求：

受傷情形：
{injuries}

損失情況：
{compensation_facts}
"""

# Multiple plaintiffs compensation prompt template
def get_compensation_prompt_part1_multiple_plaintiffs(injuries, compensation_facts, average_compensation=None, plaintiffs_info=""):
    avg_compensation_text = f"請注意：類似案件的平均賠償金額為 {average_compensation:.0f} 元。這僅供參考，不應直接使用此金額，而應根據各原告受傷情形和損失明細進行合理估算。\n\n" if average_compensation else ""
    plaintiff_text = f"原告資訊：{plaintiffs_info}\n\n" if plaintiffs_info else ""
    print(f"FOR DEBUG!COMPENSATION GENERATION 拿到的資訊：plaintiff_text: {plaintiff_text}\n")
    return f"""你是一個台灣原告律師，你需要幫忙起草車禍起訴狀中的賠償請求部分。請根據以下提供的受傷情形和損失情況，為每位原告列出所有可能的賠償項目，每個項目需要有明確的金額和原因。
            **不要生成總結或者結論。**

{plaintiff_text}
格式要求：
- 首先使用（一）、（二）等標記區分不同原告
- 每位原告部分下，使用數字1、2、3等標記不同賠償項目
- 若有原告姓名則使用；如無，則使用「原告甲○○」、「原告乙○○」等代稱
- 每個項目需包含標題、金額及詳細說明事實根據
- 金額應以阿拉伯數字呈現，並加上「元」字
- 相關賠償項目可包括但不限於：醫療費用、看護費用、交通費用、工作損失、修車費用、精神慰撫金
- 嚴格按照範本，不要添加額外資訊

格式範例：
（一）原告[姓名/代稱]部分：
1. [損害項目]：[金額]元
[詳細說明該項損害的原因、計算基礎及相關證據]
2. [損害項目]：[金額]元
[詳細說明該項損害的原因、計算基礎及相關證據]

（二）原告[姓名/代稱]部分：
1. [損害項目]：[金額]元
[詳細說明該項損害的原因、計算基礎及相關證據]
2. [損害項目]：[金額]元
[詳細說明該項損害的原因、計算基礎及相關證據]

{avg_compensation_text}請根據下列受傷情形和損失情況，列出詳細賠償請求：

受傷情形：
{injuries}

損失情況：
{compensation_facts}
"""

# Compensation part 2 prompt (calculation tags)
def get_compensation_prompt_part2(compensation_part1, plaintiffs_info=""):
    plaintiff_text = f"原告資訊：{plaintiffs_info}\n\n" if plaintiffs_info else ""
    # Determine if case involves multiple plaintiffs based on the plaintiffs_info
    is_multiple_plaintiffs = False
    if plaintiffs_info:
        plaintiffs = plaintiffs_info.replace("原告:", "").split(",")
        is_multiple_plaintiffs = len(plaintiffs) > 1
    
    # Different examples based on number of plaintiffs
    if is_multiple_plaintiffs:
        examples = """範例:
<calculate>原告1[姓名/代稱] 10000 5000 3000</calculate>
<calculate>原告2[姓名/代稱] 8000 2000 5000</calculate>"""
    else:
        examples = """範例:
<calculate>原告[姓名/代稱] 10000 5000 3000 2000</calculate>"""
    return f"""你是一個台灣原告律師助手，你的任務是幫忙為賠償請求生成計算標籤。請仔細閱讀以下賠償項目清單，然後為每位原告生成一個計算標籤。

{plaintiff_text}
賠償項目清單:
{compensation_part1}

請為每位原告生成一個<calculate>標籤，格式如下:
<calculate>原告[姓名/代稱] 金額1 金額2 金額3</calculate>

計算標籤的要求:
1. 標籤內只放數字，不要包含任何文字描述、加號、等號或小計
2. 數字必須是阿拉伯數字，不要使用中文數字
3. 不要在數字中包含逗號或其他分隔符
4. 只列出原始金額，不要自行計算總和
5. 不要在金額后面加上"元"字
6. 若賠償項目清單中有原告名稱請忽略這行，如果原告名稱不明確，才"default"作為標籤識別符

{examples}

請僅返回計算標籤，不要添加任何其他解釋或說明。
"""

# Compensation part 3 prompt (conclusion)
def get_compensation_prompt_part3(compensation_part1, summary_format, plaintiffs_info=""):
    plaintiff_text = f"原告資訊：{plaintiffs_info}\n\n" if plaintiffs_info else ""
    return f"""你是一個台灣原告律師，你需要幫忙完成車禍起訴狀中"綜上所陳"的總結部分。請根據以下提供的賠償項目和總額，生成適當的總結段落。

{plaintiff_text}
前面列出的賠償項目:
{compensation_part1}

請使用以下格式範本:
綜上所陳，[列出各原告的所有損害項目及對應金額]，{summary_format}。並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。
**範本結束**
禁止輸出範本以外的任何東西
數字必須是阿拉伯數字，不要使用中文數字
請確保按照上方原本已列出的賠償項目，列出每一項損害內容及金額
重要：不要自己計算金額及總計，僅使用提供的總額數字。
"""

# Case summary generation prompt
def get_case_summary_prompt(accident_facts, injuries):
    return f"""規則:
    1. 依據輸入的事實描述，生成結構清晰的事故摘要，完整保留所有關鍵資訊，不得遺漏。
    2. 僅使用輸入中明確提供的資訊，不得推測或補充未出現在輸入中的內容（例如：刑事判決）。
    3. 以簡潔扼要的方式陳述內容，避免冗長敘述，確保資訊清楚易讀。
    4. 若某個資訊缺失，則不輸出該項目，填入「無」或「不詳」。
    輸出格式：
    =======================
    [事故緣由]: [內容]
    [當天環境]: [內容]
    [傷勢情形]: [內容]
    =======================
    嚴格遵照上述規則，根據輸入資訊生成事故摘要。

    事故事實：
    {accident_facts}

    受傷情形：
    {injuries}
    """




###NOT USED! Compensation part 1 prompt with average compensation 
def get_compensation_prompt_part1_with_avg(injuries, compensation_facts, average_compensation):
    return f"""你是一個台灣原告律師，你需要幫忙起草車禍起訴狀中的賠償請求部分。請根據以下提供的受傷情形和損失情況，列出所有可能的賠償項目，每個項目需要有明確的金額和原因。
            **不要生成總結或者結論。**

格式要求：
- 使用（一）、（二）等標記不同賠償項目
- 每個項目包含標題、金額和請求原因
- 若涉及多名原告或多名被告，請分別列出各自的賠償項目及原因
- 金額應以數字寫明，勿使用"千"， "萬"等字眼
- 將原告A等替換成原告名字
- 禁止輸出賠償金不相關的原告資訊
- 嚴格按照範本，不要添加額外資訊

多名原告範本：
    [原告A名稱]部分:
    [損害項目名稱1]：[金額]元'\n'
    事實根據：...
    [損害項目名稱2]：[金額]元'\n'
    事實根據：...
    [原告B名稱]部分:
    [損害項目名稱1]：[金額]元'\n'
    事實根據：...
    [損害項目名稱2]：[金額]元'\n'
    事實根據：...
**範本結束**

請注意：類似案件的平均賠償金額為 {average_compensation:.0f} 元。這僅供參考，不應直接使用此金額，而應根據本案受傷情形和損失明細進行合理估算。

請根據下列受傷情形和損失情況，列出詳細賠償請求：

受傷情形：
{injuries}

損失情況：
{compensation_facts}
"""

###NOT USED!!! Compensation part 1 prompt without average compensation
def get_compensation_prompt_part1_without_avg(injuries, compensation_facts):
    return f"""你是一個台灣原告律師，你需要幫忙起草車禍起訴狀中的賠償請求部分。請根據以下提供的受傷情形和損失情況，列出所有可能的賠償項目，每個項目需要有明確的金額和原因。
            **不要生成總結或者結論。**

格式要求：
- 使用（一）、（二）等標記不同賠償項目
- 每個項目包含標題、金額和請求原因
- 若涉及多名原告或多名被告，請分別列出各自的賠償項目及原因
- 金額應以數字寫明，勿使用"千"， "萬"等字眼
- 將原告A等替換成原告名字
- 禁止輸出賠償金不相關的原告資訊
- 嚴格按照範本，不要添加額外資訊

多名原告範本：
    [原告A名稱]部分:
    [損害項目名稱1]：[金額]元'\n'
    事實根據：...
    [損害項目名稱2]：[金額]元'\n'
    事實根據：...
    [原告B名稱]部分:
    [損害項目名稱1]：[金額]元'\n'
    事實根據：...
    [損害項目名稱2]：[金額]元'\n'
    事實根據：...
**範本結束**

請根據下列受傷情形和損失情況，列出詳細賠償請求：

受傷情形：
{injuries}

損失情況：
{compensation_facts}
"""