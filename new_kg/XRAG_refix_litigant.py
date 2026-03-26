"""
XRAG 補跑：修正可疑 Litigant 誤判（L2/L4 存疑筆數）

判斷邏輯：
  可疑條件 = LLM 說多原告(L2=1) 但全文只找到 1 個「原告XXX」
           = LLM 說多被告(L4=1) 但全文只找到 1 個「被告XXX」
修正流程：
  1. 對可疑筆重跑 Litigant LLM prompt
  2. 若新結果改變 → 更新 JSONL + 重建 Neo4j Trie 路徑
     （只移動 CONTAINS 邊，D_Fact/P_Injury 等級不動）
"""

import json, time, re, requests
from pathlib import Path
from neo4j import GraphDatabase

TENSORS_FILE = Path(__file__).parent / "phase1_tensors_v4.jsonl"
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:27b"

XRAG_URI  = "neo4j+s://3a29e735.databases.neo4j.io"
XRAG_USER = "3a29e735"
XRAG_PASS = "WSsO9OxVIn_mk31PiDOyMeZgjJ5epEPtOTVfHtuVYE8"

# ── 姓名偵測 regex（與 XRAG_add_party_info.py 同） ────────
MASKED   = r'[\u4e00-\u9fff]○[\u4e00-\u9fff○]?'
SURNAMES = (
    "王李張劉陳楊黃趙吳周徐孫胡朱高林何郭馬羅梁宋鄭謝韓唐馮董蕭"
    "程曹袁鄧許傅沈曾彭呂蘇盧蔣蔡賈丁魏薛葉閻余潘杜戴夏鍾汪田任"
    "姜范方石姚譚廖鄒熊金陸郝孔白崔康毛邱秦江史顧侯邵孟龍萬錢湯"
    "尹黎易常武賀賴龔文施卓游簡柯翁柳洪涂倪巫紀葛成舒喬貝龐桂連"
    "苗顏莊溫闕阮包嚴穆塗靳昌鄔虞童班殷魯齊費鮑杞詹蕭許吳蔡呂鄧"
)
FULLNAME = r'[' + SURNAMES + r'][\u4e00-\u9fff]{1,2}'
COMPANY  = (r'[\u4e00-\u9fff]{2,12}'
            r'(?:股份有限公司|有限公司|公司|企業行|企業社|診所|醫院'
            r'|醫事檢驗所|協會|基金會|社團法人|財團法人)')
SUBJ     = r'(?:' + MASKED + r'|' + FULLNAME + r'|' + COMPANY + r')'
RE_P     = re.compile(r'原告[：: ]?(' + SUBJ + r')')
RE_D     = re.compile(r'被告[：: ]?(' + SUBJ + r')')


def score_to_level(s: float) -> str:
    if s > 0.85: return "A"
    if s > 0.65: return "B"
    if s > 0.45: return "C"
    if s > 0.15: return "D"
    if s < 0:    return "E"
    return "N"


def unique_names(text, pattern):
    return list(dict.fromkeys(
        m.strip() for m in pattern.findall(text) if len(m.strip()) >= 2
    ))


# ── 找出可疑案件 ──────────────────────────────────────────
def find_suspicious(records: list) -> set:
    sus = set()
    for rec in records:
        lig = rec["litigant"]
        ft  = rec.get("fact_text", "")
        cid = str(rec["case_id"])
        p_names = unique_names(ft, RE_P)
        d_names = unique_names(ft, RE_D)
        if lig.get("L2") and len(p_names) == 1:
            sus.add(cid)
        if lig.get("L4") and len(d_names) == 1:
            sus.add(cid)
    return sus


# ── Ollama ────────────────────────────────────────────────
def call_ollama(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL, "prompt": prompt,
                "stream": False, "options": {"temperature": 0.0}
            }, timeout=120)
            resp.raise_for_status()
            return resp.json()["response"].strip()
        except Exception as e:
            print(f"  [Ollama 第{attempt+1}次失敗] {e}")
            time.sleep(5)
    return ""


def extract_json(text: str) -> str:
    if "```" in text:
        text = "\n".join(l for l in text.split("\n") if not l.strip().startswith("```"))
    s, e = text.find("{"), text.rfind("}") + 1
    return text[s:e] if s != -1 else ""


def detect_litigant(fact_text: str) -> dict | None:
    prompt = f"""你是法律文件分析專家。請閱讀以下起訴書事實段落，判斷訴訟當事人結構。

文本：
{fact_text[:1500]}

請只回答JSON，不要其他文字：
{{"single_plaintiff":true或false,"multiple_plaintiffs":true或false,"single_defendant":true或false,"multiple_defendants":true或false}}

判斷規則（重要）：
- single/multiple_plaintiff 恰好一個為true；single/multiple_defendant 恰好一個為true
- 「多原告」：多位當事人分別作為原告提出請求（各自有「原告」稱謂）
- 搭載乘客、家屬、訴外人、事故目擊者 ≠ 原告
- 「多被告」：自然人被告＋公司僱主被告，或多位自然人被告
- 受僱人與其任職公司同時被告 → multiple_defendants=true"""

    resp = call_ollama(prompt)
    try:
        d = json.loads(extract_json(resp))
        lig = {
            "L1": 1 if d.get("single_plaintiff")    else 0,
            "L2": 1 if d.get("multiple_plaintiffs") else 0,
            "L3": 1 if d.get("single_defendant")    else 0,
            "L4": 1 if d.get("multiple_defendants") else 0,
        }
        # 基本合法性驗證
        if lig["L1"] + lig["L2"] == 1 and lig["L3"] + lig["L4"] == 1:
            return lig
        print(f"  [非法結果] {lig}，跳過")
        return None
    except Exception as ex:
        print(f"  [解析失敗] {ex} | {resp[:60]}")
        return None


