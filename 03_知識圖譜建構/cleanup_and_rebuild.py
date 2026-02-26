#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理並重建知識圖譜
"""

import os
import sys
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class DatabaseCleaner:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        logger.info(f"✅ 已連接到 Neo4j: {NEO4J_URI}")

    def close(self):
        self.driver.close()

    def count_nodes(self, session):
        """統計各類型節點數量"""
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        results = session.run(query)

        logger.info("📊 當前資料庫狀態：")
        logger.info("━" * 50)
        total = 0
        for record in results:
            label = record['label'] or 'No Label'
            count = record['count']
            logger.info(f"  {label:20s}: {count:,} 個")
            total += count
        logger.info("━" * 50)
        logger.info(f"  {'總計':20s}: {total:,} 個")
        logger.info("")
        return total

    def delete_all_case_related_nodes(self, session):
        """刪除所有 Case 相關節點"""
        logger.info("🗑️  開始刪除所有 Case 相關節點...")

        # 分批刪除，避免超時
        batch_size = 1000
        total_deleted = 0

        while True:
            query = f"""
            MATCH (c:Case)
            WITH c LIMIT {batch_size}
            DETACH DELETE c
            RETURN count(c) as deleted
            """

            result = session.run(query).single()
            deleted = result['deleted']
            total_deleted += deleted

            if deleted > 0:
                logger.info(f"  已刪除 {total_deleted:,} 個 Case 節點...")
            else:
                break

        logger.info(f"✅ 總共刪除 {total_deleted:,} 個 Case 節點")
        logger.info("")

    def delete_orphan_nodes(self, session):
        """刪除孤立的 Facts, Laws, Compensation 節點"""
        logger.info("🗑️  清理孤立節點...")

        node_types = ['Facts', 'Laws', 'Compensation', 'Conclusion']
        total_deleted = 0

        for node_type in node_types:
            query = f"""
            MATCH (n:{node_type})
            WHERE NOT exists((n)<-[:HAS_{node_type.upper()}]-())
            WITH n LIMIT 10000
            DETACH DELETE n
            RETURN count(n) as deleted
            """

            result = session.run(query).single()
            deleted = result['deleted']
            total_deleted += deleted

            if deleted > 0:
                logger.info(f"  刪除 {deleted:,} 個孤立的 {node_type} 節點")

        logger.info(f"✅ 總共刪除 {total_deleted:,} 個孤立節點")
        logger.info("")

    def cleanup(self):
        """執行清理"""
        with self.driver.session() as session:
            logger.info("=" * 60)
            logger.info("開始清理資料庫")
            logger.info("=" * 60)
            logger.info("")

            # 清理前統計
            self.count_nodes(session)

            # 刪除 Case 節點
            self.delete_all_case_related_nodes(session)

            # 刪除孤立節點
            self.delete_orphan_nodes(session)

            # 清理後統計
            logger.info("清理後狀態：")
            remaining = self.count_nodes(session)

            logger.info("=" * 60)
            logger.info("✅ 清理完成！")
            logger.info("=" * 60)

            return remaining == 0

def main():
    # 確認操作
    print("⚠️  警告：此操作將刪除所有 Case 及相關節點！")
    print("確定要繼續嗎？(輸入 'YES' 確認)")

    confirmation = input("> ").strip()

    if confirmation != "YES":
        print("❌ 已取消操作")
        sys.exit(0)

    # 執行清理
    cleaner = DatabaseCleaner()

    try:
        cleaner.cleanup()
    finally:
        cleaner.close()

    logger.info("")
    logger.info("🎉 資料庫已清空！")
    logger.info("📝 接下來請執行：")
    logger.info("   python KG_100_rebuild_6057_cases.py")

if __name__ == "__main__":
    main()
