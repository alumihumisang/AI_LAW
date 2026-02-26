#!/usr/bin/env python3
"""刪除舊版Detail節點"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

print(f"連接到 Neo4j: {NEO4J_URI}")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def delete_old_details(tx):
    """刪除舊版的Detail節點"""
    queries = [
        # 統計舊節點數量
        ("MATCH (n:LawDetail) RETURN count(n) as count", "LawDetail節點數"),
        ("MATCH (n:CompensationDetail) RETURN count(n) as count", "CompensationDetail節點數"),
        ("MATCH (n:ConclusionDetail) RETURN count(n) as count", "ConclusionDetail節點數"),

        # 刪除節點
        ("MATCH (n:LawDetail) DETACH DELETE n", "刪除LawDetail"),
        ("MATCH (n:CompensationDetail) DETACH DELETE n", "刪除CompensationDetail"),
        ("MATCH (n:ConclusionDetail) DETACH DELETE n", "刪除ConclusionDetail"),
    ]

    for query, description in queries:
        print(f"\n執行: {description}")
        print(f"查詢: {query}")

        result = tx.run(query)

        # 如果是統計查詢，顯示結果
        if "RETURN count" in query:
            count = result.single()["count"]
            print(f"結果: {count} 個節點")
        else:
            summary = result.consume()
            print(f"✅ 已刪除，nodes_deleted={summary.counters.nodes_deleted}, relationships_deleted={summary.counters.relationships_deleted}")

try:
    with driver.session() as session:
        print("\n開始刪除舊版Detail節點...")
        session.execute_write(delete_old_details)
        print("\n✅ 所有舊版Detail節點已刪除完成！")

except Exception as e:
    print(f"\n❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.close()
    print("\n資料庫連線已關閉")
