import re

def extract_parties_v9(user_query: str) -> dict:
    """
    角色感知版原告 / 被告抽取器 v9
    直接讀律師輸入進行語義判斷，穩定歸戶
    """

    result = {"原告": set(), "被告": set()}

    # 先擷取「事故發生緣由」段落（減少無關干擾）
    match = re.search(r"一[、.． ]?事故發生緣由[:：]?\s*(.*?)(二|$)", user_query, re.S)
    incident_text = match.group(1) if match else user_query

    # 角色標籤型正則：
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

    # 進一步補強：  
    # 若完全沒抽到，且有 "原告" / "被告" 這類關鍵詞，仍以通稱填入
    if not result["原告"]:
        if "原告" in incident_text:
            result["原告"].add("原告")

    if not result["被告"]:
        if "被告" in incident_text:
            result["被告"].add("被告")

    # 最後整理輸出 (去重排序)
    return {
        "原告": "、".join(sorted(result["原告"])) if result["原告"] else "未提及",
        "被告": "、".join(sorted(result["被告"])) if result["被告"] else "未提及"
    }

# ✅ 測試範例：
if __name__ == "__main__":
    text = """
一、事故發生緣由:
被告余泳霖於民國110年4月24日晚間10時許，在新竹市○區○○路000號飲用啤酒後，
仍處於不能安全駕駛動力交通工具之狀態，竟基於酒後駕駛動力交通工具之犯意，
於翌（25）日上午6時29分許，無照駕駛被告劉慧綾名下之車牌號碼000-000號普通重型機車。
"""

    parties = extract_parties_v9(text)
    print(parties)
