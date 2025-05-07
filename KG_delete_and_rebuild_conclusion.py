# KG_delete_and_rebuild_conclusion.py
# 刪除並重建結論節點
import logging
import os
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入 `.env` 環境變數
load_dotenv()

# 設置 logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# 讀取 Neo4j 連線資訊
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Neo4jConclusionUpdater:
    def __init__(self):
        """ 初始化 Neo4j 連線 """
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        logger.info("✅ 成功連接至 Neo4j 資料庫")

    def close(self):
        """ 關閉 Neo4j 連線 """
        self.driver.close()
        logger.info("✅ 已關閉 Neo4j 連線")

    def delete_old_conclusions(self):
        """ 刪除所有舊的 Conclusion 節點及其關聯 """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (comp:Compensation)-[r:推導]->(c:Conclusion)
                DELETE r, c;
                """
            )
            logger.info("🗑️ 已刪除所有舊的 Conclusion 節點")

    def add_new_conclusions(self, case_id, conclusion_text):
        """ 為每個 Compensation 重新建立 Conclusion 節點 """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (c:Case {id: $case_id})-[:包含]->(f:Facts)-[:適用]->(l:Laws)-[:計算]->(comp:Compensation)
                MERGE (new_con:Conclusion {case_id: $case_id})
                SET new_con.description = $conclusion_text
                MERGE (comp)-[:推導]->(new_con);
                """,
                {
                    "case_id": case_id,
                    "conclusion_text": conclusion_text,
                },
            )
            logger.info(f"✅ 已為案件 {case_id} 更新新的 Conclusion 節點")

    def process_conclusions(self, file_path, sheet_name):
        """ 讀取 Excel，處理並更新所有 Compensation 的 Conclusion """
        logger.info(f"📥 讀取 Excel 檔案: {file_path}")
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

        logger.info("📌 開始更新 Conclusion 節點...")
        for _, row in df.iterrows():
            self.add_new_conclusions(
                case_id=row["case_id"], conclusion_text=row["結論"]
            )

        logger.info("✅ 所有 Compensation 節點的 Conclusion 更新完成！")

if __name__ == "__main__":
    file_path = input("📂 請輸入 Excel 檔案路徑: ").strip()
    sheet_name = input("📑 請輸入要使用的工作表名稱: ").strip()
    
    neo4j_system = Neo4jConclusionUpdater()
    try:
        # 1. 先刪除舊的 Conclusion
        neo4j_system.delete_old_conclusions()

        # 2. 讀取 Excel 並新增新的 Conclusion
        neo4j_system.process_conclusions(file_path, sheet_name)
    finally:
        neo4j_system.close()
    
    logger.info("🚀 知識圖譜 Conclusion 更新完成！")
