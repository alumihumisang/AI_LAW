"""
起訴書文本切段工具
切成四段：fact / laws / compensation / conclusion
"""
import re


def chunk_indictment(text: str) -> dict:
    """
    將起訴書全文切成四段。

    Returns:
        {
            "fact_text":         事故事實段（一、）
            "laws_text":         法條引用段（二、按）
            "compensation_text": 各項賠償金額段（(一)(二)...）
            "conclusion_text":   綜上結論段
            "full_text":         全文
        }
    """
    result = {
        "fact_text": "",
        "laws_text": "",
        "compensation_text": "",
        "conclusion_text": "",
        "full_text": text,
    }

    if not text:
        return result

    # ── 找各分界點 ────────────────────────────────────────

    # 法條段起點：「二、按」或「二、依」
    laws_match = re.search(r'[二2][、,，。\s]*[按依]', text)

    # 賠償項目起點：第一個 (一) 或 （一）
    comp_match = re.search(r'[（(]一[）)]', text)

    # 結論段起點：含「綜上」的段落
    conclusion_match = re.search(r'綜上', text)

    # ── 切段 ──────────────────────────────────────────────

    # 事實段：開頭到法條段之前
    if laws_match:
        result["fact_text"] = text[:laws_match.start()].strip()
    else:
        result["fact_text"] = text.strip()

    # 法條段：法條起點到賠償起點之前
    if laws_match and comp_match and comp_match.start() > laws_match.start():
        result["laws_text"] = text[laws_match.start():comp_match.start()].strip()
    elif laws_match:
        result["laws_text"] = text[laws_match.start():].strip()

    # 賠償段：賠償起點到結論之前
    if comp_match and conclusion_match and conclusion_match.start() > comp_match.start():
        result["compensation_text"] = text[comp_match.start():conclusion_match.start()].strip()
    elif comp_match:
        result["compensation_text"] = text[comp_match.start():].strip()

    # 結論段：最後一個「綜上」段落
    if conclusion_match:
        result["conclusion_text"] = text[conclusion_match.start():].strip()

    return result


if __name__ == "__main__":
    # 快速測試
    import pandas as pd
    df = pd.read_excel("/home/aru/AI_LAW/6057起訴書_全.xlsx")

    ok = 0
    missing_laws = 0
    missing_comp = 0
    missing_conc = 0

    for _, row in df.iterrows():
        chunks = chunk_indictment(row["起訴書"] or "")
        if not chunks["laws_text"]:
            missing_laws += 1
        if not chunks["compensation_text"]:
            missing_comp += 1
        if not chunks["conclusion_text"]:
            missing_conc += 1
        else:
            ok += 1

    total = len(df)
    print(f"總計: {total}")
    print(f"缺 laws_text:        {missing_laws} ({missing_laws/total*100:.1f}%)")
    print(f"缺 compensation_text:{missing_comp} ({missing_comp/total*100:.1f}%)")
    print(f"缺 conclusion_text:  {missing_conc} ({missing_conc/total*100:.1f}%)")
    print(f"四段齊全:            {ok} ({ok/total*100:.1f}%)")

    # 印出第1筆看看
    sample = chunk_indictment(df.iloc[0]["起訴書"])
    for k, v in sample.items():
        if k != "full_text":
            print(f"\n── {k} ──")
            print(v[:200])
