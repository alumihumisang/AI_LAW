#!/usr/bin/env python3
"""
KG_160_mark_liability_type.py
為 6057 個案例標記 liability_type（責任基礎類型）
- 100% 規則式，不使用 LLM
- 直接從適用法條判斷
"""
import os
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

# 設置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Neo4j 連線
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def mark_liability_type():
    """
    為所有案例標記 liability_type
    從 LawDetail 節點的 article 屬性提取法條編號
    """
    logger.info("🚀 開始標記 liability_type...")

    with driver.session() as session:
        # 使用 Cypher 直接標記
        result = session.run("""
            MATCH (c:Case)

            // 找出該案例的所有 LawDetail（通過 case_id）
            OPTIONAL MATCH (ld:LawDetail)
            WHERE ld.case_id = c.case_id

            WITH c, collect(DISTINCT ld.article) as law_articles

            // 從法條名稱中提取編號（如：民法第184條 -> 184）
            WITH c, [article IN law_articles WHERE article CONTAINS '187'] as has_187,
                    [article IN law_articles WHERE article CONTAINS '188'] as has_188,
                    [article IN law_articles WHERE article CONTAINS '190'] as has_190,
                    [article IN law_articles WHERE article CONTAINS '184'] as has_184,
                    [article IN law_articles WHERE article CONTAINS '191'] as has_191

            // 判斷 liability_type（優先順序：187 > 188 > 190 > 184/191）
            SET c.liability_type =
                CASE
                    WHEN size(has_187) > 0 THEN 'guardian_liability_187'
                    WHEN size(has_188) > 0 THEN 'employer_liability_188'
                    WHEN size(has_190) > 0 THEN 'animal_liability_190'
                    WHEN size(has_184) > 0 OR size(has_191) > 0 THEN 'general_tort_184_191'
                    ELSE 'other'
                END

            RETURN c.case_id, c.liability_type
        """)

        # 統計結果
        records = list(result)
        logger.info(f"✅ 成功標記 {len(records)} 個案例")

    # 統計分布
    logger.info("\n📊 liability_type 分布：")
    with driver.session() as session:
        distribution = session.run("""
            MATCH (c:Case)
            WHERE c.liability_type IS NOT NULL
            RETURN c.liability_type as type, count(*) as count
            ORDER BY count DESC
        """).data()

        for record in distribution:
            logger.info(f"   {record['type']}: {record['count']} 個案例")

    return distribution

def verify_results():
    """驗證標記結果"""
    logger.info("\n🔍 驗證標記結果...")

    with driver.session() as session:
        # 檢查是否所有案例都有 liability_type
        result = session.run("""
            MATCH (c:Case)
            RETURN
                count(c) as total,
                count(c.liability_type) as with_type
        """).single()

        total = result["total"]
        with_type = result["with_type"]

        logger.info(f"   總案例數：{total}")
        logger.info(f"   已標記：{with_type} ({with_type/total*100:.1f}%)")

        if with_type == total:
            logger.info("   ✅ 所有案例都已標記")
        else:
            logger.warning(f"   ⚠️ 還有 {total - with_type} 個案例未標記")

def main():
    try:
        print("=" * 60)
        print("🏷️ 標記案例責任基礎類型（liability_type）")
        print("=" * 60)
        print("此腳本會根據適用法條自動標記案例類型：")
        print("  - guardian_liability_187（監護人責任）")
        print("  - employer_liability_188（僱用人責任）")
        print("  - animal_liability_190（動物占有人責任）")
        print("  - general_tort_184_191（一般侵權）")
        print("  - other（其他）")
        print("=" * 60)

        confirm = input("\n是否開始標記？(y/N): ").lower().strip()
        if confirm not in ['y', 'yes', '是']:
            print("❌ 操作已取消")
            return

        # 執行標記
        distribution = mark_liability_type()

        # 驗證結果
        verify_results()

        print("\n" + "=" * 60)
        print("🎉 標記完成！")
        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ 標記過程出錯：{e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
