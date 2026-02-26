#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KG_350: 建立 Detail 節點到 Neo4j
從 structured_summaries_with_chunks.jsonl 讀取並建立細節節點
"""

import json
import os
import sys
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kg_350_build_details.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")  # 修正：使用 NEO4J_USERNAME
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class DetailNodeBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        logger.info(f"✅ 已連接到 Neo4j: {NEO4J_URI}")

    def close(self):
        self.driver.close()
        logger.info("🔌 已關閉 Neo4j 連接")

    def create_detail_node(self, session, chunk_data):
        """
        建立 Detail 節點並連接到對應的段落節點
        """
        case_id = chunk_data['case_id']
        parent_section = chunk_data['parent_section']
        chunk_id = chunk_data['chunk_id']
        chunk_text = chunk_data['chunk_text']
        chunk_index = chunk_data['chunk_index']
        extracted_detail = chunk_data.get('extracted_detail', {})

        # 跳過 conclusion - Conclusion 太短不需要細節節點
        if parent_section == 'conclusion':
            return None

        # 根據 parent_section 決定節點類型、父節點標籤和關係路徑
        section_mapping = {
            'facts': {
                'parent_label': 'Facts',
                'detail_label': 'FactDetail',
                'path_query': 'MATCH (case:Case {case_id: $case_id})-[:包含]->(parent:Facts)'
            },
            'laws': {
                'parent_label': 'Laws',
                'detail_label': 'LawDetail',
                'path_query': 'MATCH (case:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(parent:Laws)'
            },
            'compensation': {
                'parent_label': 'Compensation',
                'detail_label': 'CompensationDetail',
                'path_query': 'MATCH (case:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(:Laws)-[:計算]->(parent:Compensation)'
            }
        }

        if parent_section not in section_mapping:
            logger.warning(f"⚠️  未知的 parent_section: {parent_section}")
            return

        section_config = section_mapping[parent_section]
        detail_label = section_config['detail_label']
        path_query = section_config['path_query']

        # 建立 Detail 節點
        query = f"""
        // 找到對應的段落節點
        {path_query}

        // 建立 Detail 節點
        CREATE (detail:{detail_label} {{
            chunk_id: $chunk_id,
            chunk_text: $chunk_text,
            chunk_index: $chunk_index,
            case_id: $case_id,
            detail_type: $detail_type,
            extracted_info: $extracted_info,
            semantic_summary: $semantic_summary
        }})

        // 建立關係
        CREATE (parent)-[:HAS_DETAIL {{chunk_index: $chunk_index}}]->(detail)

        RETURN detail.chunk_id as created_chunk_id
        """

        params = {
            'case_id': int(case_id),  # 確保 case_id 是整數
            'chunk_id': chunk_id,
            'chunk_text': chunk_text,
            'chunk_index': chunk_index,
            'detail_type': extracted_detail.get('detail_type', 'Unknown'),
            'extracted_info': json.dumps(extracted_detail.get('extracted_info', {}), ensure_ascii=False),
            'semantic_summary': extracted_detail.get('semantic_summary', '')
        }

        try:
            result = session.run(query, params)
            return result.single()
        except Exception as e:
            logger.error(f"❌ 建立節點失敗 {chunk_id}: {e}")
            return None

    def process_all_chunks(self, jsonl_file):
        """
        處理所有 chunks
        """
        # 計算總行數（使用 binary mode 避免編碼錯誤）
        with open(jsonl_file, 'rb') as f:
            total_lines = sum(1 for _ in f)

        logger.info(f"📊 開始處理 {total_lines} 個 chunks")

        success_count = 0
        error_count = 0

        with self.driver.session() as session:
            with open(jsonl_file, 'rb') as f:
                for line_num, line in enumerate(tqdm(f, total=total_lines, desc="建立 Detail 節點"), 1):
                    try:
                        # 解碼每一行，忽略錯誤
                        line_str = line.decode('utf-8', errors='ignore')
                        chunk_data = json.loads(line_str)
                        result = self.create_detail_node(session, chunk_data)

                        if result:
                            success_count += 1
                        else:
                            error_count += 1

                        # 每 1000 筆輸出進度
                        if line_num % 1000 == 0:
                            logger.info(f"✅ 已處理: {line_num}/{total_lines} (成功: {success_count}, 失敗: {error_count})")

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON 解析錯誤 (第 {line_num} 行): {e}")
                        error_count += 1
                    except Exception as e:
                        logger.error(f"❌ 處理錯誤 (第 {line_num} 行): {e}")
                        error_count += 1

        logger.info(f"""
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        🎉 處理完成！
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        ✅ 成功建立: {success_count} 個節點
        ❌ 失敗: {error_count} 個
        📊 總計: {total_lines} 個 chunks
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)

    def verify_results(self):
        """
        驗證建立的節點數量
        """
        with self.driver.session() as session:
            # 統計各類型 Detail 節點數量（不包含 ConclusionDetail）
            query = """
            MATCH (d)
            WHERE d:FactDetail OR d:LawDetail OR d:CompensationDetail
            RETURN labels(d)[0] as node_type, count(*) as count
            """

            results = session.run(query)

            logger.info("\n📊 Detail 節點統計：")
            for record in results:
                logger.info(f"  {record['node_type']}: {record['count']:,} 個")

            # 檢查是否有孤立節點（沒有連接到段落的）
            orphan_query = """
            MATCH (d)
            WHERE (d:FactDetail OR d:LawDetail OR d:CompensationDetail)
              AND NOT exists((d)<-[:HAS_DETAIL]-())
            RETURN count(d) as orphan_count
            """

            orphan_result = session.run(orphan_query).single()
            orphan_count = orphan_result['orphan_count']

            if orphan_count > 0:
                logger.warning(f"⚠️  發現 {orphan_count} 個孤立節點（未連接到段落）")
            else:
                logger.info("✅ 所有 Detail 節點都已正確連接")

def main():
    # 輸入檔案路徑
    jsonl_file = "/home/aru/AI_LAW/04_向量化與索引/structured_summaries_with_chunks.jsonl"

    if not os.path.exists(jsonl_file):
        logger.error(f"❌ 找不到檔案: {jsonl_file}")
        sys.exit(1)

    logger.info(f"📂 讀取檔案: {jsonl_file}")

    # 建立節點
    builder = DetailNodeBuilder()

    try:
        builder.process_all_chunks(jsonl_file)
        builder.verify_results()
    finally:
        builder.close()

    logger.info("🎉 完成！")

if __name__ == "__main__":
    main()
