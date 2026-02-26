#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KG_306: 從 extracted_info 中提取並更新 CompensationDetail 的 category/amount/item_name
資料其實已經在 Neo4j 裡了，只是需要從 JSON 字串中解析出來
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
        logging.FileHandler('kg_306_fix_compensation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


def parse_extracted_info(extracted_info_str):
    """
    解析 extracted_info JSON 字串

    Args:
        extracted_info_str: JSON 字串或空字典

    Returns:
        dict: 解析後的字典，包含 category, amount, item_name 等
    """
    if not extracted_info_str:
        return {}

    try:
        # 如果已經是字典，直接返回
        if isinstance(extracted_info_str, dict):
            return extracted_info_str

        # 如果是字串，解析 JSON
        if isinstance(extracted_info_str, str):
            # 處理空字串或 "{}"
            if not extracted_info_str.strip() or extracted_info_str.strip() == "{}":
                return {}
            return json.loads(extracted_info_str)

        return {}
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️  JSON 解析失敗: {e}")
        return {}
    except Exception as e:
        logger.warning(f"⚠️  未預期的錯誤: {e}")
        return {}


def fix_compensation_details():
    """
    修復所有 CompensationDetail 節點
    從 extracted_info 中提取 category、amount、item_name 並更新到節點屬性
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    logger.info("✅ 已連接到 Neo4j")

    with driver.session() as session:
        # 統計總數
        result = session.run("MATCH (n:CompensationDetail) RETURN count(n) as total")
        total = result.single()["total"]
        logger.info(f"📊 共有 {total} 個 CompensationDetail 節點")

        # 批次處理
        batch_size = 100
        updated = 0
        no_data = 0
        failed = 0

        for offset in tqdm(range(0, total, batch_size), desc="修復 CompensationDetail"):
            # 讀取一批節點
            result = session.run("""
                MATCH (n:CompensationDetail)
                RETURN n.chunk_id as chunk_id,
                       n.extracted_info as extracted_info
                ORDER BY n.chunk_id
                SKIP $offset LIMIT $batch_size
            """, offset=offset, batch_size=batch_size)

            nodes = list(result)

            # 處理每個節點
            for record in nodes:
                chunk_id = record["chunk_id"]
                extracted_info_str = record["extracted_info"]

                # 解析 extracted_info
                extracted_info = parse_extracted_info(extracted_info_str)

                if not extracted_info:
                    no_data += 1
                    continue

                # 提取欄位
                category = extracted_info.get('category')
                amount = extracted_info.get('amount')
                item_name = extracted_info.get('item_name')
                calculation_method = extracted_info.get('calculation_method')

                # 構建更新查詢（只更新有值的欄位）
                update_parts = []
                params = {"chunk_id": chunk_id}

                if category:
                    update_parts.append("n.category = $category")
                    params["category"] = category

                if amount is not None:
                    update_parts.append("n.amount = $amount")
                    params["amount"] = amount

                if item_name:
                    update_parts.append("n.item_name = $item_name")
                    params["item_name"] = item_name

                if calculation_method:
                    update_parts.append("n.calculation_method = $calculation_method")
                    params["calculation_method"] = calculation_method

                # 更新 detail_type 為 category（避免都是 Unknown）
                if category:
                    update_parts.append("n.detail_type = $detail_type")
                    params["detail_type"] = category

                if not update_parts:
                    no_data += 1
                    continue

                # 執行更新
                try:
                    update_query = f"""
                    MATCH (n:CompensationDetail {{chunk_id: $chunk_id}})
                    SET {', '.join(update_parts)}
                    """
                    session.run(update_query, params)
                    updated += 1
                except Exception as e:
                    logger.error(f"❌ 更新節點 {chunk_id} 失敗: {e}")
                    failed += 1

        # 統計結果
        logger.info("\n" + "="*60)
        logger.info("📊 修復統計：")
        logger.info(f"  成功更新：{updated}")
        logger.info(f"  無資料：{no_data}")
        logger.info(f"  失敗：{failed}")

        # 統計各類別數量
        logger.info("\n" + "="*60)
        logger.info("📈 各類別分布：")
        logger.info("="*60)
        result = session.run("""
            MATCH (n:CompensationDetail)
            WHERE n.category IS NOT NULL
            RETURN n.category as category, count(*) as count
            ORDER BY count DESC
        """)
        for record in result:
            logger.info(f"  {record['category']:<20} {record['count']:>8} 個")

        # 統計有金額的節點
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
            logger.info("\n" + "="*60)
            logger.info("💰 金額統計：")
            logger.info("="*60)
            logger.info(f"  有金額的節點：{stats['count']} 個")
            logger.info(f"  平均金額：{stats['avg_amount']:,.0f} 元")
            logger.info(f"  最小金額：{stats['min_amount']:,.0f} 元")
            logger.info(f"  最大金額：{stats['max_amount']:,.0f} 元")

        # 統計 detail_type 分布
        logger.info("\n" + "="*60)
        logger.info("📊 detail_type 分布（修復後）：")
        logger.info("="*60)
        result = session.run("""
            MATCH (n:CompensationDetail)
            RETURN n.detail_type as type, count(*) as count
            ORDER BY count DESC
            LIMIT 15
        """)
        for record in result:
            logger.info(f"  {record['type']:<20} {record['count']:>8} 個")

    driver.close()
    logger.info("\n✅ 修復完成！")


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("🔧 開始修復 CompensationDetail 節點（從 extracted_info 提取）")
    logger.info("="*80)
    fix_compensation_details()
