#!/usr/bin/env python3
"""
檢查 Neo4j 中 Laws 節點的結構
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

env_path = os.path.join(os.path.dirname(__file__), '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 60)
print("🔍 檢查 Laws 節點結構")
print("=" * 60)

with driver.session() as session:
    # 1. 檢查 Laws 節點數量
    laws_count = session.run("MATCH (l:Laws) RETURN count(l) as count").single()["count"]
    print(f"\n📊 Laws 節點總數：{laws_count}")

    # 2. 檢查 Laws 節點的屬性
    if laws_count > 0:
        sample = session.run("MATCH (l:Laws) RETURN l LIMIT 3").data()
        print("\n📋 Laws 節點樣本（前3個）：")
        for i, record in enumerate(sample, 1):
            print(f"\n   樣本 {i}:")
            laws_node = record['l']
            for key, value in laws_node.items():
                print(f"      {key}: {value}")

    # 3. 檢查 Case -> Laws 的關係
    print("\n🔗 檢查 Case -> Laws 關係：")
    rel_count = session.run("""
        MATCH (c:Case)-[r]->(l:Laws)
        RETURN type(r) as rel_type, count(*) as count
    """).data()

    if rel_count:
        for record in rel_count:
            print(f"   關係類型 '{record['rel_type']}': {record['count']} 條")
    else:
        print("   ⚠️ 沒有找到 Case -> Laws 的關係！")

    # 4. 檢查法條編號的格式
    print("\n📝 檢查法條編號格式：")
    law_numbers = session.run("""
        MATCH (l:Laws)
        RETURN DISTINCT l.法條編號 as law_num
        ORDER BY law_num
        LIMIT 20
    """).data()

    if law_numbers:
        print("   前20個法條編號：")
        for record in law_numbers:
            print(f"      {record['law_num']}")
    else:
        print("   ⚠️ 沒有找到 '法條編號' 屬性！")

        # 嘗試找其他可能的屬性名稱
        print("\n   嘗試尋找其他屬性...")
        all_props = session.run("""
            MATCH (l:Laws)
            RETURN keys(l) as props
            LIMIT 1
        """).single()

        if all_props:
            print(f"   Laws 節點的所有屬性：{all_props['props']}")

driver.close()
print("\n" + "=" * 60)
