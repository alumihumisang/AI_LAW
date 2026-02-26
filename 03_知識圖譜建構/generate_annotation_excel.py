#!/usr/bin/env python3
"""
生成標註表格的 Excel 檔案
自動從 Neo4j 抽取案例對並生成摘要
"""
import os
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
import random

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def generate_case_summary(case_id, session):
    """
    生成案例摘要（100字內，白話文）
    """
    result = session.run("""
        MATCH (c:Case {case_id: $case_id})

        // 取得事實
        OPTIONAL MATCH (c)-[:HAS_DETAIL]->(fd:FactDetail)
        WITH c, collect(fd.chunk_text)[..3] as facts

        // 取得賠償
        OPTIONAL MATCH (c)-[:HAS_DETAIL]->(cd:CompensationDetail)
        WITH c, facts,
             collect({item: cd.item, amount: cd.amount}) as comps,
             sum(cd.amount) as total_amount

        RETURN
            c.liability_type as liability,
            c.party_structure as party,
            facts,
            total_amount
    """, case_id=case_id)

    record = result.single()
    if not record:
        return f"案例 {case_id}（資料不足）"

    # 簡化責任類型
    liability_map = {
        'general_tort_184': '一般過失侵權',
        'employer_liability_188': '僱用人責任',
        'guardian_liability_187': '監護人責任',
        'animal_liability_190': '動物侵權',
        'other': '其他'
    }
    liability = liability_map.get(record['liability'], '未分類')

    # 合併事實文本
    facts_text = ''.join(record['facts'] or [])

    # 提取關鍵資訊（簡單關鍵字匹配）
    violation = '違規'
    if '闖紅燈' in facts_text or '紅燈' in facts_text:
        violation = '闖紅燈'
    elif '超速' in facts_text:
        violation = '超速'
    elif '酒駕' in facts_text or '飲酒' in facts_text:
        violation = '酒駕'
    elif '未保持安全距離' in facts_text or '未保持' in facts_text:
        violation = '未保持安全距離'
    elif '未禮讓' in facts_text:
        violation = '未禮讓'

    injury = '受傷'
    if '死亡' in facts_text:
        injury = '死亡'
    elif '骨折' in facts_text:
        injury = '骨折'
    elif '腦震盪' in facts_text:
        injury = '腦震盪'
    elif '擦傷' in facts_text or '挫傷' in facts_text:
        injury = '擦傷'
    elif '植物人' in facts_text:
        injury = '植物人'

    # 賠償金額
    total = record['total_amount'] or 0
    if total > 10000:
        amount_str = f"約{int(total/10000)}萬元"
    else:
        amount_str = "未明"

    # 組合摘要
    summary = f"被告{violation}導致原告{injury}，屬{liability}，判賠{amount_str}"

    return summary


def select_case_pairs():
    """
    自動選擇 60 對案例
    30 對相似 + 30 對不相似
    """
    print("🔍 從 Neo4j 選擇案例對...")

    with driver.session() as session:
        # ========== 相似案例對 ==========
        print("\n選擇相似案例對（責任類型相同 + 當事人結構相同）...")

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

        similar_pairs = [(r['case1'], r['case2']) for r in similar_result]
        print(f"   ✅ 找到 {len(similar_pairs)} 對相似案例")

        # ========== 不相似案例對 ==========
        print("\n選擇不相似案例對（責任類型不同）...")

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

        dissimilar_pairs = [(r['case1'], r['case2']) for r in dissimilar_result]
        print(f"   ✅ 找到 {len(dissimilar_pairs)} 對不相似案例")

        return similar_pairs, dissimilar_pairs


