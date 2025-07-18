# 1. KG_setting.py
# 設置案件-事實-法條-賠償-結論
import logging
import os
import time
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入 `.env` 環境變數
load_dotenv()

# 設置 logging 紀錄日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# 讀取 Neo4j 連線資訊
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class Neo4jLegalGraph:
    def __init__(self):
        """ 初始化 Neo4j 連線 """
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        logger.info("成功連接至 Neo4j 資料庫")

    def close(self):
        """ 關閉 Neo4j 連線 """
        self.driver.close()
        logger.info("已關閉 Neo4j 連線")

    def create_case_graph(self, case_id, facts, laws, compensation, conclusion, case_type=None):
        """ 建立案件知識圖譜，主幹節點皆以 case_id 為 MERGE 條件，避免重複 """
        
        # 注意：不再設定case_type到Neo4j，因為LLM判斷可能有誤
        # case_type僅保留在ES中使用
        
        with self.driver.session() as session:
            session.run(
                """
                MERGE (c:Case {id: $case_id})
                SET c.name = "案件 " + $case_id,
                    c.case_id = $case_id
                    

                MERGE (f:Facts {case_id: $case_id})
                SET f.description = $facts

                MERGE (l:Laws {case_id: $case_id})
                SET l.description = $laws

                MERGE (comp:Compensation {case_id: $case_id})
                SET comp.description = $compensation

                MERGE (con:Conclusion {case_id: $case_id})
                SET con.description = $conclusion

                MERGE (c)-[:包含]->(f)
                MERGE (f)-[:適用]->(l)
                MERGE (l)-[:計算]->(comp)
                MERGE (comp)-[:推導]->(con)
                """,
                {
                    "case_id": case_id,
                    "facts": facts,
                    "laws": laws,
                    "compensation": compensation,
                    "conclusion": conclusion,
                },
            )
            logger.info(f"✅ 已建立案件 {case_id} 的主幹節點與關係")

    def process_cases(self, file_path, sheet_name):
        """ 讀取 Excel，處理並建立知識圖譜 """
        logger.info(f"讀取 Excel 檔案: {file_path}")
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

        logger.info("開始建立知識圖譜...")
        for _, row in df.iterrows():
            self.create_case_graph(
                case_id=row["case_id"],
                facts=row["事實概述"],
                laws=row["法條引用"],
                compensation=row["損害賠償項目"],
                conclusion=row["結論"],
            )
        logger.info("✅ 所有案件知識圖譜建立完成！")

if __name__ == "__main__":
    start_time = time.time()
    
    file_path = input("請輸入 Excel 檔案路徑: ").strip()
    sheet_name = input("請輸入要使用的工作表名稱: ").strip()
    
    neo4j_system = Neo4jLegalGraph()
    try:
        neo4j_system.process_cases(file_path, sheet_name)
    finally:
        neo4j_system.close()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    logger.info(f"\nTotal execution time: {hours}h {minutes}m {seconds}s")
    print(f"\nTotal execution time: {hours}h {minutes}m {seconds}s")
