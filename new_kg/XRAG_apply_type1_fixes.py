"""
Type 1 修正：LLM 判定 single，但 fact_text 明確有兩個被告/原告
經人工確認的安全修正清單（共 18 筆）
"""
import json
from pathlib import Path
from neo4j import GraphDatabase

TENSORS_FILE = Path(__file__).parent / "phase1_tensors_v4.jsonl"

XRAG_URI  = "neo4j+s://3a29e735.databases.neo4j.io"
XRAG_USER = "3a29e735"
XRAG_PASS = "WSsO9OxVIn_mk31PiDOyMeZgjJ5epEPtOTVfHtuVYE8"

# { case_id: (old_L1,old_L2,old_L3,old_L4) → (new_L1,new_L2,new_L3,new_L4) }
# D side fixes: L3=1→0, L4=0→1 (person + company 共同被告)
# P side fixes: L1=1→0, L2=0→1 (two plaintiffs)
FIXES = {
    # D side (被告：自然人 + 公司)
    "645":  ((1,0,1,0), (1,0,0,1)),
    "2578": ((1,0,1,0), (1,0,0,1)),
    "2875": ((1,0,1,0), (1,0,0,1)),
    "4111": ((1,0,1,0), (1,0,0,1)),
    "4272": ((1,0,1,0), (1,0,0,1)),
    "4464": ((1,0,1,0), (1,0,0,1)),
    "4509": ((1,0,1,0), (1,0,0,1)),
    "4819": ((1,0,1,0), (1,0,0,1)),
    "4838": ((1,0,1,0), (1,0,0,1)),
    "4853": ((0,1,1,0), (0,1,0,1)),  # P side already L2=1, only D changes
    "4864": ((1,0,1,0), (1,0,0,1)),
    "5377": ((1,0,1,0), (1,0,0,1)),
    "5582": ((1,0,1,0), (1,0,0,1)),
    "5583": ((1,0,1,0), (1,0,0,1)),
    "5664": ((1,0,1,0), (1,0,0,1)),
    "5704": ((1,0,1,0), (1,0,0,1)),
    # P side (原告：受僱人 + 公司)
    "3622": ((1,0,0,1), (0,1,0,1)),
    "5694": ((1,0,0,1), (0,1,0,1)),
}


def score_to_level(s: float) -> str:
    if s > 0.85: return "A"
    if s > 0.65: return "B"
    if s > 0.45: return "C"
    if s > 0.15: return "D"
    if s < 0:    return "E"
    return "N"


def update_trie(driver, case_id, old_lig, new_lig, scores):
    old_root = f"L{old_lig['L1']}{old_lig['L2']}{old_lig['L3']}{old_lig['L4']}"
    new_root = f"L{new_lig['L1']}{new_lig['L2']}{new_lig['L3']}{new_lig['L4']}"

    df_score = scores.get("D_Fact", 0.0)
    pi_score = scores.get("P_Injury", 0.0)
    df_level = score_to_level(df_score)
    pi_level = score_to_level(pi_score)

    old_l3  = f"{old_root}_DF_{df_level}_PI_{pi_level}"
    new_l2  = f"{new_root}_DF_{df_level}"
    new_l3  = f"{new_l2}_PI_{pi_level}"

    with driver.session() as s:
        s.run("MERGE (:LitigantConfig {code: $c})", c=new_root)
        s.run("MERGE (:FeatureNode {code: $c})", c=new_l2)
        s.run("MERGE (:FeatureNode {code: $c})", c=new_l3)
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
        s.run("""
            MATCH ({code: $old_leaf})-[r:CONTAINS]->(c:Case {case_id: $cid})
            DELETE r
        """, old_leaf=old_l3, cid=case_id)
        s.run("""
            MATCH (leaf {code: $new_leaf}), (c:Case {case_id: $cid})
            MERGE (leaf)-[:CONTAINS]->(c)
            SET c.litigant_code = $new_root
        """, new_leaf=new_l3, cid=case_id, new_root=new_root)


def main():
    print("=== Type 1 修正：18 筆 ===")

    records = {}
    with open(TENSORS_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                records[str(rec["case_id"])] = rec

    driver = GraphDatabase.driver(XRAG_URI, auth=(XRAG_USER, XRAG_PASS))
    changed = 0

    for cid, (old_tuple, new_tuple) in sorted(FIXES.items(), key=lambda x: int(x[0])):
        rec = records.get(cid)
        if not rec:
            print(f"  [警告] case {cid} 不存在")
            continue

        old_lig = rec["litigant"]
        actual  = (old_lig["L1"], old_lig["L2"], old_lig["L3"], old_lig["L4"])
        if actual != old_tuple:
            print(f"  [跳過] case {cid} 實際={actual} 不符預期 {old_tuple}")
            continue

        new_lig = {"L1": new_tuple[0], "L2": new_tuple[1],
                   "L3": new_tuple[2], "L4": new_tuple[3]}
        old_code = f"L{old_tuple[0]}{old_tuple[1]}{old_tuple[2]}{old_tuple[3]}"
        new_code = f"L{new_tuple[0]}{new_tuple[1]}{new_tuple[2]}{new_tuple[3]}"
        print(f"  case {cid:>5}  {old_code} → {new_code}")

        # 更新 JSONL record
        rec["litigant"] = new_lig
        t = rec["tensor"]
        t[0], t[1], t[2], t[3] = new_lig["L1"], new_lig["L2"], new_lig["L3"], new_lig["L4"]
        rec["tensor"] = t
        records[cid] = rec

        update_trie(driver, cid, old_lig, new_lig, rec["scores"])
        changed += 1

    driver.close()

    # 覆蓋 JSONL
    tmp = TENSORS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records.values():
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.rename(TENSORS_FILE)

    print(f"\n完成：更新 {changed} 筆，JSONL 已覆蓋")


if __name__ == "__main__":
    main()
