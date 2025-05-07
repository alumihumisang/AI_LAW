# KG_550_generate_semantic_summary.py：產生 semantic_text 並支援彈性欄位名稱與 JSONL 輸出
import os
import pandas as pd
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase, basic_auth
from tqdm import tqdm

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class CaseSummaryGenerator:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=basic_auth(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
        # 統一使用 description/value/text 欄位作為圖譜內容來源
        self.query_map = [
            ("Facts", "MATCH (c:Case {case_id: $case_id})-[:包含]->(f:Facts) RETURN f.description AS text"),
            ("Laws", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(l:Laws) RETURN l.description AS text"),
            ("LawDetail", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(:Laws)-[:包含]->(d:LawDetail) RETURN d.description AS text"),
            ("Compensation", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(:Laws)-[:計算]->(cm:Compensation) RETURN cm.description AS text"),
            ("CompensationDetail", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(:Laws)-[:計算]->(:Compensation)-[:包含]->(cmd:CompensationDetail) RETURN cmd.description AS text"),
            ("Conclusion", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(:Laws)-[:計算]->(:Compensation)-[:推導]->(con:Conclusion) RETURN con.description AS text"),
            ("ConclusionDetail", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(:Laws)-[:計算]->(:Compensation)-[:推導]->(:Conclusion)-[:包含]->(cond:ConclusionDetail) RETURN cond.value AS text"),
            ("LawyerInput", "MATCH (c:Case {case_id: $case_id})-[:包含]->(li:LawyerInput) RETURN li.text AS text"),
            ("LawyerInput_Cause", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:LawyerInput)-[:因]->(cause:LawyerInput_Cause) RETURN cause.text AS text"),
            ("LawyerInput_Effect", "MATCH (c:Case {case_id: $case_id})-[:包含]->(:LawyerInput)-[:果]->(eff:LawyerInput_Effect) RETURN eff.text AS text")
        ]

    def close(self):
        self.driver.close()

    def fetch_case_ids(self):
        with self.driver.session() as session:
            result = session.run("MATCH (c:Case) RETURN c.case_id AS case_id, elementId(c) AS eid ORDER BY c.case_id")
            all_records = []
            missing_records = []
            for record in result:
                case_id = record["case_id"]
                eid = record["eid"]
                if case_id is None or str(case_id).strip() == "":
                    print(f"⚠️ 節點 {eid} 沒有有效的 case_id，已略過")
                    missing_records.append({"element_id": eid})
                else:
                    all_records.append(case_id)
            if missing_records:
                pd.DataFrame(missing_records).to_excel("missing_case_id_nodes.xlsx", index=False)
                print(f"⚠️ 共 {len(missing_records)} 筆節點缺少 case_id，已匯出至 missing_case_id_nodes.xlsx")
            return all_records

    def build_semantic_dict_from_case(self, case_id):
        def fetch_texts(session, query, parameters):
            result = session.run(query, parameters)
            return [record["text"] for record in result if record["text"] and record["text"].strip() != ""]

        with self.driver.session() as session:
            summary_dict = {"case_id": case_id, "segments": []}
            for label, query in self.query_map:
                texts = fetch_texts(session, query, {"case_id": case_id})
                if texts:
                    summary_dict["segments"].append({"section": label, "content": texts})
            return summary_dict

    def export_jsonl_summary(self, output_path="semantic_summaries.jsonl"):
        case_ids = self.fetch_case_ids()
        with open(output_path, "w", encoding="utf-8") as f:
            for cid in tqdm(case_ids):
                summary_obj = self.build_semantic_dict_from_case(cid)
                f.write(json.dumps(summary_obj, ensure_ascii=False) + "\n")
        print(f"✅ 已輸出 JSONL 格式語意摘要至：{output_path}")

if __name__ == "__main__":
    generator = CaseSummaryGenerator()
    try:
        generator.export_jsonl_summary("semantic_summaries.jsonl")
    finally:
        generator.close()
