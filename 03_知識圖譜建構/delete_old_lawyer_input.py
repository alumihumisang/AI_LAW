#!/usr/bin/env python3
"""刪除舊版LawyerInput節點 (LawyerInput_Cause, LawyerInput_Effect)"""

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

def delete_old_lawyer_input(tx):
    """刪除舊版的LawyerInput節點"""
    queries = [
        # 統計舊節點數量
        ("MATCH (n:LawyerInput_Cause) RETURN count(n) as count", "LawyerInput_Cause節點數"),
        ("MATCH (n:LawyerInput_Effect) RETURN count(n) as count", "LawyerInput_Effect節點數"),
        ("MATCH (n:LawyerInput) RETURN count(n) as count", "LawyerInput節點數"),

        # 刪除節點
        ("MATCH (n:LawyerInput_Cause) DETACH DELETE n", "刪除LawyerInput_Cause"),
        ("MATCH (n:LawyerInput_Effect) DETACH DELETE n", "刪除LawyerInput_Effect"),
        ("MATCH (n:LawyerInput) DETACH DELETE n", "刪除LawyerInput"),
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
        print("\n開始刪除舊版LawyerInput節點...")
        session.execute_write(delete_old_lawyer_input)
        print("\n✅ 所有舊版LawyerInput節點已刪除完成！")

except Exception as e:
    print(f"\n❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.close()
    print("\n資料庫連線已關閉")
