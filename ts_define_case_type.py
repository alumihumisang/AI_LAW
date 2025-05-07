import re
from ts_input_filter import generate_filter

def get_case_type(sim_input: str, people_input: str = None, cinfo: int = 0):
    """
    根據模擬輸入文本 sim_input 判斷案件的類型。
    Args:
        sim_input (str): 用戶輸入的案件描述文字。
        people_input (str): 外部若已有 get_people 結果，則傳入以避免重複推理。
        cinfo (int): 是否回傳 case_info。
    Returns:
        tuple: (案件的類型描述, 原告資訊[, case_info])
    """
    # ✅ 若外部已傳入抽出結果則使用，否則用 generate_filter()
    if people_input is None:
        case_info, plaintiffs_info = generate_filter(sim_input)
    else:
        case_info = people_input
        # 預設原告資訊為第一個原告（僅供展示）
        plaintiff_match = re.search(r"原告[:：]?(.*?)\n", case_info)
        plaintiffs_info = plaintiff_match.group(1).strip() if plaintiff_match else "未提及"

    print(f"CASE INFO: {case_info}\n")

    # 分割姓名
    pattern = r"原告:([\u4e00-\u9fa5A-Za-z0-9○·．,、]+)"
    plaintiff_match = re.search(pattern, case_info)
    pattern = r"被告:([\u4e00-\u9fa5A-Za-z0-9○·．,、]+)"
    defendant_match = re.search(pattern, case_info)

    plaintiffs = re.split(r"[,、]", plaintiff_match.group(1)) if plaintiff_match else []
    defendants = re.split(r"[,、]", defendant_match.group(1)) if defendant_match else []

    plaintiffs = [name.strip() for name in plaintiffs]
    defendants = [name.strip() for name in defendants]

    # 判斷基本案型
    case_type = ""
    p, d = len(plaintiffs), len(defendants)
    if p <= 1 and d <= 1:
        case_type = "單純原被告各一"
    elif p > 1 and d <= 1:
        case_type = "數名原告"
    elif p <= 1 and d > 1:
        case_type = "數名被告"
    elif p > 1 and d > 1:
        case_type = "原被告皆數名"

    # 加入 §187/§188/§190 類型
    match = re.search(r'被告是否為未成年人(.*?)被告是否為受僱人(.*?)車禍是否由動物造成(.*)', case_info, re.S)
    if match:
        if match.group(1).strip()[-1] == "是":
            case_type += "+§187未成年案型"
        if match.group(2).strip()[-1] == "是":
            case_type += "+§188僱用人案型"
        if match.group(3).strip()[-1] == "是":
            case_type += "+§190動物案型"

    if cinfo == 1:
        return case_type, plaintiffs_info, case_info
    return case_type, plaintiffs_info
