#!/usr/bin/env python3
"""
基於 50 筆真實 query 生成標註表
為每個 query 從 6057 筆資料庫中找候選案例
"""
import os
import pandas as pd
import re
import random
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def extract_compensation_items(text):
    """從文字中提取賠償項目"""
    if not text or pd.isna(text):
        return set()

    text = str(text)
    items = set()

    item_patterns = {
        '醫療費': ['醫療費', '醫藥費', '醫療用品', '復健費'],
        '看護費': ['看護費', '照顧費', '照護費'],
        '慰撫金': ['慰撫金', '精神慰撫金', '精神賠償'],
        '工作損失': ['薪資損失', '工作損失', '收入損失', '業績損失', '營業損失'],
        '車輛損失': ['車輛修理', '機車修理', '汽車修理', '修復費', '修繕費', '車損'],
        '交通費': ['交通費', '車資', '計程車費'],
        '財物損失': ['財物損失', '手機', '眼鏡', '安全帽', '手錶', '衣物'],
        '喪葬費': ['喪葬費', '殯葬費'],
        '扶養費': ['扶養費', '扶養損失'],
        '其他': ['鑑定費', '訴訟費', '代墊款']
    }

    for item_type, keywords in item_patterns.items():
        for keyword in keywords:
            if keyword in text:
                items.add(item_type)
                break

    return items


def extract_query_features(indictment_text, category):
    """
    從 query 的起訴書中提取特徵
    返回：{liability_type, party_structure, violation, injury, compensation_items}
    """
    features = {
        'liability_type': 'general_tort_184_191',
        'party_structure': 'single_vs_single',
        'violation': None,
        'injury': None,
        'compensation_items': set()
    }

    # 根據類別判斷 party_structure（使用 Neo4j 實際的值）
    if '數名原告' in category:
        features['party_structure'] = 'multiple_plaintiffs'
    elif '數名被告' in category:
        features['party_structure'] = 'multiple_defendants'
    elif '原被告皆數名' in category:
        features['party_structure'] = 'multiple_both'
    else:
        features['party_structure'] = 'single_vs_single'

    # 根據類別和法條判斷 liability_type（使用 Neo4j 實際的值）
    if '§187' in category or '未成年' in category:
        features['liability_type'] = 'guardian_liability_187'
    elif '§188' in category or '僱用人' in category:
        features['liability_type'] = 'employer_liability_188'
    elif '§190' in category or '動物' in category:
        features['liability_type'] = 'animal_liability_190'
    else:
        # 從法條引用推斷
        if '民法第187條' in indictment_text or '監護人' in indictment_text:
            features['liability_type'] = 'guardian_liability_187'
        elif '民法第188條' in indictment_text:
            features['liability_type'] = 'employer_liability_188'
        elif '民法第190條' in indictment_text:
            features['liability_type'] = 'animal_liability_190'
        else:
            features['liability_type'] = 'general_tort_184_191'

    # 提取違規行為
    if '闖紅燈' in indictment_text or '紅燈' in indictment_text:
        features['violation'] = '闖紅燈'
    elif '酒駕' in indictment_text or '飲酒' in indictment_text:
        features['violation'] = '酒駕'
    elif '超速' in indictment_text:
        features['violation'] = '超速'
    elif '左轉' in indictment_text and '違規' in indictment_text:
        features['violation'] = '違規左轉'
    elif '貿然' in indictment_text and ('駛出' in indictment_text or '變換' in indictment_text or '迴轉' in indictment_text):
        features['violation'] = '貿然駛出'
    elif '未保持安全距離' in indictment_text:
        features['violation'] = '未保持安全距離'
    elif '疏未注意' in indictment_text or '疏於注意' in indictment_text:
        features['violation'] = '疏未注意'
    else:
        features['violation'] = '違規'

    # 提取傷害類型
    if '死亡' in indictment_text:
        features['injury'] = '死亡'
    elif '骨折' in indictment_text:
        features['injury'] = '骨折'
    elif '植物人' in indictment_text:
        features['injury'] = '植物人'
    elif '腦' in indictment_text and ('震盪' in indictment_text or '創' in indictment_text):
        features['injury'] = '腦部傷害'
    elif '擦傷' in indictment_text or '挫傷' in indictment_text:
        features['injury'] = '擦傷/挫傷'
    else:
        features['injury'] = '受傷'

    # 提取賠償項目
    features['compensation_items'] = extract_compensation_items(indictment_text)

    return features


