#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KG_360: 建立標準化的 LawDetail 節點到 Neo4j
從 Excel 讀取法條命中情況，為每個命中的法條建立 Detail 節點
"""

import pandas as pd
import os
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kg_360_build_law_details.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# 法條標準內容對應表
LAW_ARTICLES = {
    "民法第184條第1項前段": "因故意或過失，不法侵害他人之權利者，負損害賠償責任。",
    "民法第185條第1項": "數人共同不法侵害他人之權利者，連帶負損害賠償責任。",
    "民法第187條第1項": "無行為能力人或限制行為能力人，不法侵害他人之權利者，以行為時有識別能力為限，與其法定代理人連帶負損害賠償責任。",
    "民法第188條第1項": "受僱人因執行職務，不法侵害他人之權利者，由僱用人與行為人連帶負損害賠償責任。",
    "民法第190條第1項": "動物加損害於他人者，由其占有人負損害賠償責任。但依動物之種類及性質已為相當注意之管束，或縱為相當注意之管束而仍不免發生損害者，不在此限。",
    "民法第191條之2": "汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。但於防止損害之發生，已盡相當之注意者，不在此限。",
    "民法第193條第1項": "不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。",
    "民法第195條第1項前段": "不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。",
    "民法第213條第1項": "負損害賠償責任者，除法律另有規定或契約另有訂定外，應回復他方損害發生前之原狀。",
    "民法第216條第1項": "損害賠償，除法律另有規定或契約另有訂定外，應以填補債權人所受損害及所失利益為限。",
    "民法第217條第1項": "損害之發生或擴大，被害人與有過失者，法院得減輕賠償金額，或免除之。"
}

class LawDetailBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        logger.info(f"✅ 已連接到 Neo4j: {NEO4J_URI}")

    def close(self):
        self.driver.close()
        logger.info("🔌 已關閉 Neo4j 連接")

    def create_law_detail_node(self, session, case_id, article_name, article_content):
        """
        建立 LawDetail 節點並連接到 Laws 節點

        節點結構：
        - article: 法條名稱（例如：民法第184條第1項前段）
        - content: 法條內容
        - case_id: 案件 ID
        """
        query = """
        // 找到對應的 Laws 節點
        MATCH (case:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(laws:Laws)

        // 建立 LawDetail 節點
        CREATE (detail:LawDetail {
            article: $article_name,
            content: $article_content,
            case_id: $case_id
        })

        // 建立關係
        CREATE (laws)-[:HAS_DETAIL]->(detail)

        RETURN detail.article as created_article
        """

        params = {
            'case_id': int(case_id),
            'article_name': article_name,
            'article_content': article_content
        }

        try:
            result = session.run(query, params)
            return result.single()
        except Exception as e:
            logger.error(f"❌ 建立節點失敗 case_id={case_id}, article={article_name}: {e}")
            return None

    def process_law_excel(self, excel_file):
        """
        讀取法條 Excel，建立 LawDetail 節點
        """
        logger.info(f"📂 讀取檔案: {excel_file}")
        df = pd.read_excel(excel_file, sheet_name='6057法條')

        logger.info(f"📊 共有 {len(df)} 個案件")

        # 法條欄位（排除 case_id 和 法條引用）
        law_columns = [col for col in df.columns if col not in ['case_id', '法條引用']]

        success_count = 0
        error_count = 0
        total_details = 0

        with self.driver.session() as session:
            for idx, row in tqdm(df.iterrows(), total=len(df), desc="建立 LawDetail 節點"):
                case_id = row['case_id']

                # 檢查每個法條是否命中
                for article_name in law_columns:
                    if row[article_name] == 'O':  # 命中該法條
                        article_content = LAW_ARTICLES.get(article_name)

                        if article_content:
                            result = self.create_law_detail_node(
                                session, case_id, article_name, article_content
                            )

                            if result:
                                success_count += 1
                            else:
                                error_count += 1
                        else:
                            logger.warning(f"⚠️  找不到法條內容: {article_name}")
                            error_count += 1

                        total_details += 1

                # 每 500 筆輸出進度
                if (idx + 1) % 500 == 0:
                    logger.info(f"✅ 已處理 {idx + 1}/{len(df)} 個案件，建立 {success_count} 個 LawDetail 節點")

        logger.info(f"""
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        🎉 處理完成！
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ✅ 成功建立: {success_count:,} 個 LawDetail 節點
        ❌ 失敗: {error_count} 個
        📊 總計處理: {total_details:,} 個法條命中
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

    def verify_results(self):
        """
        驗證建立的節點數量
        """
        with self.driver.session() as session:
            # 統計 LawDetail 節點數量
            result = session.run("""
                MATCH (d:LawDetail)
                RETURN count(d) as total_count
            """)
            total_count = result.single()['total_count']

            logger.info(f"\n📊 LawDetail 節點總數: {total_count:,} 個")

            # 統計各法條的節點數量
            result = session.run("""
                MATCH (d:LawDetail)
                RETURN d.article as article, count(*) as count
                ORDER BY count DESC
            """)

            logger.info("\n📊 各法條的節點數量：")
            for record in result:
                logger.info(f"  {record['article']}: {record['count']:,} 個")

            # 檢查孤立節點
            result = session.run("""
                MATCH (d:LawDetail)
                WHERE NOT exists((d)<-[:HAS_DETAIL]-())
                RETURN count(d) as orphan_count
            """)

            orphan_count = result.single()['orphan_count']
            if orphan_count > 0:
                logger.warning(f"⚠️  發現 {orphan_count:,} 個孤立節點（未連接到 Laws）")
            else:
                logger.info("✅ 所有 LawDetail 節點都已正確連接")


def main():
    excel_file = "/home/aru/AI_LAW/09_輸入輸出資料/整合_起訴書_四段(FINAL)_6057.xlsx"

    if not os.path.exists(excel_file):
        logger.error(f"❌ 找不到檔案: {excel_file}")
        return

    builder = LawDetailBuilder()

    try:
        builder.process_law_excel(excel_file)
        builder.verify_results()
    finally:
        builder.close()

    logger.info("🎉 完成！")


if __name__ == "__main__":
    main()
