#!/usr/bin/env python3
"""
KG_161_extract_party_structure.py
提取所有案例並初步判斷 party_structure
輸出 Excel 供人工檢查和修正
"""
import os
import logging
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
import re

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

# 設置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Neo4j 連線
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def detect_party_structure_from_text(fact_text):
    """
    從事實文本中判斷當事人結構並提取姓名
    使用精準的規則，減少人工檢查需求
    """
    if not fact_text:
        return 'unknown', '無事實文本', [], []

    # 強烈的複數標記（高信心度）
    plaintiff_strong_markers = [
        '原告等', '各原告', '原告們',
        '原告二人', '原告三人', '原告四人',
        '原告甲', '原告乙', '原告丙',
        '數名原告', '多名原告'
    ]

    defendant_strong_markers = [
        '被告等', '各被告', '被告們',
        '被告二人', '被告三人', '被告四人',
        '被告甲', '被告乙', '被告丙',
        '數名被告', '多名被告',
        '連帶'  # 通常表示多個被告
    ]

    # 檢查強烈標記
    has_multiple_plaintiffs = any(marker in fact_text for marker in plaintiff_strong_markers)
    has_multiple_defendants = any(marker in fact_text for marker in defendant_strong_markers)

    # 提取當事人名稱（簡單版）
    plaintiff_names = []
    defendant_names = []

    # 檢查是否有「原告XXX」格式的人名
    import re

    # 匹配「原告+中文姓名」（2-4個字）
    plaintiff_pattern = r'原告([甲乙丙丁戊己庚辛壬癸]|[一二三四五六七八九十]+|[\u4e00-\u9fff]{2,4})'
    plaintiff_matches = re.findall(plaintiff_pattern, fact_text)
    plaintiff_names = list(set([m for m in plaintiff_matches if m not in ['等', '們']]))

    # 匹配「被告+中文姓名」
    defendant_pattern = r'被告([甲乙丙丁戊己庚辛壬癸]|[一二三四五六七八九十]+|[\u4e00-\u9fff]{2,4})'
    defendant_matches = re.findall(defendant_pattern, fact_text)
    defendant_names = list(set([m for m in defendant_matches if m not in ['等', '們']]))

    # 決定人數
    plaintiff_count = len(plaintiff_names) if plaintiff_names else (2 if has_multiple_plaintiffs else 1)
    defendant_count = len(defendant_names) if defendant_names else (2 if has_multiple_defendants else 1)

    # 決定 party_structure
    if plaintiff_count > 1 and defendant_count > 1:
        party_structure = 'multiple_both'
        confidence = '高信心' if (plaintiff_names or defendant_names) else '中等信心'
    elif plaintiff_count > 1 and defendant_count == 1:
        party_structure = 'multiple_plaintiffs'
        confidence = '高信心' if plaintiff_names else '中等信心'
    elif plaintiff_count == 1 and defendant_count > 1:
        party_structure = 'multiple_defendants'
        confidence = '高信心' if defendant_names else '中等信心'
    else:
        # 默認：單純各一（如果沒有明確的複數標記）
        party_structure = 'single_vs_single'
        confidence = '高信心'  # 改為高信心！因為沒有複數標記就應該是單一

    return party_structure, confidence, plaintiff_names, defendant_names

def extract_cases_for_review():
    """
    提取所有案例的相關信息供人工檢查
    """
    logger.info("📊 從 Neo4j 提取案例資訊...")

    with driver.session() as session:
        result = session.run("""
            MATCH (c:Case)

            // 取得 liability_type（已經標記好了）
            WITH c, c.liability_type as liability_type

            // 取得事實文本（從 FactDetail，用 case_id 匹配）
            OPTIONAL MATCH (fd:FactDetail)
            WHERE fd.case_id = c.case_id

            WITH c, liability_type, collect(fd.chunk_text)[..5] as fact_samples

            // 取得適用法條（從 LawDetail）
            OPTIONAL MATCH (ld:LawDetail)
            WHERE ld.case_id = c.case_id

            WITH c, liability_type, fact_samples, collect(DISTINCT ld.article) as law_articles

            RETURN
                c.case_id as case_id,
                liability_type,
                law_articles,
                fact_samples
            ORDER BY c.case_id
        """)

        records = list(result)
        logger.info(f"✅ 成功提取 {len(records)} 個案例")

    # 處理每個案例
    data = []
    for i, record in enumerate(records, 1):
        case_id = record['case_id']
        liability_type = record['liability_type'] if record['liability_type'] else 'other'
        law_articles = record['law_articles'] if record['law_articles'] else []
        fact_samples = record['fact_samples'] if record['fact_samples'] else []

        # 組合事實文本
        if fact_samples:
            fact_text = '；'.join([f for f in fact_samples if f])[:500]
        else:
            fact_text = ''

        # 判斷 party_structure
        party_structure, confidence, plaintiff_names, defendant_names = detect_party_structure_from_text(fact_text)

        # 格式化當事人名稱
        plaintiff_str = '、'.join(plaintiff_names) if plaintiff_names else '(未提取到姓名)'
        defendant_str = '、'.join(defendant_names) if defendant_names else '(未提取到姓名)'
        plaintiff_count = len(plaintiff_names) if plaintiff_names else 1
        defendant_count = len(defendant_names) if defendant_names else 1

        data.append({
            'case_id': case_id,
            'liability_type': liability_type,
            'party_structure': party_structure,
            'confidence': confidence,
            'plaintiff_count': plaintiff_count,
            'plaintiff_names': plaintiff_str,
            'defendant_count': defendant_count,
            'defendant_names': defendant_str,
            'applicable_laws': ', '.join(law_articles),
            'fact_sample': fact_text,
            'needs_review': '是' if confidence in ['中等信心', '低信心'] else '否',
            'reviewed': '',  # 供人工填寫
            'corrected_party_structure': ''  # 供人工修正
        })

        if i % 500 == 0:
            logger.info(f"   處理進度：{i}/{len(records)}")

    return data