def generate_excel():
    """
    生成完整的標註 Excel 檔案
    """
    # Step 1: 選擇案例對
    similar_pairs, dissimilar_pairs = select_case_pairs()

    # Step 2: 生成摘要
    print("\n📝 生成案例摘要...")

    data = []

    with driver.session() as session:
        # 處理相似案例對
        print("   處理相似案例對...")
        for i, (case1, case2) in enumerate(similar_pairs, 1):
            summary1 = generate_case_summary(case1, session)
            summary2 = generate_case_summary(case2, session)

            data.append({
                '案例編號A': case1,
                '案例A摘要': summary1,
                '案例編號B': case2,
                '案例B摘要': summary2,
                '相似度(1-5)': '',
                '備註': '',
                '_expected': '相似'  # 內部標記，最後會移除
            })

            if i % 10 == 0:
                print(f"      進度：{i}/30")

        # 處理不相似案例對
        print("   處理不相似案例對...")
        for i, (case1, case2) in enumerate(dissimilar_pairs, 1):
            summary1 = generate_case_summary(case1, session)
            summary2 = generate_case_summary(case2, session)

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

    # Step 3: 隨機打亂順序（不要讓標註者看出前30個都是相似的）
    print("\n🔀 隨機打亂順序...")
    random.shuffle(data)

    # Step 4: 建立 DataFrame
    df = pd.DataFrame(data)

    # 移除內部標記欄位
    df_export = df.drop(columns=['_expected'])

    # Step 5: 儲存為 Excel
    output_dir = os.path.join(os.path.dirname(__file__), '..', '09_輸入輸出資料')
    output_path = os.path.join(output_dir, '案例相似度標註表_給法律系.xlsx')

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
                '您將看到 60 對交通事故判決案例，請判斷每對案例的相似程度。',
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
                '  ✓ 例如：都是闖紅燈導致骨折，但交通工具不同',
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
                '   • 闖紅燈、超速、酒駕等是否相似？',
                '',
                '3. 傷害結果',
                '   • 死亡、骨折、擦傷等是否相似？',
                '',
                '4. 賠償金額',
                '   • 是否在同一數量級？',
                '   • 50萬 vs 80萬 算接近',
                '   • 50萬 vs 500萬 差很多',
                '',
                '【範例】',
                '',
                '案例A：被告闖紅燈導致原告骨折，判賠50萬',
                '案例B：被告闖紅燈導致原告骨折，判賠80萬',
                '→ 評分：5分（非常相似）',
                '',
                '案例A：被告闖紅燈導致原告骨折，判賠50萬',
                '案例B：未成年人騎車撞人，家長負監護人責任，判賠5萬',
                '→ 評分：1分（責任類型完全不同）',
                '',
                '案例A：被告闖紅燈導致原告骨折，判賠50萬',
                '案例B：被告酒駕撞死行人，判賠500萬',
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
        worksheet.column_dimensions['A'].width = 12  # 案例編號A
        worksheet.column_dimensions['B'].width = 50  # 案例A摘要
        worksheet.column_dimensions['C'].width = 12  # 案例編號B
        worksheet.column_dimensions['D'].width = 50  # 案例B摘要
        worksheet.column_dimensions['E'].width = 15  # 相似度
        worksheet.column_dimensions['F'].width = 30  # 備註

        worksheet_inst = writer.sheets['使用說明']
        worksheet_inst.column_dimensions['A'].width = 80

    print(f"✅ Excel 檔案已生成：{output_path}")
    print(f"\n📊 統計：")
    print(f"   總案例對數：{len(data)}")
    print(f"   相似案例對：{sum(1 for d in data if d['_expected'] == '相似')}")
    print(f"   不相似案例對：{sum(1 for d in data if d['_expected'] == '不相似')}")
    print(f"\n📝 下一步：")
    print(f"   1. 打開檔案檢查內容")
    print(f"   2. 先閱讀「使用說明」分頁")
    print(f"   3. 在「標註表」分頁填寫相似度")
    print(f"   4. 或將此檔案交給法律系學生標註")

    return output_path


def main():
    try:
        print("=" * 80)
        print("📋 生成案例相似度標註表")
        print("=" * 80)
        print()

        output_path = generate_excel()

        print("\n" + "=" * 80)
        print("🎉 完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()


if __name__ == "__main__":
    main()
