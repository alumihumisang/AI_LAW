# KG_4.75_setting_conclusion_extend.py
# 新增或更新 ConclusionDetail，不會刪除任何舊資料

import logging
import os
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入 .env 環境變數
load_dotenv()

# 設置 logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Neo4j 連線資訊
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Neo4jConclusionUpdater:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        logger.info("✅ 成功連接至 Neo4j")

    def close(self):
        self.driver.close()
        logger.info("✅ 已關閉 Neo4j 連線")

    def add_or_update_detail(self, case_id, detail_name, detail_value):
        with self.driver.session() as session:
            session.run(
                """
                MATCH (con:Conclusion {case_id: $case_id})
                MERGE (cd:ConclusionDetail {case_id: $case_id, name: $detail_name})
                SET cd.value = $detail_value,
                    cd.case_id = $case_id
                MERGE (con)-[:包含]->(cd)
                """,
                {
                    "case_id": case_id,
                    "detail_name": detail_name,
                    "detail_value": detail_value,
                },
            )
            logger.info(f"✅ 案件 {case_id} ➜ 結論細節：{detail_name} = {detail_value}")

    def process_excel(self, file_path, sheet_name):
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
        logger.info(f"📥 已讀取 Excel：{file_path}")

        for _, row in df.iterrows():
            case_id = row["case_id"]
            for col in [
                "單一原告總計金額(不含肇事責任)", 
                "單一原告總計金額(不含肇事責任且已根據事實扣除費用)", 
                "多名原告總計金額(不含肇事責任)", 
                "多名原告總計金額(不含肇事責任且已根據事實扣除費用)"
            ]:
                if col in row and pd.notna(row[col]):
                    self.add_or_update_detail(case_id, col, row[col])

        logger.info("🚀 所有 ConclusionDetail 新增/更新完成！")

if __name__ == "__main__":
    file_path = input("📂 請輸入 Excel 檔案路徑: ").strip()
    sheet_name = input("📑 請輸入要使用的工作表名稱: ").strip()

    updater = Neo4jConclusionUpdater()
    try:
        updater.process_excel(file_path, sheet_name)
    finally:
        updater.close()
