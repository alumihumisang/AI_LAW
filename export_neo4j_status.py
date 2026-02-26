#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
導出 Neo4j 資料庫現狀到 Excel
讓用戶可以檢視目前存儲的資料
"""

import pandas as pd
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

output_path = "09_輸入輸出資料/Neo4j資料庫現狀檢視.xlsx"

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

    with driver.session() as session:

        # Sheet 1: 節點類型統計
        print("正在統計節點類型...")
        result = session.run("CALL db.labels()")
        labels = [record["label"] for record in result]

        stats = []
        for label in sorted(labels):
            count_result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
            count = count_result.single()["count"]
            stats.append({"節點類型": label, "數量": count})

        df_stats = pd.DataFrame(stats)
        df_stats.to_excel(writer, sheet_name='節點統計', index=False)
        print(f"  ✅ 節點統計：{len(labels)} 種類型")

        # Sheet 2: Case 範例（前 20 筆）
        print("正在讀取 Case 範例...")
        result = session.run("""
            MATCH (c:Case)
            RETURN c.case_id as 案件ID,
                   c.liability_type as 責任類型,
                   c.party_structure as 當事人結構,
                   c.case_type as 案例類型
            ORDER BY c.case_id
            LIMIT 20
        """)
        df_cases = pd.DataFrame([dict(record) for record in result])
        df_cases.to_excel(writer, sheet_name='Case範例', index=False)
        print(f"  ✅ Case 範例")

        # Sheet 3: FactDetail 範例（各類型前 5 筆）
        print("正在讀取 FactDetail 範例...")
        result = session.run("""
            MATCH (fd:FactDetail)
            WITH fd.detail_type as type, collect(fd)[0..5] as samples
            UNWIND samples as fd
            RETURN fd.case_id as 案件ID,
                   fd.detail_type as 細節類型,
                   fd.chunk_id as ChunkID,
                   fd.chunk_text as 原文,
                   fd.semantic_summary as 語義摘要
            ORDER BY fd.detail_type, fd.case_id
            LIMIT 50
        """)
        df_fact_details = pd.DataFrame([dict(record) for record in result])
        df_fact_details.to_excel(writer, sheet_name='FactDetail範例', index=False)
        print(f"  ✅ FactDetail 範例")

        # Sheet 4: InjuryInfo 詳細（前 10 筆）
        print("正在讀取 InjuryInfo 詳細...")
        result = session.run("""
            MATCH (fd:FactDetail)
            WHERE fd.detail_type = 'InjuryInfo'
            RETURN fd.case_id as 案件ID,
                   fd.chunk_text as 原文,
                   fd.semantic_summary as 摘要,
                   fd.extracted_info as 提取資訊
            LIMIT 10
        """)
        df_injury = pd.DataFrame([dict(record) for record in result])
        # 將 extracted_info 字典轉成字串
        if 'extracted_info' in df_injury.columns:
            df_injury['提取資訊'] = df_injury['提取資訊'].apply(lambda x: str(x) if x else "")
        df_injury.to_excel(writer, sheet_name='InjuryInfo詳細', index=False)
        print(f"  ✅ InjuryInfo 詳細")

        # Sheet 5: VehicleInfo 詳細（前 10 筆）
        print("正在讀取 VehicleInfo 詳細...")
        result = session.run("""
            MATCH (fd:FactDetail)
            WHERE fd.detail_type = 'VehicleInfo'
            RETURN fd.case_id as 案件ID,
                   fd.chunk_text as 原文,
                   fd.semantic_summary as 摘要,
                   fd.extracted_info as 提取資訊
            LIMIT 10
        """)
        df_vehicle = pd.DataFrame([dict(record) for record in result])
        if 'extracted_info' in df_vehicle.columns:
            df_vehicle['提取資訊'] = df_vehicle['提取資訊'].apply(lambda x: str(x) if x else "")
        df_vehicle.to_excel(writer, sheet_name='VehicleInfo詳細', index=False)
        print(f"  ✅ VehicleInfo 詳細")

        # Sheet 6: LawDetail 範例（前 20 筆）
        print("正在讀取 LawDetail 範例...")
        result = session.run("""
            MATCH (ld:LawDetail)
            RETURN ld.case_id as 案件ID,
                   ld.chunk_id as ChunkID,
                   ld.chunk_text as 原文,
                   ld.semantic_summary as 摘要
            ORDER BY ld.case_id
            LIMIT 20
        """)
        df_law_details = pd.DataFrame([dict(record) for record in result])
        df_law_details.to_excel(writer, sheet_name='LawDetail範例', index=False)
        print(f"  ✅ LawDetail 範例")

        # Sheet 7: CompensationDetail 範例（前 30 筆）
        print("正在讀取 CompensationDetail 範例...")
        result = session.run("""
            MATCH (cd:CompensationDetail)
            RETURN cd.case_id as 案件ID,
                   cd.chunk_id as ChunkID,
                   cd.chunk_index as 索引,
                   cd.chunk_text as 原文,
                   cd.semantic_summary as 摘要,
                   cd.detail_type as 類型,
                   cd.category as 分類,
                   cd.amount as 金額,
                   cd.item_name as 項目名稱
            ORDER BY cd.case_id, cd.chunk_index
            LIMIT 30
        """)
        df_comp_details = pd.DataFrame([dict(record) for record in result])
        df_comp_details.to_excel(writer, sheet_name='CompensationDetail範例', index=False)
        print(f"  ✅ CompensationDetail 範例")

        # Sheet 8: 關係統計
        print("正在統計關係類型...")
        result = session.run("""
            CALL db.relationshipTypes() YIELD relationshipType
            RETURN relationshipType as 關係類型
        """)
        df_rels = pd.DataFrame([dict(record) for record in result])

        # 統計每種關係的數量
        rel_counts = []
        for rel_type in df_rels['關係類型']:
            try:
                count_result = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count")
                count = count_result.single()["count"]
                rel_counts.append(count)
            except:
                rel_counts.append(0)

        df_rels['數量'] = rel_counts
        df_rels = df_rels.sort_values('數量', ascending=False)
        df_rels.to_excel(writer, sheet_name='關係統計', index=False)
        print(f"  ✅ 關係統計")

        # Sheet 9: 關係範例（Case -> Facts -> Laws -> Compensation）
        print("正在讀取關係範例...")
        result = session.run("""
            MATCH (c:Case)-[:包含]->(f:Facts)-[:適用]->(l:Laws)-[:計算]->(comp:Compensation)
            RETURN c.case_id as 案件ID,
                   c.liability_type as 責任類型,
                   f.text as 事實概述,
                   l.text as 法條引用,
                   comp.text as 賠償概述
            LIMIT 5
        """)
        df_rel_examples = pd.DataFrame([dict(record) for record in result])
        # 截斷長文本
        for col in df_rel_examples.columns:
            if df_rel_examples[col].dtype == 'object':
                df_rel_examples[col] = df_rel_examples[col].apply(
                    lambda x: x[:200] + "..." if isinstance(x, str) and len(x) > 200 else x
                )
        df_rel_examples.to_excel(writer, sheet_name='關係範例', index=False)
        print(f"  ✅ 關係範例")

        # Sheet 10: FactDetail 類型分布
        print("正在統計 FactDetail 類型分布...")
        result = session.run("""
            MATCH (fd:FactDetail)
            RETURN fd.detail_type as 類型, count(*) as 數量
            ORDER BY 數量 DESC
        """)
        df_fact_types = pd.DataFrame([dict(record) for record in result])
        df_fact_types.to_excel(writer, sheet_name='FactDetail類型分布', index=False)
        print(f"  ✅ FactDetail 類型分布")

        # Sheet 11: 摘要說明
        summary_data = [
            {"項目": "資料庫URI", "內容": NEO4J_URI},
            {"項目": "導出時間", "內容": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"項目": "總節點數", "內容": df_stats['數量'].sum()},
            {"項目": "節點類型數", "內容": len(df_stats)},
            {"項目": "關係類型數", "內容": len(df_rels)},
            {"項目": "", "內容": ""},
            {"項目": "主要節點", "內容": ""},
            {"項目": "  - Case", "內容": f"{df_stats[df_stats['節點類型']=='Case']['數量'].values[0]} 個"},
            {"項目": "  - FactDetail", "內容": f"{df_stats[df_stats['節點類型']=='FactDetail']['數量'].values[0]} 個"},
            {"項目": "  - LawDetail", "內容": f"{df_stats[df_stats['節點類型']=='LawDetail']['數量'].values[0]} 個"},
            {"項目": "  - CompensationDetail", "內容": f"{df_stats[df_stats['節點類型']=='CompensationDetail']['數量'].values[0]} 個"},
            {"項目": "", "內容": ""},
            {"項目": "說明", "內容": "此檔案包含 Neo4j 資料庫的完整現狀快照"},
            {"項目": "", "內容": "請檢視各個 Sheet 確認資料結構是否符合預期"},
        ]
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='摘要', index=False)
        print(f"  ✅ 摘要")

driver.close()

print("\n" + "="*60)
print(f"✅ 導出完成！")
print(f"📁 檔案位置：{output_path}")
print("="*60)
print("\n請檢視 Excel 檔案，確認資料結構後再繼續。")
