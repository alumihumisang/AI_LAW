#!/usr/bin/env python3
"""
從起訴書 Excel 生成標註表格
使用真實的起訴書內容生成詳細摘要
"""
import os
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
import random
import re

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def extract_key_info(fact_text):
    """
    從事實概述中提取關鍵信息（違規、傷害）
    """
    if not fact_text or pd.isna(fact_text):
        return None, None

    # 提取違規行為
    violation = None
    if '闖紅燈' in fact_text or '紅燈' in fact_text:
        violation = '闖紅燈'
    elif '酒駕' in fact_text or '飲酒' in fact_text:
        violation = '酒駕'
    elif '超速' in fact_text:
        violation = '超速'
    elif '左轉' in fact_text and ('未' in fact_text or '疏' in fact_text):
        violation = '違規左轉'
    elif '貿然' in fact_text and ('駛出' in fact_text or '變換' in fact_text):
        violation = '貿然駛出'
    elif '未保持安全距離' in fact_text or '未保持' in fact_text:
        violation = '未保持安全距離'
    elif '未禮讓' in fact_text:
        violation = '未禮讓'
    elif '疏未注意' in fact_text:
        violation = '疏未注意'
    else:
        violation = '違規'

    # 提取傷害類型
    injury = None
    if '死亡' in fact_text:
        injury = '死亡'
    elif '骨折' in fact_text:
        injury = '骨折'
    elif '腦' in fact_text and ('震盪' in fact_text or '創' in fact_text or '梗塞' in fact_text):
        injury = '腦部傷害'
    elif '植物人' in fact_text:
        injury = '植物人'
    elif '擦傷' in fact_text or '挫傷' in fact_text:
        injury = '擦傷/挫傷'
    elif '受傷' in fact_text:
        injury = '受傷'
    else:
        injury = '受傷'

    return violation, injury


def extract_total_amount(conclusion_text):
    """
    從結論中提取總賠償金額
    """
    if not conclusion_text or pd.isna(conclusion_text):
        return None

    # 尋找金額（可能格式：1,237,470元、123萬、1,237,470）
    patterns = [
        r'合計[\s]*([0-9,]+)元',
        r'總計[\s]*([0-9,]+)元',
        r'賠償[\s]*([0-9,]+)元',
        r'([0-9,]+)元'
    ]

    for pattern in patterns:
        match = re.search(pattern, conclusion_text)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = int(amount_str)
                return amount
            except:
                continue

    return None


def generate_case_summary(case_id, indictment_df):
    """
    生成案例摘要（從起訴書內容）
    """
    # 從 DataFrame 中找到這個案例
    case_row = indictment_df[indictment_df['case_id'] == int(case_id)]

    if case_row.empty:
        return f"案例{case_id}（資料不足）"

    row = case_row.iloc[0]

    # 提取關鍵信息
    violation, injury = extract_key_info(row['事實概述'])
    total_amount = extract_total_amount(row['結論'])

    # 從法條判斷責任類型
    law_text = str(row['法條引用']) if not pd.isna(row['法條引用']) else ''

    if '民法第187條' in law_text or '監護人' in law_text:
        liability = '監護人責任'
    elif '民法第188條' in law_text or '僱用人' in law_text:
        liability = '僱用人責任'
    elif '民法第190條' in law_text or '動物' in law_text:
        liability = '動物侵權'
    elif '民法第184條' in law_text:
        liability = '一般過失侵權'
    elif '民法第191條之2' in law_text:
        liability = '一般過失侵權'
    else:
        liability = '一般過失侵權'

    # 格式化金額
    if total_amount and total_amount > 0:
        if total_amount >= 10000:
            amount_str = f"約{int(total_amount/10000)}萬元"
        else:
            amount_str = f"{total_amount}元"
    else:
        amount_str = "未明"

    # 組合摘要
    summary = f"被告{violation}導致原告{injury}，屬{liability}，判賠{amount_str}"

    return summary