# ── Neo4j：移動 Case 到新 Trie 路徑 ──────────────────────
def update_trie(driver, case_id: str, old_lig: dict, new_lig: dict, scores: dict):
    old_root = f"L{old_lig['L1']}{old_lig['L2']}{old_lig['L3']}{old_lig['L4']}"
    new_root = f"L{new_lig['L1']}{new_lig['L2']}{new_lig['L3']}{new_lig['L4']}"

    df_score = scores.get("D_Fact", 0.0)
    pi_score = scores.get("P_Injury", 0.0)
    df_level = score_to_level(df_score)
    pi_level = score_to_level(pi_score)

    old_l3 = f"{old_root}_DF_{df_level}_PI_{pi_level}"
    new_l2 = f"{new_root}_DF_{df_level}"
    new_l3 = f"{new_l2}_PI_{pi_level}"

    with driver.session() as s:
        # 建新 Trie 節點（若已存在則 MERGE 不重建）
        s.run("MERGE (:LitigantConfig {code: $c})", c=new_root)
        s.run("MERGE (:FeatureNode {code: $c})", c=new_l2)
        s.run("MERGE (:FeatureNode {code: $c})", c=new_l3)

        # 建新 Trie 邊
        s.run("""
            MATCH (a {code: $fc}), (b {code: $tc})
            MERGE (a)-[r:HAS_FEATURE {feature: 'D_Fact'}]->(b)
            SET r.score = $sc
        """, fc=new_root, tc=new_l2, sc=df_score)
        s.run("""
            MATCH (a {code: $fc}), (b {code: $tc})
            MERGE (a)-[r:HAS_FEATURE {feature: 'P_Injury'}]->(b)
            SET r.score = $sc
        """, fc=new_l2, tc=new_l3, sc=pi_score)

        # 移動 Case：刪舊 CONTAINS → 建新 CONTAINS → 更新 litigant_code
        s.run("""
            MATCH ({code: $old_leaf})-[r:CONTAINS]->(c:Case {case_id: $cid})
            DELETE r
        """, old_leaf=old_l3, cid=case_id)
        s.run("""
            MATCH (leaf {code: $new_leaf}), (c:Case {case_id: $cid})
            MERGE (leaf)-[:CONTAINS]->(c)
            SET c.litigant_code = $new_root
        """, new_leaf=new_l3, cid=case_id, new_root=new_root)


# ── 主程式 ────────────────────────────────────────────────
def main():
    print("=== XRAG 補跑：Litigant 誤判修正 ===")

    records = {}
    with open(TENSORS_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                records[str(rec["case_id"])] = rec
    print(f"讀取：{len(records)} 筆")

    suspicious = find_suspicious(list(records.values()))
    total = len(suspicious)
    print(f"可疑 Litigant 筆數：{total} 筆\n")

    driver = GraphDatabase.driver(XRAG_URI, auth=(XRAG_USER, XRAG_PASS))

    changed, skipped = 0, 0
    for i, cid in enumerate(sorted(suspicious, key=int)):
        rec     = records[cid]
        old_lig = rec["litigant"]
        old_code = f"L{old_lig['L1']}{old_lig['L2']}{old_lig['L3']}{old_lig['L4']}"

        print(f"[{i+1}/{total}] case {cid} 舊={old_code}", end="  ", flush=True)

        new_lig = detect_litigant(rec.get("fact_text", ""))
        if new_lig is None:
            print("LLM失敗，跳過")
            skipped += 1
            continue

        new_code = f"L{new_lig['L1']}{new_lig['L2']}{new_lig['L3']}{new_lig['L4']}"
        if new_code == old_code:
            print(f"維持 {old_code}")
            continue

        print(f"→ {new_code}  更新！")

        # 更新 JSONL
        rec["litigant"] = new_lig
        t = rec["tensor"]
        t[0], t[1], t[2], t[3] = new_lig["L1"], new_lig["L2"], new_lig["L3"], new_lig["L4"]
        rec["tensor"] = t
        records[cid] = rec

        # 更新 Neo4j
        update_trie(driver, cid, old_lig, new_lig, rec["scores"])
        changed += 1

    driver.close()

    # 覆蓋 JSONL
    tmp = TENSORS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.rename(TENSORS_FILE)

    print(f"\n=== 完成 ===")
    print(f"  更新：{changed} 筆  維持：{total-changed-skipped} 筆  LLM失敗：{skipped} 筆")
    print(f"  JSONL 已覆蓋：{TENSORS_FILE}")


if __name__ == "__main__":
    main()
