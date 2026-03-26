"""
用 LI_injury 重新驗證全部 6057 筆的 P_Injury 等級
- 來源：LI_injury（二、原告受傷情形）比 fact_text 更可靠
- 有斷點續跑（checkpoint.json）
- 只更新有變動的筆
"""
import json, re, requests, time
from pathlib import Path
from neo4j import GraphDatabase

TENSORS_FILE = Path("/home/aru/AI_LAW/new_kg/phase1_tensors_v4.jsonl")
CHECKPOINT   = Path("/home/aru/AI_LAW/new_kg/refix_all_injury_checkpoint.json")
LOG_FILE     = Path("/tmp/refix_all_injury.log")

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:27b"

XRAG_URI  = "neo4j+s://3a29e735.databases.neo4j.io"
XRAG_USER = "3a29e735"
XRAG_PASS = "WSsO9OxVIn_mk31PiDOyMeZgjJ5epEPtOTVfHtuVYE8"

INJURY_SCORE = {"A":1.0,"B":0.8,"C":0.6,"D":0.4,"E":0.2,"N":0.0}

def score_to_level(s):
    if s > 0.85: return "A"
    if s > 0.65: return "B"
    if s > 0.45: return "C"
    if s > 0.15: return "D"
    if s < 0:    return "E"
    return "N"

def call_ollama(prompt, retries=3):
    for i in range(retries):
        try:
            r = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 10}
            }, timeout=60)
            return r.json().get("response", "").strip()
        except Exception as e:
            if i == retries - 1:
                return "N"
            time.sleep(2)
    return "N"

def classify_injury(li_injury_text):
    if not li_injury_text or len(li_injury_text.strip()) < 10:
        return "N"
    prompt = f"""以下是台灣民事車禍案件中，律師描述「原告受傷情形」的段落。
請判斷【原告本人】的人身傷害等級。
若描述的是被告受傷、訴外人受傷、或純財產損失（車損），請回答N。

原告受傷描述：
{li_injury_text[:800]}

【傷害等級】
A=植物人/截肢/全身癱瘓/無法脫離呼吸器
B=顱內出血/脊椎骨折/需專人長期看護/失明/下肢癱瘓
C=骨折/鋼釘固定/住院手術/粉碎性骨折/多處複合傷
D=挫傷/腦震盪/需復健/輕微骨裂/拉傷/扭傷
E=擦傷/破皮/瘀青/輕微擦挫傷
N=原告未受傷/純財損/純驚嚇/受傷的是被告或訴外人

只回答一個字母（A/B/C/D/E/N）："""
    resp = call_ollama(prompt).upper()
    for ch in resp:
        if ch in "ABCDEN":
            return ch
    return "N"

def update_neo4j(driver, case_id, lig, old_pi, new_pi, new_scores):
    root     = f"L{lig['L1']}{lig['L2']}{lig['L3']}{lig['L4']}"
    df_level = score_to_level(new_scores["D_Fact"])
    old_code = f"{root}_DF_{df_level}_PI_{old_pi}"
    new_code = f"{root}_DF_{df_level}_PI_{new_pi}"
    df_code  = f"{root}_DF_{df_level}"
    with driver.session() as s:
        s.run("MERGE (:FeatureNode {code:$c})", c=new_code)
        s.run("""
            MATCH (df {code:$df}), (pi_n {code:$pn})
            MERGE (df)-[r:HAS_FEATURE {feature:'P_Injury'}]->(pi_n)
            SET r.score = $sc
        """, df=df_code, pn=new_code, sc=INJURY_SCORE[new_pi])
        s.run("""
            MATCH (old {code:$oc})-[r:CONTAINS]->(c:Case {case_id:$cid})
            DELETE r
        """, oc=old_code, cid=str(case_id))
        s.run("""
            MATCH (pi_n {code:$nc}), (c:Case {case_id:$cid})
            MERGE (pi_n)-[:CONTAINS]->(c)
        """, nc=new_code, cid=str(case_id))
        s.run("""
            MATCH (c:Case {case_id:$cid})
            SET c.feature_scores = $fs
        """, cid=str(case_id), fs=json.dumps(new_scores, ensure_ascii=False))

def main():
    # 載入斷點
    done = set()
    if CHECKPOINT.exists():
        done = set(json.loads(CHECKPOINT.read_text()))
        print(f"[續跑] 已完成 {len(done)} 筆，繼續...")

    records = []
    with open(TENSORS_FILE) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    total = len(records)

    driver = GraphDatabase.driver(XRAG_URI, auth=(XRAG_USER, XRAG_PASS))
    log = open(LOG_FILE, "a")

    changed = 0
    same    = 0

    for i, rec in enumerate(records):
        cid = str(rec["case_id"])
        if cid in done:
            continue

        li_inj = rec.get("LI_injury", "")
        cur_score = rec["scores"]["P_Injury"]
        cur_level = score_to_level(cur_score)

        new_level = classify_injury(li_inj)
        new_score = INJURY_SCORE[new_level]

        progress = f"[{i+1:4d}/{total}] case {rec['case_id']:5} {cur_level}→{new_level}"

        if new_level != cur_level:
            # 更新 JSONL record
            rec["scores"]["P_Injury"] = new_score
            rec["tensor"][8]          = new_score
            rec.setdefault("fact_injury_matrix", {}).setdefault("Plaintiff", {})["Injury"] = new_level
            # 更新 Neo4j
            try:
                update_neo4j(driver, rec["case_id"], rec["litigant"],
                             cur_level, new_level, rec["scores"])
                log.write(f"{progress} ✓\n")
            except Exception as e:
                log.write(f"{progress} ERR: {e}\n")
            changed += 1
            print(progress)
        else:
            same += 1

        done.add(cid)

        # 每 50 筆存斷點 + 回寫 JSONL
        if len(done) % 50 == 0:
            CHECKPOINT.write_text(json.dumps(list(done)))
            # 回寫整個 JSONL（用 dict 快速查找）
            rec_dict = {str(r["case_id"]): r for r in records}
            with open(TENSORS_FILE, "w") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  [存檔] {len(done)}/{total} 完成，已變更 {changed} 筆")

    # 最終回寫
    with open(TENSORS_FILE, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    CHECKPOINT.write_text(json.dumps(list(done)))

    driver.close()
    log.write(f"\n=== 完成 changed={changed} same={same} ===\n")
    log.close()
    print(f"\n✅ 完成：{changed} 筆更新，{same} 筆不變")

if __name__ == "__main__":
    main()
