#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KG_307: 重新建立 CompensationDetail 節點（修正版）
從 structured_summaries_with_chunks.jsonl 重新讀取並正確建立節點
"""

import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('kg_307_rebuild_compensation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

JSONL_FILE = "../04_向量化與索引/structured_summaries_with_chunks.jsonl"


def rebuild_compensation_details():
    """
    重新建立 CompensationDetail 節點
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    logger.info("✅ 已連接到 Neo4j")

    # Step 1: 刪除舊的 CompensationDetail 節點
    logger.info("🗑️  刪除舊的 CompensationDetail 節點...")
    with driver.session() as session:
        result = session.run("MATCH (n:CompensationDetail) DETACH DELETE n")
        summary = result.consume()
        logger.info(f"   ✅ 已刪除 {summary.counters.nodes_deleted} 個節點")

    # Step 2: 讀取 JSONL 並重新建立節點
    logger.info(f"📖 讀取 {JSONL_FILE}...")

    # 計算總行數
    with open(JSONL_FILE, 'rb') as f:
        total_lines = sum(1 for _ in f)

    logger.info(f"   共 {total_lines} 行")

    created = 0
    skipped = 0
    failed = 0

    with driver.session() as session:
        with open(JSONL_FILE, 'rb') as f:
            for line in tqdm(f, total=total_lines, desc="重建 CompensationDetail"):
                try:
                    # 解碼
                    line_str = line.decode('utf-8', errors='ignore')
                    chunk_data = json.loads(line_str)

                    # 只處理 compensation
                    if chunk_data.get('parent_section') != 'compensation':
                        skipped += 1
                        continue

                    case_id = chunk_data['case_id']
                    chunk_id = chunk_data['chunk_id']
                    chunk_text = chunk_data['chunk_text']
                    chunk_index = chunk_data['chunk_index']
                    extracted_detail = chunk_data.get('extracted_detail', {})

                    # Compensation 的 extracted_detail 結構：
                    # {
                    #     "category": "medical",
                    #     "item_name": "醫療費用",
                    #     "amount": 171170,
                    #     "calculation_method": "實際支出",
                    #     "semantic_summary": "..."
                    # }

                    category = extracted_detail.get('category', 'unknown')
                    item_name = extracted_detail.get('item_name', '')
                    amount = extracted_detail.get('amount')
                    calculation_method = extracted_detail.get('calculation_method', '')
                    semantic_summary = extracted_detail.get('semantic_summary', '')

                    # 建立節點
                    query = """
                    MATCH (case:Case {case_id: $case_id})-[:包含]->(:Facts)-[:適用]->(:Laws)-[:計算]->(parent:Compensation)

                    CREATE (detail:CompensationDetail {
                        chunk_id: $chunk_id,
                        chunk_text: $chunk_text,
                        chunk_index: $chunk_index,
                        case_id: $case_id,
                        detail_type: $category,
                        category: $category,
                        item_name: $item_name,
                        semantic_summary: $semantic_summary
                    })

                    CREATE (parent)-[:HAS_DETAIL {chunk_index: $chunk_index}]->(detail)

                    RETURN detail.chunk_id as created_chunk_id
                    """

                    params = {
                        'case_id': int(case_id),
                        'chunk_id': chunk_id,
                        'chunk_text': chunk_text,
                        'chunk_index': chunk_index,
                        'category': category,
                        'item_name': item_name,
                        'semantic_summary': semantic_summary
                    }

                    # 只有在有金額時才設置
                    if amount is not None:
                        query = query.replace(
                            "semantic_summary: $semantic_summary",
                            "semantic_summary: $semantic_summary,\n        amount: $amount"
                        )
                        params['amount'] = amount

                    # 只有在有 calculation_method 時才設置
                    if calculation_method:
                        query = query.replace(
                            "semantic_summary: $semantic_summary",
                            "semantic_summary: $semantic_summary,\n        calculation_method: $calculation_method"
                        )
                        params['calculation_method'] = calculation_method

                    result = session.run(query, params)
                    if result.single():
                        created += 1

                except json.JSONDecodeError:
                    failed += 1
                    continue
                except Exception as e:
                    logger.error(f"❌ 處理失敗: {e}")
                    failed += 1
                    continue

    driver.close()

    # 統計結果
    logger.info("\n" + "="*60)
    logger.info("📊 重建統計：")
    logger.info(f"  成功建立：{created} 個")
    logger.info(f"  跳過（非 compensation）：{skipped} 個")
    logger.info(f"  失敗：{failed} 個")

    # 驗證結果
    logger.info("\n" + "="*60)
    logger.info("🔍 驗證結果...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        # 統計各類別
        result = session.run("""
            MATCH (n:CompensationDetail)
            WHERE n.category IS NOT NULL
            RETURN n.category as category, count(*) as count
            ORDER BY count DESC
        """)
        logger.info("\n各類別分布：")
        for record in result:
            logger.info(f"  {record['category']:<20} {record['count']:>8} 個")

        # 統計金額
        result = session.run("""
            MATCH (n:CompensationDetail)
            WHERE n.amount IS NOT NULL
            RETURN count(*) as count,
                   avg(n.amount) as avg_amount,
                   min(n.amount) as min_amount,
                   max(n.amount) as max_amount
        """)
        stats = result.single()
        if stats and stats['count'] > 0:
            logger.info("\n金額統計：")
            logger.info(f"  有金額的節點：{stats['count']} 個")
            logger.info(f"  平均金額：{stats['avg_amount']:,.0f} 元")
            logger.info(f"  最小金額：{stats['min_amount']:,.0f} 元")
            logger.info(f"  最大金額：{stats['max_amount']:,.0f} 元")

        # 範例節點
        result = session.run("""
            MATCH (n:CompensationDetail)
            RETURN n.chunk_id as chunk_id,
                   n.category as category,
                   n.item_name as item_name,
                   n.amount as amount,
                   n.chunk_text as chunk_text
            LIMIT 5
        """)
        logger.info("\n" + "="*60)
        logger.info("範例節點（前 5 筆）：")
        logger.info("="*60)
        for i, record in enumerate(result, 1):
            logger.info(f"\n節點 {i}:")
            logger.info(f"  chunk_id: {record['chunk_id']}")
            logger.info(f"  category: {record['category']}")
            logger.info(f"  item_name: {record['item_name']}")
            logger.info(f"  amount: {record['amount']}")
            logger.info(f"  chunk_text: {record['chunk_text'][:80]}...")

    driver.close()
    logger.info("\n✅ 重建完成！")


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("🔨 重新建立 CompensationDetail 節點（修正 extracted_detail 結構問題）")
    logger.info("="*80)
    rebuild_compensation_details()
