"""
XRAG Phase 2: Ontology Graph Construction
從 Phase 1 的 tensor JSONL 建構 Neo4j 知識圖譜

Trie 結構（固定 3 層）：
  L1: LitigantConfig   e.g. L1010
  L2: DF 節點          e.g. L1010_DF_B        （Defendant Fact 等級）
  L3: DF+PI 葉節點     e.g. L1010_DF_B_PI_C   （+ Plaintiff Injury 等級）
  Case: 掛在葉節點下，存完整文本與所有特徵屬性

Hash Code 公式：Hash = L ∥ DF_ℓ_D ∥ PI_ℓ_P
  - L    = 訴訟結構代碼（L1/L2/L3/L4 各 0 或 1）
  - DF   = Defendant Fact 特徵標識
  - PI   = Plaintiff Injury 特徵標識
  - ℓ_D  = D_Fact 等級字母（A/B/C/D/E/N）
  - ℓ_P  = P_Injury 等級字母（A/B/C/D/E/N）

Case 節點屬性（不進 Trie）：
  - comp_level:       Plaintiff Comp 等級字母
  - has_vicarious:    是否有替代責任人（V_Fact 或 V_Injury 非零）
  - has_insurance:是否有強制險已賠扣除項（E_Comp < 0）
  - 所有原始文本段落、feature_scores、tensor
"""

import json
import re
import pandas as pd
from pathlib import Path
from neo4j import GraphDatabase

EXCEL_PATH = Path("/home/aru/AI_LAW/6057起訴書_全.xlsx")
ART_VICARIOUS = re.compile(r'第\s*18[78]\s*條')  # 187未成年、188僱用人

# ── 設定 ──────────────────────────────────────────────
XRAG_URI  = "neo4j+s://3a29e735.databases.neo4j.io"
XRAG_USER = "3a29e735"
XRAG_PASS = "WSsO9OxVIn_mk31PiDOyMeZgjJ5epEPtOTVfHtuVYE8"

TENSORS_FILE      = Path(__file__).parent / "phase1_tensors_v4.jsonl"
LAWYER_INPUT_FILE = Path("/home/aru/AI_LAW/09_輸入輸出資料/6057律師輸入.xlsx")

BATCH_SIZE = 50


# ── Score → 等級字母 ──────────────────────────────────
def score_to_level(s: float) -> str:
    if s > 0.85:  return "A"
    if s > 0.65:  return "B"
    if s > 0.45:  return "C"
    if s > 0.15:  return "D"
    if s < 0:     return "E"
    return "N"


# ── 建立 Trie 路徑（固定 3 層） ───────────────────────
def build_trie_path(record: dict) -> list[tuple]:
    """
    Returns list of (node_code, label, edge_feature, edge_score)
    L1: LitigantConfig root
    L2: DF level node
    L3: DF+PI leaf node
    """
    lig    = record["litigant"]
    scores = record["scores"]

    # L1: LitigantConfig root — L{L1}{L2}{L3}{L4}
    root_code = f"L{lig['L1']}{lig['L2']}{lig['L3']}{lig['L4']}"
    path = [(root_code, "LitigantConfig", None, None)]

    # L2: Defendant Fact level
    df_score = scores.get("D_Fact", 0.0)
    df_level = score_to_level(df_score)
    l2_code  = f"{root_code}_DF_{df_level}"
    path.append((l2_code, "FeatureNode", "D_Fact", df_score))

    # L3: Plaintiff Injury level (leaf)
    pi_score = scores.get("P_Injury", 0.0)
    pi_level = score_to_level(pi_score)
    l3_code  = f"{l2_code}_PI_{pi_level}"
    path.append((l3_code, "FeatureNode", "P_Injury", pi_score))

    return path


# ── 讀取律師輸入 ──────────────────────────────────────
def load_lawyer_inputs() -> dict:
    df = pd.read_excel(LAWYER_INPUT_FILE)
    return {str(row["case_id"]): row["律師輸入"] or "" for _, row in df.iterrows()}

def load_vicarious_by_law() -> set:
    """用法條 187/188 確定性偵測連帶責任案件"""
    from chunk_utils import chunk_indictment
    df = pd.read_excel(EXCEL_PATH)
    result = set()
    for _, row in df.iterrows():
        text   = str(row["起訴書"])
        chunks = chunk_indictment(text)
        laws   = chunks["laws_text"] + chunks["fact_text"]
        if ART_VICARIOUS.search(laws):
            result.add(str(row["case_id"]))
    return result


