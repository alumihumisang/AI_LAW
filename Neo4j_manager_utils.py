# Neo4j_manager_utils.py
from neo4j import GraphDatabase
from typing import List, Dict
import os
from dotenv import load_dotenv

load_dotenv()

class Neo4jManager:
    def __init__(self, uri=None, user=None, password=None, logger=None):
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USERNAME")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.logger = logger

        print(f"🔍 Connecting to Neo4j at {self.uri} with user {self.user}")

        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            print("✅ 成功連接 Neo4j")
        except Exception as e:
            print(f"❌ 連接 Neo4j 失敗: {e}")
            raise e

    def close(self):
        if self.driver:
            self.driver.close()

    def query_related_cases(self, query_text: str, top_k: int = 5) -> List[Dict]:
        """
        根據最新圖譜結構查詢：
        Case → Facts → Laws → LawDetail → Compensation → CompensationDetail → Conclusion → ConclusionDetail
        並包含模擬律師輸入的因果關係（LawyerInput → Cause / Effect）。
        """
        query = """
        MATCH (c:Case)-[:包含]->(f:Facts)-[:適用]->(l:Laws)-[:包含]->(ld:LawDetail)
                      -[:計算]->(comp:Compensation)-[:包含]->(compd:CompensationDetail)
                      -[:推導]->(con:Conclusion)-[:包含]->(cd:ConclusionDetail)
        OPTIONAL MATCH (c)-[:包含]->(li:LawyerInput)-[:因|:果]->(le)
        WHERE f.text CONTAINS $query_text OR ld.text CONTAINS $query_text OR compd.text CONTAINS $query_text 
              OR cd.value CONTAINS $query_text OR le.text CONTAINS $query_text
        RETURN c.id AS case_id, f.text AS case_description, 
               collect(DISTINCT ld.text) + collect(DISTINCT compd.text) + 
               collect(DISTINCT cd.value) + collect(DISTINCT le.text) AS related_chunks
        LIMIT $top_k
        """
        with self.driver.session() as session:
            results = session.run(query, query_text=query_text, top_k=top_k)
            return [
                {
                    "case_id": record["case_id"],
                    "case_description": record["case_description"],
                    "related_chunks": record["related_chunks"]
                }
                for record in results
            ]
            
    # def get_related_laws(self, query_text: str, top_k: int = 5) -> List[Dict]:
    #     """
    #     根據輸入文字查詢相關法條。
    #     假設資料模型中，法條節點 (Laws) 與法條細節 (LawDetail) 之間存在「包含」關係。
    #     """
    #     query = """
    #     MATCH (l:Laws)-[:包含]->(ld:LawDetail)
    #     WHERE l.name CONTAINS $query_text OR ld.text CONTAINS $query_text
    #     RETURN l.name AS name, ld.text AS text
    #     LIMIT $top_k
    #     """
    #     with self.driver.session() as session:
    #         results = session.run(query, query_text=query_text, top_k=top_k)
    #         return [{"name": record["name"], "text": record["text"]} for record in results]

