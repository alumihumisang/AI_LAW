#!/usr/bin/env python3
"""
檢查 Neo4j 和 ES 中的 case_type 狀態
"""
import os
import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

# Neo4j 連線
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# ES 連線
ES_HOST = os.getenv("ELASTIC_HOST")
ES_USER = os.getenv("ELASTIC_USER")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 60)
print("🔍 檢查 case_type 狀態")
print("=" * 60)

# 1. 檢查 Neo4j
print("\n📊 Neo4j 狀態：")
with driver.session() as session:
    # 總案例數
    total = session.run("MATCH (c:Case) RETURN count(c) as count").single()["count"]
    print(f"   總案例數：{total}")

    # 有 case_type 的案例數
    with_type = session.run("""
        MATCH (c:Case)
        WHERE c.case_type IS NOT NULL
        RETURN count(c) as count
    """).single()["count"]
    print(f"   有 case_type：{with_type} ({with_type/total*100:.1f}%)")

    # case_type 分布
    if with_type > 0:
        distribution = session.run("""
            MATCH (c:Case)
            WHERE c.case_type IS NOT NULL
            RETURN c.case_type as type, count(*) as count
            ORDER BY count DESC
        """).data()

        print("\n   📈 case_type 分布：")
        for record in distribution:
            print(f"      {record['type']}: {record['count']} 個")
    else:
        print("   ⚠️ 沒有任何案例有 case_type 屬性")

# 2. 檢查 Elasticsearch
print("\n📊 Elasticsearch 狀態：")
try:
    # 檢查 legal_kg_chunks 索引中的 case_type
    search_body = {
        "size": 0,
        "aggs": {
            "case_type_dist": {
                "terms": {
                    "field": "case_type.keyword",
                    "size": 20
                }
            },
            "total_cases": {
                "cardinality": {
                    "field": "case_id"
                }
            }
        }
    }

    url = f"{ES_HOST}/legal_kg_chunks/_search"
    response = requests.post(
        url,
        auth=(ES_USER, ES_PASSWORD),
        json=search_body,
        verify=False
    )

    if response.status_code == 200:
        result = response.json()

        total_cases = result["aggregations"]["total_cases"]["value"]
        print(f"   索引中的案例數：{total_cases}")

        case_type_buckets = result["aggregations"]["case_type_dist"]["buckets"]

        if case_type_buckets:
            print("\n   📈 case_type 分布：")
            for bucket in case_type_buckets:
                print(f"      {bucket['key']}: {bucket['doc_count']} 個文檔")
        else:
            print("   ⚠️ ES 中沒有 case_type 欄位或欄位為空")
    else:
        print(f"   ❌ ES 查詢失敗：{response.status_code}")

except Exception as e:
    print(f"   ❌ ES 連接失敗：{e}")

driver.close()

print("\n" + "=" * 60)
print("💡 建議：")
print("   1. 如果 Neo4j 中沒有 case_type，執行：")
print("      python 03_知識圖譜建構/KG_150_update_case_type.py")
print("   2. 如果 ES 中沒有 case_type，需要先標記案型")
print("=" * 60)