def select_case_pairs_from_neo4j():
    """
    從 Neo4j 選擇案例對（基於 liability_type）
    """
    print("🔍 從 Neo4j 選擇案例對...")

    with driver.session() as session:
        # 相似案例對：責任類型相同
        similar_result = session.run("""
            MATCH (c1:Case), (c2:Case)
            WHERE c1.case_id < c2.case_id
              AND c1.liability_type = c2.liability_type
              AND c1.party_structure = c2.party_structure
              AND c1.liability_type <> 'other'
              AND c1.liability_type IS NOT NULL
            RETURN c1.case_id as case1, c2.case_id as case2
            ORDER BY rand()
            LIMIT 30
        """)

        similar_pairs = [(str(r['case1']), str(r['case2'])) for r in similar_result]
        print(f"   ✅ 找到 {len(similar_pairs)} 對相似案例")

        # 不相似案例對：責任類型不同
        dissimilar_result = session.run("""
            MATCH (c1:Case), (c2:Case)
            WHERE c1.case_id < c2.case_id
              AND c1.liability_type <> c2.liability_type
              AND c1.liability_type <> 'other'
              AND c2.liability_type <> 'other'
              AND c1.liability_type IS NOT NULL
              AND c2.liability_type IS NOT NULL
            RETURN c1.case_id as case1, c2.case_id as case2
            ORDER BY rand()
            LIMIT 30
        """)

        dissimilar_pairs = [(str(r['case1']), str(r['case2'])) for r in dissimilar_result]
        print(f"   ✅ 找到 {len(dissimilar_pairs)} 對不相似案例")

        return similar_pairs, dissimilar_pairs