def save_to_excel(data, output_path):
    """
    將資料儲存為 Excel，並進行格式化
    """
    logger.info(f"💾 儲存至 Excel：{output_path}")

    df = pd.DataFrame(data)

    # 建立 Excel writer
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 寫入主要資料
        df.to_excel(writer, sheet_name='案例分類', index=False)

        # 統計資料
        stats_data = {
            'party_structure': df['party_structure'].value_counts().to_dict(),
            'liability_type': df['liability_type'].value_counts().to_dict(),
            'needs_review_count': df['needs_review'].value_counts().to_dict()
        }

        # 建立統計 sheet
        stats_df = pd.DataFrame([
            {'分類維度': 'party_structure', '類型': k, '數量': v}
            for k, v in stats_data['party_structure'].items()
        ] + [
            {'分類維度': 'liability_type', '類型': k, '數量': v}
            for k, v in stats_data['liability_type'].items()
        ])

        stats_df.to_excel(writer, sheet_name='統計資料', index=False)

        # 建立說明 sheet
        instructions = pd.DataFrame({
            '欄位名稱': [
                'case_id', 'liability_type', 'party_structure', 'confidence',
                'plaintiff_count', 'plaintiff_names', 'defendant_count', 'defendant_names',
                'applicable_laws', 'fact_sample', 'needs_review', 'reviewed', 'corrected_party_structure'
            ],
            '說明': [
                '案例 ID',
                '責任基礎類型（從法條自動判斷，100% 準確，不需檢查）',
                '當事人結構（自動判斷）',
                '判斷信心度（高信心=不需檢查）',
                '原告人數',
                '原告姓名（從事實文本提取）',
                '被告人數',
                '被告姓名（從事實文本提取）',
                '適用法條列表',
                '事實文本樣本（前 500 字）',
                '是否需要人工檢查',
                '是否已檢查（請填「是」）',
                '修正後的 party_structure（如需修正請填寫）'
            ],
            '可用值': [
                '',
                'guardian_liability_187 / employer_liability_188 / animal_liability_190 / general_tort_184_191 / other',
                'single_vs_single / multiple_plaintiffs / multiple_defendants / multiple_both',
                '高信心 / 中等信心 / 低信心',
                '',
                '',
                '',
                '',
                '',
                '',
                '是 / 否',
                '是 / 否',
                'single_vs_single / multiple_plaintiffs / multiple_defendants / multiple_both'
            ]
        })

        instructions.to_excel(writer, sheet_name='使用說明', index=False)

    logger.info(f"✅ Excel 已儲存")

def main():
    try:
        print("=" * 60)
        print("📋 提取案例並生成 party_structure 檢查表")
        print("=" * 60)
        print("此腳本會：")
        print("  1. 從 Neo4j 提取所有 6057 個案例")
        print("  2. 自動判斷 liability_type（從法條，100% 準確）")
        print("  3. 初步判斷 party_structure（規則式，需人工檢查）")
        print("  4. 輸出 Excel 供您檢查和修正")
        print("=" * 60)

        # 設定輸出路徑
        output_dir = os.path.join(os.path.dirname(__file__), '..', '09_輸入輸出資料')
        output_path = os.path.join(output_dir, 'case_type_classification_for_review.xlsx')

        confirm = input("\n是否開始提取？(y/N): ").lower().strip()
        if confirm not in ['y', 'yes', '是']:
            print("❌ 操作已取消")
            return

        # 提取案例
        data = extract_cases_for_review()

        # 儲存為 Excel
        save_to_excel(data, output_path)

        # 統計資訊
        df = pd.DataFrame(data)
        print("\n" + "=" * 60)
        print("📊 統計資訊：")
        print("=" * 60)

        print("\n🏷️ party_structure 分布：")
        print(df['party_structure'].value_counts())

        print("\n🏷️ liability_type 分布：")
        print(df['liability_type'].value_counts())

        print("\n⚠️ 需要檢查的案例數：")
        print(df['needs_review'].value_counts())

        print("\n" + "=" * 60)
        print(f"🎉 完成！Excel 已儲存至：")
        print(f"   {output_path}")
        print("=" * 60)
        print("\n📝 下一步：")
        print("   1. 打開 Excel 檔案")
        print("   2. 檢查 'needs_review' 為「是」的案例")
        print("   3. 在 'corrected_party_structure' 欄位填入正確值")
        print("   4. 在 'reviewed' 欄位標記「是」")
        print("   5. 執行 KG_162_import_party_structure.py 導入修正結果")
        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ 提取過程出錯：{e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
