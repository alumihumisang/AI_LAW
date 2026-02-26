#!/usr/bin/env python3
"""
KG_162_import_party_structure.py
從人工修正後的 Excel 導入 party_structure 到 Neo4j
"""
import os
import logging
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

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

def validate_party_structure(value):
    """驗證 party_structure 值是否合法"""
    valid_values = [
        'single_vs_single',
        'multiple_plaintiffs',
        'multiple_defendants',
        'multiple_both',
        'unknown'
    ]
    return value in valid_values

def import_from_excel(excel_path):
    """
    從 Excel 讀取並導入 party_structure 到 Neo4j
    """
    logger.info(f"📂 讀取 Excel：{excel_path}")

    # 讀取 Excel
    df = pd.read_excel(excel_path, sheet_name='案例分類')
    logger.info(f"✅ 讀取 {len(df)} 筆案例")

    # 統計
    updated_count = 0
    skipped_count = 0
    error_count = 0
    stats = {}

    with driver.session() as session:
        for idx, row in df.iterrows():
            case_id = row['case_id']

            # 決定使用哪個 party_structure
            # 優先使用人工修正的值
            if pd.notna(row.get('corrected_party_structure')) and row['corrected_party_structure'].strip():
                party_structure = row['corrected_party_structure'].strip()
                source = '人工修正'
            else:
                party_structure = row['party_structure']
                source = '自動判斷'

            # 驗證值是否合法
            if not validate_party_structure(party_structure):
                logger.warning(f"⚠️ 案例 {case_id} 的 party_structure 值不合法：{party_structure}")
                error_count += 1
                continue

            # 統計
            stats[party_structure] = stats.get(party_structure, 0) + 1

            try:
                # 更新到 Neo4j
                session.run("""
                    MATCH (c:Case {case_id: $case_id})
                    SET c.party_structure = $party_structure
                """, case_id=case_id, party_structure=party_structure)

                updated_count += 1

                if (idx + 1) % 500 == 0:
                    logger.info(f"   處理進度：{idx + 1}/{len(df)}")

            except Exception as e:
                logger.error(f"❌ 案例 {case_id} 更新失敗：{e}")
                error_count += 1

    logger.info(f"\n✅ 導入完成！")
    logger.info(f"   成功更新：{updated_count} 個案例")
    logger.info(f"   跳過：{skipped_count} 個案例")
    logger.info(f"   錯誤：{error_count} 個案例")

    logger.info(f"\n📊 party_structure 分布：")
    for ps_type, count in sorted(stats.items(), key=lambda x: -x[1]):
        logger.info(f"   {ps_type}: {count} 個案例")

    return updated_count, error_count

def verify_import():
    """驗證導入結果"""
    logger.info("\n🔍 驗證導入結果...")

    with driver.session() as session:
        # 檢查 party_structure 覆蓋率
        result = session.run("""
            MATCH (c:Case)
            RETURN
                count(c) as total,
                count(c.party_structure) as with_party_structure
        """).single()

        total = result["total"]
        with_ps = result["with_party_structure"]

        logger.info(f"   總案例數：{total}")
        logger.info(f"   已標記 party_structure：{with_ps} ({with_ps/total*100:.1f}%)")

        # 檢查分布
        distribution = session.run("""
            MATCH (c:Case)
            WHERE c.party_structure IS NOT NULL
            RETURN c.party_structure as type, count(*) as count
            ORDER BY count DESC
        """).data()

        logger.info(f"\n   📈 party_structure 分布：")
        for record in distribution:
            logger.info(f"      {record['type']}: {record['count']} 個案例")

        # 檢查同時有 liability_type 和 party_structure 的案例
        both = session.run("""
            MATCH (c:Case)
            WHERE c.liability_type IS NOT NULL
              AND c.party_structure IS NOT NULL
            RETURN count(c) as count
        """).single()["count"]

        logger.info(f"\n   ✅ 同時有兩種分類的案例：{both} ({both/total*100:.1f}%)")

def main():
    try:
        print("=" * 60)
        print("📥 從 Excel 導入 party_structure 到 Neo4j")
        print("=" * 60)

        # 設定檔案路徑
        input_dir = os.path.join(os.path.dirname(__file__), '..', '09_輸入輸出資料')
        input_path = os.path.join(input_dir, 'case_type_classification_for_review.xlsx')

        # 檢查檔案是否存在
        if not os.path.exists(input_path):
            print(f"❌ 找不到檔案：{input_path}")
            print("請先執行 KG_161_extract_party_structure.py 生成 Excel 檔案")
            return

        print(f"📂 輸入檔案：{input_path}")
        print("\n⚠️ 注意：")
        print("   - 此操作會更新 Neo4j 中的 party_structure 屬性")
        print("   - 優先使用 'corrected_party_structure' 欄位的值")
        print("   - 若該欄位為空，則使用 'party_structure' 欄位的值")

        confirm = input("\n是否開始導入？(y/N): ").lower().strip()
        if confirm not in ['y', 'yes', '是']:
            print("❌ 操作已取消")
            return

        # 執行導入
        updated_count, error_count = import_from_excel(input_path)

        # 驗證結果
        verify_import()

        print("\n" + "=" * 60)
        print("🎉 導入完成！")
        print("=" * 60)

        if error_count > 0:
            print(f"⚠️ 有 {error_count} 個案例導入失敗，請檢查日誌")

    except Exception as e:
        logger.error(f"❌ 導入過程出錯：{e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()

if __name__ == "__main__":
    main()