def main():
    try:
        print("=" * 80)
        print("📋 從起訴書生成案例相似度標註表（改進版）")
        print("=" * 80)
        print()

        # Step 1: 讀取起訴書 Excel
        print("📖 讀取起訴書資料...")
        indictment_path = os.path.join(os.path.dirname(__file__), '..',
                                       '09_輸入輸出資料', '整合_起訴書_四段(FINAL)_6057.xlsx')
        indictment_df = pd.read_excel(indictment_path)
        print(f"   ✅ 讀取完成，共 {len(indictment_df)} 筆起訴書")

        # Step 2: 從 Neo4j 選擇案例對
        similar_pairs, dissimilar_pairs = select_case_pairs_from_neo4j()

        # Step 3: 生成摘要
        print("\n📝 生成案例摘要...")
        data = []

        # 處理相似案例對
        print("   處理相似案例對...")
        for i, (case1, case2) in enumerate(similar_pairs, 1):
            summary1 = generate_case_summary(case1, indictment_df)
            summary2 = generate_case_summary(case2, indictment_df)

            data.append({
                '案例編號A': case1,
                '案例A摘要': summary1,
                '案例編號B': case2,
                '案例B摘要': summary2,
                '相似度(1-5)': '',
                '備註': '',
                '_expected': '相似'
            })

            if i % 10 == 0:
                print(f"      進度：{i}/30")

        # 處理不相似案例對
        print("   處理不相似案例對...")
        for i, (case1, case2) in enumerate(dissimilar_pairs, 1):
            summary1 = generate_case_summary(case1, indictment_df)
            summary2 = generate_case_summary(case2, indictment_df)

            data.append({
                '案例編號A': case1,
                '案例A摘要': summary1,
                '案例編號B': case2,
                '案例B摘要': summary2,
                '相似度(1-5)': '',
                '備註': '',
                '_expected': '不相似'
            })

            if i % 10 == 0:
                print(f"      進度：{i}/30")

        # Step 4: 隨機打亂
        print("\n🔀 隨機打亂順序...")
        random.shuffle(data)

        # Step 5: 建立 DataFrame
        df = pd.DataFrame(data)
        df_export = df.drop(columns=['_expected'])

        # Step 6: 儲存為 Excel
        output_dir = os.path.join(os.path.dirname(__file__), '..', '09_輸入輸出資料')
        output_path = os.path.join(output_dir, '案例相似度標註表_給法律系_v2.xlsx')

        print(f"\n💾 儲存為 Excel...")

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: 標註表
            df_export.to_excel(writer, sheet_name='標註表', index=False)

            # Sheet 2: 使用說明
            instructions = pd.DataFrame({
                '標註指引': [
                    '=== 交通事故案例相似度標註 ===',
                    '',
                    '【任務說明】',
                    '您將看到 60 對交通事故起訴書案例，請判斷每對案例的相似程度。',
                    '預計時間：15-20 分鐘',
                    '',
                    '【評分標準（5級量表）】',
                    '',
                    '5分 - 非常相似',
                    '  ✓ 兩個案例幾乎一模一樣',
                    '  ✓ 如果你是律師，會直接引用案例B來主張案例A的賠償',
                    '  ✓ 例如：都是闖紅燈導致骨折，賠償金額接近',
                    '',
                    '4分 - 相似',
                    '  ✓ 兩個案例大致相同，但有一些差異',
                    '  ✓ 案例B可以作為案例A的重要參考',
                    '  ✓ 例如：都是闖紅燈導致骨折，但金額差較多',
                    '',
                    '3分 - 普通',
                    '  ✓ 兩個案例有部分相同之處',
                    '  ✓ 案例B勉強可以參考',
                    '  ✓ 例如：都是交通事故骨折，但違規行為不同',
                    '',
                    '2分 - 不太相似',
                    '  ✓ 兩個案例差異很大',
                    '  ✓ 案例B不適合參考',
                    '  ✓ 例如：一個骨折賠50萬，一個死亡賠500萬',
                    '',
                    '1分 - 完全不相似',
                    '  ✓ 兩個案例完全不同類型',
                    '  ✓ 案例B完全無法參考',
                    '  ✓ 例如：一個是一般過失，一個是監護人責任',
                    '',
                    '【判斷重點（依重要性排序）】',
                    '',
                    '1. 責任類型（最重要！）',
                    '   • 是否都是「一般過失侵權」？',
                    '   • 如果責任類型不同 → 通常是 1-2 分',
                    '',
                    '2. 違規行為',
                    '   • 闖紅燈、超速、酒駕、違規左轉等是否相似？',
                    '',
                    '3. 傷害結果',
                    '   • 死亡、骨折、腦部傷害、擦傷等是否相似？',
                    '',
                    '4. 賠償金額',
                    '   • 是否在同一數量級？',
                    '   • 50萬 vs 80萬 算接近',
                    '   • 50萬 vs 500萬 差很多',
                    '',
                    '【範例】',
                    '',
                    '案例A：被告闖紅燈導致原告骨折，屬一般過失侵權，判賠約80萬元',
                    '案例B：被告闖紅燈導致原告骨折，屬一般過失侵權，判賠約85萬元',
                    '→ 評分：5分（非常相似）',
                    '',
                    '案例A：被告闖紅燈導致原告骨折，屬一般過失侵權，判賠約80萬元',
                    '案例B：被告疏未注意導致原告受傷，屬監護人責任，判賠約5萬元',
                    '→ 評分：1分（責任類型完全不同）',
                    '',
                    '案例A：被告闖紅燈導致原告骨折，屬一般過失侵權，判賠約80萬元',
                    '案例B：被告酒駕導致原告死亡，屬一般過失侵權，判賠約500萬元',
                    '→ 評分：2分（違規嚴重程度和傷害結果都差很多）',
                    '',
                    '【注意事項】',
                    '• 請憑直覺判斷，不需要過度思考',
                    '• 沒有標準答案，您的專業判斷就是答案',
                    '• 如果難以判斷，請選中間值（3分）',
                    '• 每對案例建議花 10-15 秒即可',
                    '',
                    '【如何填寫】',
                    '請在「標註表」分頁的「相似度(1-5)」欄位填入 1-5 的數字',
                    '「備註」欄位可選填您的想法',
                    '',
                    '感謝您的協助！'
                ]
            })
            instructions.to_excel(writer, sheet_name='使用說明', index=False)

            # 調整欄寬
            worksheet = writer.sheets['標註表']
            worksheet.column_dimensions['A'].width = 12
            worksheet.column_dimensions['B'].width = 55
            worksheet.column_dimensions['C'].width = 12
            worksheet.column_dimensions['D'].width = 55
            worksheet.column_dimensions['E'].width = 15
            worksheet.column_dimensions['F'].width = 30

            worksheet_inst = writer.sheets['使用說明']
            worksheet_inst.column_dimensions['A'].width = 80

        print(f"✅ Excel 檔案已生成：{output_path}")
        print(f"\n📊 統計：")
        print(f"   總案例對數：{len(data)}")
        print(f"   相似案例對：{sum(1 for d in data if d['_expected'] == '相似')}")
        print(f"   不相似案例對：{sum(1 for d in data if d['_expected'] == '不相似')}")

        # 顯示前5個摘要範例
        print(f"\n📝 摘要範例（前5對）：")
        for i in range(min(5, len(df_export))):
            row = df_export.iloc[i]
            print(f"\n  案例對 {i+1}:")
            print(f"    A ({row['案例編號A']}): {row['案例A摘要']}")
            print(f"    B ({row['案例編號B']}): {row['案例B摘要']}")

        print("\n" + "=" * 80)
        print("🎉 完成！")
        print("=" * 80)
        print(f"\n📝 下一步：")
        print(f"   1. 打開檔案：{output_path}")
        print(f"   2. 檢查摘要是否清楚")
        print(f"   3. 將此檔案交給法律系學生標註")

    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()


if __name__ == "__main__":
    main()
