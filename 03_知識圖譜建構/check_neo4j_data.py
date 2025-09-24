#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Neo4j 資料完整性檢查腳本
檢查各種節點類型的記錄數量
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入環境變數
load_dotenv()

class Neo4jDataChecker:
    def __init__(self):
        """初始化Neo4j連接"""
        try:
            self.driver = GraphDatabase.driver(
                os.getenv('NEO4J_URI'),
                auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
            )
            print("✅ 成功連接至 Neo4j 資料庫")
        except Exception as e:
            print(f"❌ Neo4j 連接失敗: {e}")
            sys.exit(1)
    
    def close(self):
        """關閉連接"""
        if self.driver:
            self.driver.close()
    
    def check_node_counts(self):
        """檢查所有節點類型的數量"""
        print("\n" + "="*60)
        print("📊 Neo4j 節點數量統計")
        print("="*60)
        
        with self.driver.session() as session:
            try:
                # 檢查各種節點類型
                node_types = [
                    "Case",
                    "Laws", 
                    "Compensation",
                    "Conclusion",
                    "LawyerInput"
                ]
                
                for node_type in node_types:
                    query = f"MATCH (n:{node_type}) RETURN count(n) as count"
                    result = session.run(query)
                    count = result.single()["count"]
                    status = "✅" if count > 0 else "❌"
                    print(f"{status} {node_type} 節點: {count:,} 個")
                
                print("\n" + "="*60)
                print("🔍 詳細檢查")
                print("="*60)
                
                # 檢查Case節點的case_id範圍
                query = """
                MATCH (c:Case) 
                RETURN min(c.case_id) as min_id, max(c.case_id) as max_id, count(c) as total
                """
                result = session.run(query)
                data = result.single()
                if data:
                    print(f"📋 Case節點 case_id 範圍: {data['min_id']} ~ {data['max_id']} (共 {data['total']} 個)")
                
                # 檢查LawyerInput節點的case_id範圍
                query = """
                MATCH (l:LawyerInput) 
                RETURN min(l.case_id) as min_id, max(l.case_id) as max_id, count(l) as total
                """
                result = session.run(query)
                data = result.single()
                if data and data['total'] > 0:
                    print(f"⚖️ LawyerInput節點 case_id 範圍: {data['min_id']} ~ {data['max_id']} (共 {data['total']} 個)")
                
                # 檢查哪些Case沒有對應的LawyerInput
                query = """
                MATCH (c:Case) 
                WHERE NOT EXISTS {
                    MATCH (l:LawyerInput {case_id: c.case_id})
                }
                RETURN count(c) as missing_count, min(c.case_id) as first_missing, max(c.case_id) as last_missing
                """
                result = session.run(query)
                data = result.single()
                if data and data['missing_count'] > 0:
                    print(f"⚠️ 缺少LawyerInput的Case: {data['missing_count']} 個")
                    print(f"   缺少範圍: case_id {data['first_missing']} ~ {data['last_missing']}")
                
                # 檢查哪些Case沒有Laws擴展
                query = """
                MATCH (c:Case) 
                WHERE NOT EXISTS {
                    MATCH (c)-[:HAS_LAWS]->(l:Laws)
                    WHERE l.details IS NOT NULL AND l.details <> ''
                }
                RETURN count(c) as missing_count
                """
                result = session.run(query)
                data = result.single()
                if data:
                    print(f"⚠️ 缺少Laws詳細信息的Case: {data['missing_count']} 個")
                
                # 檢查哪些Case沒有Compensation擴展
                query = """
                MATCH (c:Case) 
                WHERE NOT EXISTS {
                    MATCH (c)-[:HAS_COMPENSATION]->(comp:Compensation)
                    WHERE comp.details IS NOT NULL AND comp.details <> ''
                }
                RETURN count(c) as missing_count
                """
                result = session.run(query)
                data = result.single()
                if data:
                    print(f"⚠️ 缺少Compensation詳細信息的Case: {data['missing_count']} 個")
                
                # 檢查哪些Case沒有Conclusion擴展
                query = """
                MATCH (c:Case) 
                WHERE NOT EXISTS {
                    MATCH (c)-[:HAS_CONCLUSION]->(con:Conclusion)
                    WHERE con.details IS NOT NULL AND con.details <> ''
                }
                RETURN count(c) as missing_count
                """
                result = session.run(query)
                data = result.single()
                if data:
                    print(f"⚠️ 缺少Conclusion詳細信息的Case: {data['missing_count']} 個")
                
            except Exception as e:
                print(f"❌ 查詢失敗: {e}")
    
    def check_specific_case_ranges(self):
        """檢查特定case_id範圍的處理狀況"""
        print("\n" + "="*60)
        print("🔍 案件範圍處理狀況檢查")
        print("="*60)
        
        ranges = [
            (1, 500),
            (501, 1000),
            (1001, 1500),
            (1501, 2000),
            (2001, 2500),
            (2501, 2995)
        ]
        
        with self.driver.session() as session:
            for start, end in ranges:
                print(f"\n📋 檢查範圍 {start}-{end}:")
                
                # Case節點
                query = f"""
                MATCH (c:Case) 
                WHERE c.case_id >= {start} AND c.case_id <= {end}
                RETURN count(c) as count
                """
                result = session.run(query)
                case_count = result.single()["count"]
                
                # LawyerInput節點
                query = f"""
                MATCH (l:LawyerInput) 
                WHERE l.case_id >= {start} AND l.case_id <= {end}
                RETURN count(l) as count
                """
                result = session.run(query)
                lawyer_count = result.single()["count"]
                
                print(f"   Case: {case_count}, LawyerInput: {lawyer_count}")
                if case_count != lawyer_count:
                    print(f"   ⚠️ 不匹配！缺少 {case_count - lawyer_count} 個LawyerInput")

def main():
    checker = Neo4jDataChecker()
    try:
        checker.check_node_counts()
        checker.check_specific_case_ranges()
    finally:
        checker.close()
    
    print("\n" + "="*60)
    print("✅ 檢查完成")
    print("="*60)

if __name__ == "__main__":
    main()