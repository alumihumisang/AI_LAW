# 2. KG_setting_laws_extend.py
# 設置法條細節
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

class Neo4jLawExtension:
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

    def extend_laws_for_case(self, case_id, law_name, law_text):
        """ 
        在已經存在的 "Laws" 節點下，新增適用的 "法條細節" (LawDetail)。
        - "案件 (Case)" -> [:適用] -> "Laws"
        - "Laws" -> [:包含] -> "法條細節 (LawDetail)"
        """
        with self.driver.session() as session:
            session.run(
                """
                // 先找到該案件的 "Laws" 節點（不創建新的 Laws）
                MATCH (laws:Laws {case_id: $case_id})

                // 確保該案件的 "法條細節" (LawDetail) 被創建
                MERGE (law_detail:LawDetail {case_id: $case_id, name: $law_name})
                SET law_detail.text = $law_text,
                    law_detail.case_id = $case_id


                // 讓 "Laws" 直接連結到 "法條細節"
                MERGE (laws)-[:包含]->(law_detail)
                """,
                {
                    "case_id": case_id,
                    "law_name": law_name,
                    "law_text": law_text,
                },
            )
            logger.info(f"✅ 已為案件 {case_id} 的 'Laws' 節點增加法條細節: {law_name}")

    def process_laws(self, file_path, sheet_name):
        """ 讀取 Excel，處理並為每篇 "Laws" 建立法條細節 """
        logger.info(f"📥 讀取 Excel 檔案: {file_path}")
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

        # 定義完整法條對應的條文內容
        law_articles = {
            "民法第184條第1項前段": "因故意或過失，不法侵害他人之權利者，負損害賠償責任。故意以背於善良風俗之方法，加損害於他人者亦同。",
            "民法第185條第1項": "數人共同不法侵害他人之權利者，連帶負損害賠償責任。不能知其中孰為加害人者亦同。",
            "民法第187條第1項": "無行為能力人或限制行為能力人，不法侵害他人之權利者，以行為時有識別能力為限，與其法定代理人連帶負損害賠償責任。",
            "民法第188條第1項": "受僱人因執行職務，不法侵害他人之權利者，由僱用人與行為人連帶負損害賠償責任。但選任受僱人及監督其職務之執行，已盡相當之注意或縱加以相當之注意而仍不免發生損害者，僱用人不負賠償責任。",
            "民法第190條第1項": "動物加損害於他人者，由其占有人負損害賠償責任。但依動物之種類及性質已為相當注意之管束，或縱為相當注意之管束而仍不免發生損害者，不在此限。",
            "民法第191條之2": "汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。但於防止損害之發生，已盡相當之注意者，不在此限。",
            "民法第193條第1項": "不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。",
            "民法第195條第1項前段": "不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。其名譽被侵害者，並得請求回復名譽之適當處分。",
            "民法第213條第1項": "負損害賠償責任者，除法律另有規定或契約另有訂定外，應回復他方損害發生前之原狀。",
            "民法第216條第1項": "損害賠償，除法律另有規定或契約另有訂定外，應以填補債權人所受損害及所失利益為限。",
            "民法第217條第1項": "損害之發生或擴大，被害人與有過失者，法院得減輕賠償金額，或免除之。",
        }

        logger.info("📌 開始更新知識圖譜中的 'Laws' 節點...")
        for _, row in df.iterrows():
            for law_name in law_articles.keys():
                if law_name in row and row[law_name] == "O":  # 該案件引用了此法條
                    self.extend_laws_for_case(row["case_id"], law_name, law_articles[law_name])

        logger.info("✅ 所有 'Laws' 節點更新完成！")

if __name__ == "__main__":
    file_path = input("📂 請輸入 Excel 檔案路徑: ").strip()
    sheet_name = input("📑 請輸入要使用的工作表名稱: ").strip()
    
    neo4j_system = Neo4jLawExtension()
    try:
        neo4j_system.process_laws(file_path, sheet_name)
    finally:
        neo4j_system.close()
    
    logger.info("🚀 知識圖譜 'Laws' 節點擴充完成！")
