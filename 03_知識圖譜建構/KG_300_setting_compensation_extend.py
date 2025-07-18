# 3. KG_setting_compensation_extend.py
# 設置賠償細節
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

class Neo4jCompensationExtension:
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

    def extend_compensations_for_case(self, case_id, item_name, item_text):
        """ 
        在已經存在的 "Compensation" 節點下，新增 "賠償細節" (CompensationDetail)
        - "案件 (Case)" -> [:包含] -> "Facts"
        - "Facts" -> [:適用] -> "Laws"
        - "Laws" -> [:計算] -> "Compensation"
        - "Compensation" -> [:包含] -> "賠償細節 (CompensationDetail)"
        """
        with self.driver.session() as session:
            session.run(
                """
                // 透過 Facts 和 Laws 找到該案件的 Compensation
                MATCH (c:Case {id: $case_id})-[:包含]->(f:Facts)-[:適用]->(l:Laws)-[:計算]->(comp:Compensation)

                // 確保該案件的 "賠償細節" (CompensationDetail) 被創建
                MERGE (comp_detail:CompensationDetail {case_id: $case_id, name: $item_name})
                SET comp_detail.text = $item_text,
                    comp_detail.case_id = $case_id

                // 讓 Compensation 直接連結到 CompensationDetail
                MERGE (comp)-[:包含]->(comp_detail)
                """,
                {
                    "case_id": case_id,
                    "item_name": item_name,
                    "item_text": item_text,
                },
            )
            logger.info(f"✅ 已為案件 {case_id} 的 'Compensation' 節點增加賠償細節: {item_name}")



    def process_compensations(self, file_path, sheet_name):
        """ 讀取 Excel，處理並為每篇 "Compensation" 建立賠償細節 """
        logger.info(f"📥 讀取 Excel 檔案: {file_path}")
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

        logger.info("📌 開始更新知識圖譜中的 'Compensation' 節點...")
        for _, row in df.iterrows():
            case_id = row["case_id"]
            for col in df.columns:
                if col.startswith("項目") and pd.notna(row[col]):  # 過濾 "項目1", "項目2"...
                    item_name = col
                    item_text = row[col]
                    self.extend_compensations_for_case(case_id, item_name, item_text)

        logger.info("✅ 所有 'Compensation' 節點更新完成！")

if __name__ == "__main__":
    file_path = input("📂 請輸入 Excel 檔案路徑: ").strip()
    sheet_name = input("📑 請輸入要使用的工作表名稱: ").strip()
    
    neo4j_system = Neo4jCompensationExtension()
    try:
        neo4j_system.process_compensations(file_path, sheet_name)
    finally:
        neo4j_system.close()
    
    logger.info("🚀 知識圖譜 'Compensation' 節點擴充完成！")