def find_candidates_from_neo4j(query_features, indictment_df):
    """
    為 query 從 Neo4j 找候選案例
    混合策略：
    - 2 個同 liability_type（相似組）
    - 1 個不同 liability_type（不相似組）
    """
    candidates = []

    with driver.session() as session:
        # 找 2 個同 liability_type 的候選案例
        result_same = session.run("""
            MATCH (c:Case)
            WHERE c.liability_type = $liability_type
            RETURN c.case_id as case_id
            ORDER BY rand()
            LIMIT 2
        """, liability_type=query_features['liability_type'])

        for r in result_same:
            candidates.append(('same_liability', str(r['case_id'])))

        # 找 1 個不同 liability_type 的候選案例
        result_diff = session.run("""
            MATCH (c:Case)
            WHERE c.liability_type <> $liability_type
              AND c.liability_type <> 'other'
            RETURN c.case_id as case_id
            ORDER BY rand()
            LIMIT 1
        """, liability_type=query_features['liability_type'])

        for r in result_diff:
            candidates.append(('different_liability', str(r['case_id'])))

    return candidates


def generate_case_summary_from_db(case_id, indictment_df):
    """從資料庫案例生成摘要（從 Neo4j 查詢 liability_type）"""
    case_row = indictment_df[indictment_df['case_id'] == int(case_id)]

    if case_row.empty:
        return f"案例{case_id}（資料不足）"

    row = case_row.iloc[0]

    # 提取違規
    violation = None
    fact_text = str(row['事實概述']) if not pd.isna(row['事實概述']) else ''
    if '闖紅燈' in fact_text:
        violation = '闖紅燈'
    elif '酒駕' in fact_text:
        violation = '酒駕'
    elif '疏未注意' in fact_text:
        violation = '疏未注意'
    else:
        violation = '違規'

    # 提取傷害
    injury = None
    if '死亡' in fact_text:
        injury = '死亡'
    elif '骨折' in fact_text:
        injury = '骨折'
    else:
        injury = '受傷'

    # 從 Neo4j 查詢責任類型
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Case {case_id: $case_id})
            RETURN c.liability_type as type
        """, case_id=int(case_id))

        liability_type = None
        for r in result:
            liability_type = r['type']
            break

    # 轉換為中文
    liability_map = {
        'general_tort_184_191': '一般過失侵權',
        'guardian_liability_187': '監護人責任',
        'employer_liability_188': '僱用人責任',
        'animal_liability_190': '動物侵權'
    }
    liability = liability_map.get(liability_type, '一般過失侵權')

    # 提取賠償項目
    comp_items = extract_compensation_items(row['損害賠償項目'])
    items_str = '、'.join(sorted(comp_items)) if comp_items else '未明'

    return f"被告{violation}導致原告{injury}，屬{liability}，賠償項目：{items_str}"


def generate_query_summary(indictment_text, features):
    """從 query 起訴書生成摘要"""
    liability_map = {
        'general_tort_184_191': '一般過失侵權',
        'guardian_liability_187': '監護人責任',
        'employer_liability_188': '僱用人責任',
        'animal_liability_190': '動物侵權'
    }

    liability = liability_map.get(features['liability_type'], '一般過失侵權')
    violation = features['violation'] or '違規'
    injury = features['injury'] or '受傷'

    items_str = '、'.join(sorted(features['compensation_items'])) if features['compensation_items'] else '未明'

    return f"被告{violation}導致原告{injury}，屬{liability}，賠償項目：{items_str}"


def main():
    try:
        print("="*80)
        print("📋 基於 50 筆真實 query 生成標註表")
        print("="*80)
        print()

        # Step 1: 讀取 ground truth query
        print("📖 讀取 50 筆 query...")
        query_path = os.path.join(os.path.dirname(__file__), '..',
                                   '09_輸入輸出資料', 'ground truth用.xlsx')
        query_df = pd.read_excel(query_path)

        # 填充類別
        query_df['類別'] = query_df['類別'].fillna(method='ffill')
        print(f"   ✅ 讀取完成，共 {len(query_df)} 筆 query")
        print()
        print("   案型分布：")
        print(query_df['類別'].value_counts().sort_index())
        print()

        # Step 2: 讀取資料庫案例
        print("📖 讀取資料庫案例...")
        indictment_path = os.path.join(os.path.dirname(__file__), '..',
                                       '09_輸入輸出資料', '整合_起訴書_四段(FINAL)_6057.xlsx')
        indictment_df = pd.read_excel(indictment_path)
        print(f"   ✅ 讀取完成，共 {len(indictment_df)} 筆案例")
        print()

        # Step 3: 為每個 query 找候選案例
        print("🔍 為每個 query 找候選案例...")
        data = []
        gpt_col = 'gpt-4o-mini-2024-07-18\n3000筆起訴書\nrun: 20241217'

        for i, row in query_df.iterrows():
            query_id = i + 1
            category = row['類別']
            indictment_text = row[gpt_col]

            if pd.isna(indictment_text):
                continue

            # 提取 query 特徵
            features = extract_query_features(indictment_text, category)

            # 生成 query 摘要
            query_summary = generate_query_summary(indictment_text, features)

            # 找候選案例
            candidates = find_candidates_from_neo4j(features, indictment_df)

            # 為每個候選生成摘要並加入資料
            for candidate_type, case_id in candidates:
                candidate_summary = generate_case_summary_from_db(case_id, indictment_df)

                data.append({
                    'query_id': query_id,
                    '案型': category,
                    'query摘要': query_summary,
                    '候選案例case_id': case_id,
                    '候選案例摘要': candidate_summary,
                    '相似度(1-5)': '',
                    '備註': ''
                })

            if (i + 1) % 10 == 0:
                print(f"   進度：{i+1}/{len(query_df)}")

        print(f"\n   ✅ 共生成 {len(data)} 對 (query, 候選案例)")
        print()

        # Step 4: 建立 DataFrame
        df = pd.DataFrame(data)

        # Step 5: 儲存為 Excel
        output_dir = os.path.join(os.path.dirname(__file__), '..', '09_輸入輸出資料')
        output_path = os.path.join(output_dir, '案例相似度標註表_50query.xlsx')

        print(f"💾 儲存為 Excel...")

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: 標註表
            df.to_excel(writer, sheet_name='標註表', index=False)

            # Sheet 2: 使用說明
            instructions = pd.DataFrame({
                '標註指引': [
                    '=== 基於真實 query 的案例相似度標註（混合策略）===',
                    '',
                    '資料說明：',
                    f'• 50 筆真實 query（GPT-4o-mini 生成的起訴書）',
                    f'• 每個 query 有 3 個候選案例',
                    f'• 候選策略：**2 個同責任類型 + 1 個不同責任類型**',
                    f'• 目的：既測試細粒度相似度，又測試大類區分能力',
                    '',
                    '評分標準：',
                    '5分 = 非常相似（幾乎一樣）',
                    '4分 = 相似（大致相同）',
                    '3分 = 普通（部分相同）',
                    '2分 = 不太相似（差異很大）',
                    '1分 = 完全不相似（完全不同類型）',
                    '',
                    '判斷重點：',
                    '1. 責任類型（§187/§188/§190/一般過失）',
                    '2. 違規行為（闖紅燈 vs 酒駕 vs 疏未注意）',
                    '3. 傷害結果（死亡 vs 骨折 vs 擦傷）',
                    '4. 賠償項目組成（醫療+看護+慰撫 vs 只有慰撫）',
                    '',
                    '請在「相似度(1-5)」欄位填入評分'
                ]
            })
            instructions.to_excel(writer, sheet_name='使用說明', index=False)

            # 調整欄寬
            worksheet = writer.sheets['標註表']
            worksheet.column_dimensions['A'].width = 10  # query_id
            worksheet.column_dimensions['B'].width = 20  # 案型
            worksheet.column_dimensions['C'].width = 80  # query摘要
            worksheet.column_dimensions['D'].width = 12  # case_id
            worksheet.column_dimensions['E'].width = 80  # 候選摘要
            worksheet.column_dimensions['F'].width = 15  # 相似度
            worksheet.column_dimensions['G'].width = 30  # 備註

            worksheet_inst = writer.sheets['使用說明']
            worksheet_inst.column_dimensions['A'].width = 80

        print(f"✅ Excel 檔案已生成：{output_path}")
        print()

        # 統計
        print("="*80)
        print("📊 統計")
        print("="*80)
        print(f"總案例對數：{len(data)}")
        print(f"Query 數量：{len(query_df)}")
        print(f"平均每個 query 的候選數：{len(data) / len(query_df):.1f}")
        print()

        # 按案型統計
        print("各案型的 query 和候選數：")
        for case_type in df['案型'].unique():
            queries = df[df['案型'] == case_type]['query_id'].nunique()
            pairs = len(df[df['案型'] == case_type])
            print(f"  {case_type}: {queries} 個 query, {pairs} 對")
        print()

        # 顯示範例
        print("="*80)
        print("📝 案例範例（前 5 對）")
        print("="*80)

        for i in range(min(5, len(df))):
            row = df.iloc[i]
            print(f"\n【第 {i+1} 對】query_id={row['query_id']}, 案型={row['案型']}")
            print(f"  Query: {row['query摘要']}")
            print(f"  候選 ({row['候選案例case_id']}): {row['候選案例摘要']}")

        print()
        print("="*80)
        print("🎉 完成！")
        print("="*80)
        print()
        print("📝 下一步：執行 AI 標註")
        print("   python annotate_query_by_ai.py")

    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.close()


if __name__ == "__main__":
    main()
