"""
XRAG 補充當事人資訊
為既有 Case 節點加上：
  - plaintiff_count  : 原告人數（整數；多人時嘗試從文本計數）
  - defendant_count  : 被告人數（同上）
  - plaintiff_names  : 原告姓名清單（list[str]）
  - defendant_names  : 被告姓名清單（list[str]）

姓名來源：fact_text regex
  台灣起訴書常見格式：
    甲○○、乙○○      遮蔽式（一字 + ○○）
    王○○、陳○明      部分遮蔽
    王大明            實名
"""

import json
import re
from pathlib import Path
from neo4j import GraphDatabase

TENSORS_FILE = Path(__file__).parent / "phase1_tensors_v4.jsonl"

XRAG_URI  = "neo4j+s://3a29e735.databases.neo4j.io"
XRAG_USER = "3a29e735"
XRAG_PASS = "WSsO9OxVIn_mk31PiDOyMeZgjJ5epEPtOTVfHtuVYE8"

BATCH_SIZE = 100

# ── 姓名提取 regex ──────────────────────────────────────────
# 台灣起訴書典型格式：
#   (1) 遮蔽名：一個中文字 + ○○ 或 ○X（X=中文字）
#   (2) 半遮蔽：二~三中文字，含 ○
#   (3) 全名：二~四個中文字（無 ○）
# ── 姓名子模式 ────────────────────────────────────────────
# (1) 遮蔽名：含 ○，如 甲○○、王○明、林○○  → 精準可靠
MASKED_PAT = r'[\u4e00-\u9fff]○[\u4e00-\u9fff○]?'

# (2) 全名（不含 ○）：第一字限常見姓氏 + 後接 1~2 字
#     以姓氏為錨點，避免把「騎乘車號」「因而人車」等動詞片語誤抓
SURNAMES = (
    # 百家姓常見姓（台灣法院文書高頻，已去重）
    # 注意：「於」是介詞不是姓，不收錄
    "王李張劉陳楊黃趙吳周徐孫胡朱高林何郭馬羅梁宋鄭謝韓唐馮董蕭"
    "程曹袁鄧許傅沈曾彭呂蘇盧蔣蔡賈丁魏薛葉閻余潘杜戴夏鍾汪田任"
    "姜范方石姚譚廖鄒熊金陸郝孔白崔康毛邱秦江史顧侯邵孟龍萬錢湯"
    "尹黎易常武賀賴龔文施卓游簡柯翁柳洪涂倪巫紀葛成舒喬貝龐桂連"
    "苗顏莊溫闕阮包嚴穆塗靳昌鄔虞童班殷魯齊費鮑杞詹蕭許吳蔡呂鄧"
)
FULL_NAME_PAT = r'[' + SURNAMES + r'][\u4e00-\u9fff]{1,2}'

# (3) 公司/法人名稱：2~12 字 + 法人尾綴
#     台灣常見：有限公司、股份有限公司、企業行、診所、醫院、學校、協會等
COMPANY_SUFFIX = r'(?:股份有限公司|有限公司|企業有限公司|企業股份有限公司|公司|企業行|企業社|診所|醫院|醫事檢驗所|學校|協會|基金會|社團法人|財團法人|運輸行|商行|工作室)'
COMPANY_PAT    = r'[\u4e00-\u9fff]{2,12}' + COMPANY_SUFFIX

NAME_PAT    = r'(?:' + MASKED_PAT + r'|' + FULL_NAME_PAT + r')'
SUBJECT_PAT = r'(?:' + MASKED_PAT + r'|' + FULL_NAME_PAT + r'|' + COMPANY_PAT + r')'

RE_PLAINTIFF = re.compile(r'原告(?:等)?[：: ]?(' + SUBJECT_PAT + r')')
RE_DEFENDANT = re.compile(r'被告(?:等)?[：: ]?(' + SUBJECT_PAT + r')')


def extract_names(text: str, pattern: re.Pattern) -> list[str]:
    """從 fact_text 提取姓名，去重，最多回傳 10 個。"""
    raw = pattern.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for name in raw:
        name = name.strip()
        if len(name) < 2:
            continue
        if name not in seen:
            seen.add(name)
            result.append(name)
        if len(result) >= 10:
            break
    return result


def count_from_names(names: list[str], flag_single: int, flag_multiple: int) -> int:
    """
    有名字時信 regex 計數（比 LLM 可靠）；
    沒名字時才 fallback 到 L1/L3（單人）或 L2/L4（多人）旗標。
    """
    if names:
        return len(names)   # regex 實際找到幾個就幾個
    if flag_single:
        return 1
    if flag_multiple:
        return 2            # LLM 說多人但沒抓到名字，保守記 2
    return 0


