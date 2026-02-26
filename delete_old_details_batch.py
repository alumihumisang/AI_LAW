#!/usr/bin/env python3
"""分批刪除舊版Detail節點（避免超時）"""

import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import time

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def delete_in_batches(label, batch_size=1000):
    """分批刪除節點"""
    total_deleted = 0

    print(f"\n開始分批刪除 {label} 節點...")

    while True:
        with driver.session() as session:
            result = session.run(f"""
                MATCH (n:{label})
                WITH n LIMIT {batch_size}
                DETACH DELETE n
                RETURN count(n) as deleted
            """)

            deleted = result.single()["deleted"]
            total_deleted += deleted

            print(f"  已刪除 {deleted} 個節點，累計: {total_deleted}")

            if deleted == 0:
                break

            # 避免過於頻繁
            time.sleep(0.5)

    print(f"✅ {label} 刪除完成，總計: {total_deleted} 個節點\n")
    return total_deleted

try:
    print("=" * 60)
    print("開始分批刪除舊版Detail節點")
    print("=" * 60)

    # 刪除三種Detail節點
    total_law = delete_in_batches("LawDetail", batch_size=1000)
    total_comp = delete_in_batches("CompensationDetail", batch_size=1000)
    total_conc = delete_in_batches("ConclusionDetail", batch_size=1000)

    print("=" * 60)
    print(f"✅ 所有舊版Detail節點已刪除完成！")
    print(f"總計刪除: {total_law + total_comp + total_conc} 個節點")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 錯誤: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.close()
