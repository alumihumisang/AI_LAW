# KG_5_import_lawyer_input.py
# 修正版：所有節點皆含 case_id 屬性

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

class Neo4jLawyerInputImporter:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        logger.info("✅ 成功連接至 Neo4j 資料庫")

    def close(self):
        self.driver.close()
        logger.info("✅ 已關閉 Neo4j 連線")

    def add_lawyer_input(self, case_id, full_text, cause_text, effect_text):
        with self.driver.session() as session:
            # 1. 主節點：LawyerInput
            session.run(
                """
                MATCH (c:Case {id: $case_id})
                MERGE (input:LawyerInput {case_id: $case_id})
                SET input.text = $full_text,
                    input.case_id = $case_id
                MERGE (c)-[:包含]->(input)
                """,
                {"case_id": case_id, "full_text": full_text},
            )

            # 2. 因：LawyerInput_Cause
            session.run(
                """
                MATCH (input:LawyerInput {case_id: $case_id})
                MERGE (cause:LawyerInput_Cause {case_id: $case_id})
                SET cause.text = $cause_text,
                    cause.case_id = $case_id
                MERGE (input)-[:因]->(cause)
                """,
                {"case_id": case_id, "cause_text": cause_text},
            )

            # 3. 果：LawyerInput_Effect
            session.run(
                """
                MATCH (input:LawyerInput {case_id: $case_id})
                MERGE (effect:LawyerInput_Effect {case_id: $case_id})
                SET effect.text = $effect_text,
                    effect.case_id = $case_id
                MERGE (input)-[:果]->(effect)
                """,
                {"case_id": case_id, "effect_text": effect_text},
            )

            logger.info(f"✅ 已為案件 {case_id} 新增 LawyerInput 及因果細節")

    def process_lawyer_inputs(self, file_path, sheet_name):
        logger.info(f"📥 讀取 Excel 檔案: {file_path}")
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

        logger.info("📌 開始導入 LawyerInput 節點...")
        for _, row in df.iterrows():
            self.add_lawyer_input(
                case_id=row["case_id"],
                full_text=row["律師輸入"],
                cause_text=row["緣由"],
                effect_text=row["後果"],
            )

        logger.info("✅ 所有 LawyerInput 節點導入完成！")

if __name__ == "__main__":
    file_path = input("\U0001F4C2 請輸入 Excel 檔案路徑: ").strip()
    sheet_name = input("📑 請輸入要使用的工作表名稱: ").strip()

    neo4j_system = Neo4jLawyerInputImporter()
    try:
        neo4j_system.process_lawyer_inputs(file_path, sheet_name)
    finally:
        neo4j_system.close()

    logger.info("\U0001F680 知識圖譜 LawyerInput 導入完成！")