# ── 批次建圖（UNWIND） ────────────────────────────────
def build_graph(driver, records: list, lawyer_inputs: dict, vicarious_ids: set):
    with driver.session() as s:

        nodes_to_merge = {}  # code → label
        edges_to_merge = []  # (from_code, to_code, feat, score_val)
        case_data      = []

        for rec in records:
            path   = build_trie_path(rec)
            scores = rec["scores"]

            # Trie 節點與邊
            for i, (code, label, edge_feat, edge_score) in enumerate(path):
                if code not in nodes_to_merge:
                    nodes_to_merge[code] = label
                if i > 0:
                    prev_code = path[i-1][0]
                    edges_to_merge.append((prev_code, code, edge_feat, edge_score))

            # Case 節點
            leaf_code = path[-1][0]
            cid       = rec["case_id"]

            # 不進 Trie 的特徵：Comp 等級、替代責任、強制險扣除
            p_comp_score      = scores.get("P_Comp", 0.0)
            has_vicarious = cid in vicarious_ids   # 法條 187/188 確定性偵測
            has_insurance = scores.get("E_Comp", 0.0) < 0

            case_data.append({
                "case_id":           cid,
                "leaf_code":         leaf_code,
                "fact_text":         rec.get("fact_text", ""),
                "laws_text":         rec.get("laws_text", ""),
                "compensation_text": rec.get("compensation_text", ""),
                "conclusion_text":   rec.get("conclusion_text", ""),
                "lawyer_input":      lawyer_inputs.get(cid, ""),
                "feature_scores":    json.dumps(rec.get("scores", {}), ensure_ascii=False),
                "tensor":            rec.get("tensor", []),
                "litigant_code":     path[0][0],
                "comp_level":        score_to_level(p_comp_score),
                "has_vicarious":     has_vicarious,
                "has_insurance": has_insurance,
                "comp_amount":  rec.get("comp_amount", 0),
            })

        # ── 批次建 Trie 節點 ──────────────────────────
        node_list = [{"code": code, "label": label}
                     for code, label in nodes_to_merge.items()]
        for i in range(0, len(node_list), BATCH_SIZE):
            batch = node_list[i:i+BATCH_SIZE]
            lc_batch = [n for n in batch if n["label"] == "LitigantConfig"]
            if lc_batch:
                s.run("UNWIND $rows AS row MERGE (:LitigantConfig {code: row.code})",
                      rows=lc_batch)
            fn_batch = [n for n in batch if n["label"] == "FeatureNode"]
            if fn_batch:
                s.run("UNWIND $rows AS row MERGE (:FeatureNode {code: row.code})",
                      rows=fn_batch)

        print(f"  Trie 節點建立完成：{len(nodes_to_merge)} 個")

        # ── 批次建 Trie 邊（去重） ─────────────────────
        seen_edges   = set()
        unique_edges = []
        for (fc, tc, feat, score_val) in edges_to_merge:
            key = (fc, tc)
            if key not in seen_edges:
                seen_edges.add(key)
                unique_edges.append({
                    "from_code": fc,
                    "to_code":   tc,
                    "feature":   feat,
                    "score":     score_val if score_val is not None else 0.0,
                })

        for i in range(0, len(unique_edges), BATCH_SIZE):
            batch = unique_edges[i:i+BATCH_SIZE]
            s.run("""
                UNWIND $rows AS row
                MATCH (a {code: row.from_code}), (b {code: row.to_code})
                MERGE (a)-[r:HAS_FEATURE {feature: row.feature}]->(b)
                SET r.score = row.score
            """, rows=batch)

        print(f"  Trie 邊建立完成：{len(unique_edges)} 條")

        # ── 批次建 Case 節點 ───────────────────────────
        for i in range(0, len(case_data), BATCH_SIZE):
            batch = case_data[i:i+BATCH_SIZE]
            s.run("""
                UNWIND $rows AS row
                MERGE (c:Case {case_id: row.case_id})
                SET c.fact_text          = row.fact_text,
                    c.laws_text          = row.laws_text,
                    c.compensation_text  = row.compensation_text,
                    c.conclusion_text    = row.conclusion_text,
                    c.lawyer_input       = row.lawyer_input,
                    c.feature_scores     = row.feature_scores,
                    c.tensor             = row.tensor,
                    c.litigant_code      = row.litigant_code,
                    c.comp_level         = row.comp_level,
                    c.has_vicarious      = row.has_vicarious,
                    c.has_insurance  = row.has_insurance,
                    c.comp_amount    = row.comp_amount
                WITH c, row
                MATCH (leaf {code: row.leaf_code})
                MERGE (leaf)-[:CONTAINS]->(c)
            """, rows=batch)

        print(f"  Case 節點建立完成：{len(case_data)} 個")


# ── 主程式 ────────────────────────────────────────────
def main():
    print("=== XRAG Phase 2: Build Knowledge Graph ===")

    records = []
    with open(TENSORS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    print(f"Phase 1 資料：{len(records)} 筆")

    lawyer_inputs = load_lawyer_inputs()
    print(f"律師輸入：{len(lawyer_inputs)} 筆")

    print("偵測連帶責任案件（法條 187/188）...")
    vicarious_ids = load_vicarious_by_law()
    print(f"連帶責任案件：{len(vicarious_ids)} 筆")

    driver = GraphDatabase.driver(XRAG_URI, auth=(XRAG_USER, XRAG_PASS))

    # 清除舊資料（正式執行時可移除）
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
    print("清除舊資料")

    build_graph(driver, records, lawyer_inputs, vicarious_ids)

    with driver.session() as s:
        cnt = s.run("MATCH (n) RETURN count(n) as c").single()["c"]
        rel = s.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
    print(f"\n完成！節點：{cnt}，關聯：{rel}")

    driver.close()


if __name__ == "__main__":
    main()
