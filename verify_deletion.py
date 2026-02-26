#!/usr/bin/env python3
"""驗證舊節點已刪除"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def verify_deletion(tx):
    """驗證節點已刪除"""
    queries = [
        ("MATCH (n:LawDetail) RETURN count(n) as count", "LawDetail"),
        ("MATCH (n:CompensationDetail) RETURN count(n) as count", "CompensationDetail"),
        ("MATCH (n:ConclusionDetail) RETURN count(n) as count", "ConclusionDetail"),
        ("MATCH (n:Case) RETURN count(n) as count", "Case"),
        ("MATCH (n:Facts) RETURN count(n) as count", "Facts"),
        ("MATCH (n:Laws) RETURN count(n) as count", "Laws"),
        ("MATCH (n:Compensation) RETURN count(n) as count", "Compensation"),
    ]

    print("\n📊 當前節點統計：\n")
    for query, label in queries:
        result = tx.run(query)
        count = result.single()["count"]
        status = "✅" if (label in ["LawDetail", "CompensationDetail", "ConclusionDetail"] and count == 0) else "📌"
        print(f"{status} {label}: {count} 個節點")

try:
    with driver.session() as session:
        session.execute_read(verify_deletion)

except Exception as e:
    print(f"❌ 錯誤: {e}")

finally:
    driver.close()
