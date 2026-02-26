# KG_120_build_lawyer_input_nodes.py
# 建立律師輸入的三個主幹節點到 Neo4j

import pandas as pd
import logging
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class LawyerInputGraphBuilder:
    def __init__(self):
        """初始化 Neo4j 連線"""
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD),
        )
        logger.info("成功連接至 Neo4j 資料庫")

    def close(self):
        """關閉 Neo4j 連線"""
        self.driver.close()
        logger.info("已關閉 Neo4j 連線")

    def delete_old_lawyer_input_nodes(self):
        """刪除舊的 LawyerInput 節點（包含所有三種類型）"""
        with self.driver.session() as session:
            # 刪除 LawyerInput_Accident
            result = session.run("""
                MATCH (l:LawyerInput_Accident)
                DETACH DELETE l
                RETURN count(l) as deleted
            """)
            deleted_accident = result.single()['deleted']

            # 刪除 LawyerInput_Injury
            result = session.run("""
                MATCH (l:LawyerInput_Injury)
                DETACH DELETE l
                RETURN count(l) as deleted
            """)
            deleted_injury = result.single()['deleted']

            # 刪除 LawyerInput_Claim
            result = session.run("""
                MATCH (l:LawyerInput_Claim)
                DETACH DELETE l
                RETURN count(l) as deleted
            """)
            deleted_claim = result.single()['deleted']

            total = deleted_accident + deleted_injury + deleted_claim
            logger.info(f"✅ 已刪除 {total} 個舊的 LawyerInput 節點 (Accident:{deleted_accident}, Injury:{deleted_injury}, Claim:{deleted_claim})")

    def create_lawyer_input_nodes(self, case_id, accident, injury, claim):
        """
        建立三個律師輸入主幹節點並以鏈式結構連接

        節點結構（鏈式）：
        Case -[HAS_LAWYER_INPUT]-> LawyerInput_Accident (一、事故發生緣由)
                                        -[導致]-> LawyerInput_Injury (二、原告受傷情形)
                                                    -[請求]-> LawyerInput_Claim (三、請求賠償的事實根據)
        """
        with self.driver.session() as session:
            session.run(
                """
                MATCH (c:Case {case_id: $case_id})

                MERGE (accident:LawyerInput_Accident {case_id: $case_id})
                SET accident.description = $accident

                MERGE (injury:LawyerInput_Injury {case_id: $case_id})
                SET injury.description = $injury

                MERGE (claim:LawyerInput_Claim {case_id: $case_id})
                SET claim.description = $claim

                MERGE (c)-[:HAS_LAWYER_INPUT]->(accident)
                MERGE (accident)-[:導致]->(injury)
                MERGE (injury)-[:請求]->(claim)
                """,
                {
                    "case_id": int(case_id),
                    "accident": accident,
                    "injury": injury,
                    "claim": claim,
                }
            )

    def process_lawyer_inputs(self, file_path):
        """讀取切分後的 Excel，建立律師輸入節點"""
        logger.info(f"讀取檔案: {file_path}")
        df = pd.read_excel(file_path, sheet_name="律師輸入_三段")

        logger.info(f"共有 {len(df)} 筆律師輸入資料")

        for idx, row in df.iterrows():
            self.create_lawyer_input_nodes(
                case_id=row['case_id'],
                accident=row['一、事故發生緣由'],
                injury=row['二、原告受傷情形'],
                claim=row['三、請求賠償的事實根據']
            )

            if (idx + 1) % 500 == 0:
                logger.info(f"✅ 已建立 {idx + 1} 筆案件的律師輸入節點")

        logger.info("✅ 所有律師輸入節點建立完成！")

    def verify_nodes(self):
        """驗證節點建立結果"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (a:LawyerInput_Accident)
                RETURN count(a) as count
            """)
            accident_count = result.single()['count']

            result = session.run("""
                MATCH (i:LawyerInput_Injury)
                RETURN count(i) as count
            """)
            injury_count = result.single()['count']

            result = session.run("""
                MATCH (c:LawyerInput_Claim)
                RETURN count(c) as count
            """)
            claim_count = result.single()['count']

            logger.info(f"\n節點統計：")
            logger.info(f"  LawyerInput_Accident: {accident_count}")
            logger.info(f"  LawyerInput_Injury: {injury_count}")
            logger.info(f"  LawyerInput_Claim: {claim_count}")

            # 檢查關係
            result = session.run("""
                MATCH (c:Case)-[r:HAS_LAWYER_INPUT]->()
                RETURN count(r) as count
            """)
            relation_count = result.single()['count']
            logger.info(f"  HAS_LAWYER_INPUT 關係: {relation_count}")


def main():
    file_path = "/home/aru/AI_LAW/09_輸入輸出資料/6057律師輸入_三段切分.xlsx"

    builder = LawyerInputGraphBuilder()

    try:
        # 刪除舊的 LawyerInput 節點
        logger.info("Step 1: 刪除舊的 LawyerInput 節點...")
        builder.delete_old_lawyer_input_nodes()

        # 建立新的律師輸入節點
        logger.info("\nStep 2: 建立新的律師輸入節點...")
        builder.process_lawyer_inputs(file_path)

        # 驗證結果
        logger.info("\nStep 3: 驗證節點建立結果...")
        builder.verify_nodes()

    finally:
        builder.close()


if __name__ == "__main__":
    main()