def process_record(rec: dict) -> dict:
    lig       = rec["litigant"]
    fact_text = rec.get("fact_text", "")

    plaintiff_names = extract_names(fact_text, RE_PLAINTIFF)
    defendant_names = extract_names(fact_text, RE_DEFENDANT)

    plaintiff_count = count_from_names(
        plaintiff_names, lig.get("L1", 0), lig.get("L2", 0))
    defendant_count = count_from_names(
        defendant_names, lig.get("L3", 0), lig.get("L4", 0))

    return {
        "case_id":         str(rec["case_id"]),
        "plaintiff_count": plaintiff_count,
        "defendant_count": defendant_count,
        "plaintiff_names": plaintiff_names,
        "defendant_names": defendant_names,
    }


def update_neo4j(driver, updates: list):
    with driver.session() as s:
        for i in range(0, len(updates), BATCH_SIZE):
            batch = updates[i:i + BATCH_SIZE]
            s.run("""
                UNWIND $rows AS row
                MATCH (c:Case {case_id: row.case_id})
                SET c.plaintiff_count = row.plaintiff_count,
                    c.defendant_count = row.defendant_count,
                    c.plaintiff_names = row.plaintiff_names,
                    c.defendant_names = row.defendant_names
            """, rows=batch)
            print(f"  [{i+len(batch)}/{len(updates)}] 批次完成")


MISSING = "未提及"


def finalize_names(names: list[str]) -> list[str]:
    """空清單填 ['未提及']，保持 list 型別一致。"""
    return names if names else [MISSING]


def main():
    import random
    print("=== XRAG: 補充當事人資訊 ===")

    records = []
    with open(TENSORS_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    print(f"讀取：{len(records)} 筆")

    # 先跑 process_record，再套 finalize
    raw_updates = [process_record(rec) for rec in records]
    # 同時保留原始 fact_text 供診斷用
    fact_map = {str(r["case_id"]): r.get("fact_text", "") for r in records}

    updates = []
    for u in raw_updates:
        updates.append({
            **u,
            "plaintiff_names": finalize_names(u["plaintiff_names"]),
            "defendant_names": finalize_names(u["defendant_names"]),
        })

    # ── 統計 ──────────────────────────────────────────
    has_p   = sum(1 for u in updates if u["plaintiff_names"] != [MISSING])
    has_d   = sum(1 for u in updates if u["defendant_names"] != [MISSING])
    miss_p  = len(updates) - has_p
    miss_d  = len(updates) - has_d
    multi_p = sum(1 for u in updates if u["plaintiff_count"] > 1)
    multi_d = sum(1 for u in updates if u["defendant_count"] > 1)
    print(f"原告：抓到姓名 {has_p} 筆 / 未提及 {miss_p} 筆（多原告：{multi_p} 筆）")
    print(f"被告：抓到姓名 {has_d} 筆 / 未提及 {miss_d} 筆（多被告：{multi_d} 筆）")

    # ── 預覽前 8 筆（有抓到名字） ───────────────────
    print("\n── 有抓到名字（前 8 筆）──")
    shown = 0
    for u in updates:
        if u["plaintiff_names"] != [MISSING] or u["defendant_names"] != [MISSING]:
            p_str = "、".join(u["plaintiff_names"])
            d_str = "、".join(u["defendant_names"])
            print(f"  {u['case_id']:>5}: 原{u['plaintiff_count']}人[{p_str}]  被{u['defendant_count']}人[{d_str}]")
            shown += 1
            if shown >= 8:
                break

    # ── 診斷：隨機抽 8 筆「被告未提及」，印 fact_text 前 150 字 ──
    no_def = [u for u in updates if u["defendant_names"] == [MISSING]]
    sample = random.sample(no_def, min(8, len(no_def)))
    print(f"\n── 被告姓名「未提及」隨機抽樣（共 {len(no_def)} 筆，抽 {len(sample)} 筆）──")
    print("（確認是真的沒寫名字，還是 regex 漏掉了）")
    for u in sample:
        ft = fact_map.get(u["case_id"], "")[:150].replace("\n", " ")
        print(f"\n  case {u['case_id']:>5} | {ft}")

    answer = input("\n確認寫入 Neo4j？(y/n): ").strip().lower()
    if answer != "y":
        print("已取消。")
        return

    driver = GraphDatabase.driver(XRAG_URI, auth=(XRAG_USER, XRAG_PASS))
    update_neo4j(driver, updates)
    driver.close()

    print("\n完成！Case 節點已補充當事人資訊。")
    print("驗證查詢：")
    print("  MATCH (c:Case) RETURN c.case_id, c.plaintiff_names, c.defendant_names LIMIT 10")


if __name__ == "__main__":
    main()
