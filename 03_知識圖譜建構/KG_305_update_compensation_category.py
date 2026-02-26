#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KG_305: 更新 CompensationDetail 節點，添加 category 和 amount 欄位
從 chunk_text 和 semantic_summary 中提取結構化資訊
"""

import re
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
        logging.FileHandler('kg_305_update_compensation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


# 標準化類別對照表
CATEGORY_KEYWORDS = {
    'medical': ['醫療', '醫藥', '診療', '手術', '住院', '醫'],
    'nursing': ['看護', '照護', '護理', '照顧'],
    'vehicle': ['車輛', '車損', '維修', '修理費'],
    'income_loss': ['薪資', '工資', '收入', '工作損失', '薪資損失', '工損', '不能工作'],
    'mental': ['精神', '慰撫', '痛苦'],
    'equipment': ['輔具', '護具', '器材', '義肢', '器具'],
    'transportation': ['交通', '車資', '計程車', '往返'],
    'other': ['其他']
}


def extract_category(text):
    """
    從文本中提取賠償項目類別

    Args:
        text: 賠償項目文本（chunk_text 或 semantic_summary）

    Returns:
        str: 類別（medical/nursing/vehicle/...）
    """
    text_lower = text.lower()

    # 按優先順序檢查（避免誤判）
    priority_order = [
        'nursing',      # 看護（優先於醫療，因為容易被誤判為醫療）
        'equipment',    # 輔具
        'transportation',  # 交通
        'vehicle',      # 車輛
        'income_loss',  # 工損
        'mental',       # 精神慰撫金
        'medical',      # 醫療（放後面，因為範圍最廣）
        'other'         # 其他（最後）
    ]

    for category in priority_order:
        keywords = CATEGORY_KEYWORDS[category]
        for keyword in keywords:
            if keyword in text:
                return category

    # 如果都沒匹配，返回 other
    return 'other'


def extract_amount(text):
    """
    從文本中提取金額

    Args:
        text: 包含金額的文本

    Returns:
        int: 金額（元），如果提取失敗返回 None
    """
    # 移除逗號
    text = text.replace(',', '')

    # 正則提取金額（優先匹配帶「元」的）
    patterns = [
        r'[：:]\s*(\d+)\s*元',           # 「：123,456元」
        r'[：:]\s*新台幣\s*(\d+)\s*元',   # 「：新台幣123,456元」
        r'金額[為共計]*\s*(\d+)\s*元',    # 「金額共計123,456元」
        r'支出.*?(\d+)\s*元',            # 「支出123,456元」
        r'費用\s*(\d+)\s*元',            # 「費用123,456元」
        r'合計\s*(\d+)\s*元',            # 「合計123,456元」
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                amount = int(match.group(1))
                return amount
            except ValueError:
                continue

    # 如果上面都沒匹配，嘗試提取任何數字
    match = re.search(r'(\d{3,})', text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    return None


def extract_item_name(text):
    """
    提取項目名稱（如「醫療費用」、「看護費用」等）

    Args:
        text: chunk_text

    Returns:
        str: 項目名稱
    """
    # 提取「（一）XXX費用」或「1. XXX費用」格式
    patterns = [
        r'[（\(][一二三四五六七八九十\d]+[）\)]\s*([^：:]+)',  # （一）醫療費用
        r'^\d+[.、]\s*([^：:]+)',                              # 1. 醫療費用
        r'^([^：:：]+)',                                        # 醫療費用（開頭）
    ]

    for pattern in patterns:
        match = re.search(pattern, text.strip())
        if match:
            item_name = match.group(1).strip()
            # 移除金額
            item_name = re.sub(r'[\d,]+\s*元', '', item_name).strip()
            return item_name

    return "未知項目"


def update_compensation_details():
    """
    更新所有 CompensationDetail 節點，添加 category、amount、item_name 欄位
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    logger.info("✅ 已連接到 Neo4j")

    with driver.session() as session:
        # 統計總數
        result = session.run("MATCH (n:CompensationDetail) RETURN count(n) as total")
        total = result.single()["total"]
        logger.info(f"📊 共有 {total} 個 CompensationDetail 節點需要更新")

        # 批次處理（每次100個）
        batch_size = 100
        processed = 0
        updated = 0
        failed = 0

        for offset in tqdm(range(0, total, batch_size), desc="更新 CompensationDetail"):
            # 讀取一批節點
            result = session.run("""
                MATCH (n:CompensationDetail)
                RETURN n.chunk_id as chunk_id,
                       n.chunk_text as chunk_text,
                       n.semantic_summary as semantic_summary
                ORDER BY n.chunk_id
                SKIP $offset LIMIT $batch_size
            """, offset=offset, batch_size=batch_size)

            nodes = list(result)

            # 處理每個節點
            for record in nodes:
                chunk_id = record["chunk_id"]
                chunk_text = record["chunk_text"] or ""
                semantic_summary = record["semantic_summary"] or ""

                # 優先從 chunk_text 提取，否則從 semantic_summary 提取
                text_for_extraction = chunk_text if chunk_text else semantic_summary

                # 提取資訊
                category = extract_category(text_for_extraction)
                amount = extract_amount(text_for_extraction)
                item_name = extract_item_name(text_for_extraction)

                # 更新節點
                try:
                    update_query = """
                    MATCH (n:CompensationDetail {chunk_id: $chunk_id})
                    SET n.category = $category,
                        n.item_name = $item_name
                    """
                    params = {
                        "chunk_id": chunk_id,
                        "category": category,
                        "item_name": item_name
                    }

                    # 只有在有金額時才設置 amount
                    if amount is not None:
                        update_query += ", n.amount = $amount"
                        params["amount"] = amount

                    session.run(update_query, params)
                    updated += 1

                except Exception as e:
                    logger.error(f"❌ 更新節點 {chunk_id} 失敗: {e}")
                    failed += 1

                processed += 1

        # 統計結果
        logger.info("\n" + "="*60)
        logger.info("📊 更新統計：")
        logger.info(f"  處理總數：{processed}")
        logger.info(f"  成功更新：{updated}")
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
        logger.info("\n" + "="*60)
        logger.info("💰 金額統計：")
        logger.info("="*60)
        logger.info(f"  有金額的節點：{stats['count']} 個")
        logger.info(f"  平均金額：{stats['avg_amount']:,.0f} 元")
        logger.info(f"  最小金額：{stats['min_amount']:,.0f} 元")
        logger.info(f"  最大金額：{stats['max_amount']:,.0f} 元")

    driver.close()
    logger.info("\n✅ 更新完成！")


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("🚀 開始更新 CompensationDetail 節點")
    logger.info("="*80)
    update_compensation_details()
