"""
重新萃取 P_Injury：針對 232 筆 PI_N 但有求償的矛盾案件
策略：從 compensation_text 開頭抽傷害描述，重跑 Injury 分類
"""
import json, re, requests, time
from pathlib import Path
from neo4j import GraphDatabase

TENSORS_FILE = Path(__file__).parent / "phase1_tensors_v4.jsonl"
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:27b"

XRAG_URI  = "neo4j+s://3a29e735.databases.neo4j.io"
XRAG_USER = "3a29e735"
XRAG_PASS = "WSsO9OxVIn_mk31PiDOyMeZgjJ5epEPtOTVfHtuVYE8"

INJURY_SCORE = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2, "N": 0.0}

def score_to_level(s):
    if s > 0.85: return "A"
    if s > 0.65: return "B"
    if s > 0.45: return "C"
    if s > 0.15: return "D"
    if s < 0:    return "E"
    return "N"


def extract_injury_text(comp_text: str) -> str:
    """從賠償段抽出傷害描述句（通常在開頭）"""
    if not comp_text:
        return ""
    # 找「原告因本次事故受有...傷害」這類句子
    m = re.search(
        r'(原告[^。]*?受有[^。]{5,200}[傷害|骨折|撕裂|挫傷|出血|骨碎|截肢|植物人|腦震盪|骨折|瘀傷])',
        comp_text
    )
    if m:
        return m.group(1)
    # fallback：取前 400 字
    return comp_text[:400]


def call_ollama(prompt: str, retries=3) -> str:
    for i in range(retries):
        try:
            r = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 20}
            }, timeout=60)
            return r.json().get("response", "").strip()
        except Exception as e:
            print(f"    [重試 {i+1}] {e}")
            time.sleep(2)
    return "N"


def classify_injury(injury_text: str) -> str:
    if not injury_text:
        return "N"
    prompt = f"""以下是台灣民事案件中原告的受傷描述，請判斷傷害等級。

傷害描述：
{injury_text}

【Injury 等級】
A=植物人/截肢/全身癱瘓
B=顱內出血/脊椎骨折/需專人長期看護/失明
C=骨折/鋼釘固定/住院手術/多處複合傷
D=挫傷/腦震盪/需復健/輕微骨裂
E=擦傷/破皮/瘀青/輕微扭傷
N=原告未受傷/純財損/無人身傷害

請只回答一個字母（A/B/C/D/E/N），不要其他文字："""
    resp = call_ollama(prompt).strip().upper()
    # 只取第一個合法字母
    for ch in resp:
        if ch in "ABCDEN":
            return ch
    return "N"


def update_trie(driver, case_id, old_lig, new_lig, old_scores, new_scores):
    old_root = f"L{old_lig['L1']}{old_lig['L2']}{old_lig['L3']}{old_lig['L4']}"
    new_root = old_root  # litigant 不變

    old_df = score_to_level(old_scores["D_Fact"])
    old_pi = score_to_level(old_scores["P_Injury"])
    new_df = score_to_level(new_scores["D_Fact"])
    new_pi = score_to_level(new_scores["P_Injury"])

    old_l3 = f"{old_root}_DF_{old_df}_PI_{old_pi}"
    new_l2 = f"{new_root}_DF_{new_df}"
    new_l3 = f"{new_l2}_PI_{new_pi}"

    with driver.session() as s:
        s.run("MERGE (:FeatureNode {code:$c})", c=new_l3)
        s.run("""
            MATCH (a {code:$l2}), (b {code:$l3})
            MERGE (a)-[r:HAS_FEATURE {feature:'P_Injury'}]->(b)
            SET r.score = $sc
        """, l2=new_l2, l3=new_l3, sc=new_scores["P_Injury"])
        s.run("""
            MATCH ({code:$ol})-[r:CONTAINS]->(c:Case {case_id:$cid})
            DELETE r
        """, ol=old_l3, cid=case_id)
        s.run("""
            MATCH (leaf {code:$nl}), (c:Case {case_id:$cid})
            MERGE (leaf)-[:CONTAINS]->(c)
            SET c.litigant_code = $nr,
                c.feature_scores = $fs
        """, nl=new_l3, cid=case_id, nr=new_root,
             fs=json.dumps(new_scores, ensure_ascii=False))


def main():
    print("=== 重新萃取 P_Injury（232 筆矛盾案件）===\n")

    records = {}
    with open(TENSORS_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                records[str(rec["case_id"])] = rec

    # 找矛盾案件：P_Injury=0 且 P_Comp>=0.25
    targets = [
        rec for rec in records.values()
        if rec["scores"]["P_Injury"] == 0.0 and rec["scores"]["P_Comp"] >= 0.25
    ]
    targets.sort(key=lambda r: r["case_id"])
    print(f"目標案件：{len(targets)} 筆\n")

    driver = GraphDatabase.driver(XRAG_URI, auth=(XRAG_USER, XRAG_PASS))
    changed = 0
    stayed_n = 0

    for i, rec in enumerate(targets):
        cid  = str(rec["case_id"])
        comp = rec.get("compensation_text", "") or ""
        fact = rec.get("fact_text", "") or ""

        # 傷害文字：優先 comp 開頭，再補 fact
        injury_text = extract_injury_text(comp)
        if not injury_text:
            injury_text = fact[:400]

        new_level = classify_injury(injury_text)
        old_level = "N"

        print(f"[{i+1:3d}/{len(targets)}] case {cid:>5}  N → {new_level}"
              f"  | {injury_text[:60]}...")

        if new_level == "N":
            stayed_n += 1
            continue

        # 更新 scores
        old_scores = dict(rec["scores"])
        new_scores  = dict(old_scores)
        new_scores["P_Injury"] = INJURY_SCORE[new_level]

        # 更新 fact_injury_matrix
        fim = rec.get("fact_injury_matrix", {})
        if "Plaintiff" in fim and isinstance(fim["Plaintiff"], dict):
            fim["Plaintiff"]["Injury"] = new_level

        # 更新 tensor（index 8 = P_Injury，按實際儲存順序）
        # 實際 tensor 順序: [L1,L2,L3,L4, P_Fact,D_Fact,V_Fact,E_Fact,
        #                     P_Injury,D_Injury,V_Injury,E_Injury,
        #                     P_Comp,D_Comp,V_Comp,E_Comp]
        t = list(rec["tensor"])
        t[8] = INJURY_SCORE[new_level]
        rec["tensor"] = t
        rec["scores"] = new_scores
        rec["fact_injury_matrix"] = fim
        records[cid] = rec

        update_trie(driver, cid, rec["litigant"], rec["litigant"], old_scores, new_scores)
        changed += 1

    driver.close()

    # 覆蓋 JSONL
    tmp = TENSORS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.rename(TENSORS_FILE)

    print(f"\n✅ 完成：{changed} 筆從 PI_N 移出，{stayed_n} 筆重新確認為 N（真的無傷）")


if __name__ == "__main__":
    main()
