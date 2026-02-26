#!/usr/bin/env python3
"""
AI 自動標註案例相似度 - 賠償項目版
使用 Jaccard 相似度比較賠償項目組合
"""
import pandas as pd
import os
import re


def parse_summary(summary):
    """
    解析摘要，提取關鍵信息
    格式：被告{violation}導致原告{injury}，屬{liability}，賠償項目：{items}
    """
    info = {
        'violation': None,
        'injury': None,
        'liability': None,
        'compensation_items': set()
    }

    # 提取違規行為
    if '闖紅燈' in summary:
        info['violation'] = '闖紅燈'
    elif '酒駕' in summary:
        info['violation'] = '酒駕'
    elif '超速' in summary:
        info['violation'] = '超速'
    elif '違規左轉' in summary:
        info['violation'] = '違規左轉'
    elif '貿然駛出' in summary:
        info['violation'] = '貿然駛出'
    elif '未保持安全距離' in summary:
        info['violation'] = '未保持安全距離'
    elif '疏未注意' in summary:
        info['violation'] = '疏未注意'
    elif '違規' in summary:
        info['violation'] = '違規'

    # 提取傷害
    if '死亡' in summary:
        info['injury'] = '死亡'
    elif '植物人' in summary:
        info['injury'] = '植物人'
    elif '腦部傷害' in summary:
        info['injury'] = '腦部傷害'
    elif '骨折' in summary:
        info['injury'] = '骨折'
    elif '擦傷/挫傷' in summary:
        info['injury'] = '擦傷/挫傷'
    elif '受傷' in summary:
        info['injury'] = '受傷'

    # 提取責任類型
    if '監護人責任' in summary:
        info['liability'] = '監護人責任'
    elif '僱用人責任' in summary:
        info['liability'] = '僱用人責任'
    elif '動物侵權' in summary:
        info['liability'] = '動物侵權'
    elif '一般過失侵權' in summary:
        info['liability'] = '一般過失侵權'

    # 提取賠償項目（從「賠償項目：」後面的部分）
    items_match = re.search(r'賠償項目：(.+)$', summary)
    if items_match:
        items_str = items_match.group(1)
        if items_str != '未明':
            # 分割項目（用頓號或逗號）
            items = re.split(r'[、,]', items_str)
            info['compensation_items'] = set(item.strip() for item in items if item.strip())

    return info


def calculate_jaccard_similarity(set_a, set_b):
    """
    計算兩個集合的 Jaccard 相似度
    Jaccard = |A ∩ B| / |A ∪ B|
    """
    if not set_a and not set_b:
        return 1.0  # 兩者都空，視為完全相同
    if not set_a or not set_b:
        return 0.0  # 其中一個空，視為完全不同

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    if union == 0:
        return 0.0

    return intersection / union


def calculate_similarity_score(info_a, info_b):
    """
    計算兩個案例的相似度分數（1-5）

    規則：
    5分 = 責任類型相同 + 違規相同 + 傷害相同 + 項目高度重疊（Jaccard > 0.7）
    4分 = 責任類型相同 + (違規相同 OR 傷害相同) + 項目中度重疊（Jaccard > 0.4）
    3分 = 責任類型相同 + 部分要素相同
    2分 = 責任類型相同但其他差異大，或責任類型不同但有共通點
    1分 = 責任類型完全不同
    """

    # 責任類型不同 → 基本上就是 1 分
    if info_a['liability'] != info_b['liability']:
        # 除非其他要素非常相似，給 2 分
        if info_a['violation'] == info_b['violation'] and info_a['injury'] == info_b['injury']:
            return 2, "責任類型不同但違規和傷害相同"
        return 1, "責任類型不同"

    # 責任類型相同，接下來看其他要素
    score = 3.0  # 基礎分數
    reason = []

    # 檢查違規行為
    violation_match = False
    if info_a['violation'] == info_b['violation']:
        violation_match = True
        score += 0.5
        reason.append("違規相同")
    elif info_a['violation'] and info_b['violation']:
        # 部分違規有相似性
        similar_violations = [
            {'疏未注意', '違規', '貿然駛出'},
            {'闖紅燈', '違規左轉'},
        ]
        for group in similar_violations:
            if info_a['violation'] in group and info_b['violation'] in group:
                score += 0.3
                reason.append("違規類似")
                break

    # 檢查傷害結果
    injury_match = False
    if info_a['injury'] == info_b['injury']:
        injury_match = True
        score += 0.5
        reason.append("傷害相同")
    elif info_a['injury'] and info_b['injury']:
        # 傷害嚴重程度相似
        injury_levels = {
            '死亡': 5, '植物人': 5,
            '腦部傷害': 4,
            '骨折': 3,
            '擦傷/挫傷': 2,
            '受傷': 1
        }
        level_a = injury_levels.get(info_a['injury'], 1)
        level_b = injury_levels.get(info_b['injury'], 1)
        if abs(level_a - level_b) <= 1:
            score += 0.3
            reason.append("傷害程度相近")

    # 檢查賠償項目（用 Jaccard 相似度）
    items_jaccard = calculate_jaccard_similarity(
        info_a['compensation_items'],
        info_b['compensation_items']
    )

    if items_jaccard > 0.7:  # 高度重疊
        score += 0.6
        reason.append(f"項目高度重疊(J={items_jaccard:.2f})")
    elif items_jaccard > 0.5:  # 中高度重疊
        score += 0.4
        reason.append(f"項目中高度重疊(J={items_jaccard:.2f})")
    elif items_jaccard > 0.3:  # 中度重疊
        score += 0.2
        reason.append(f"項目中度重疊(J={items_jaccard:.2f})")
    elif items_jaccard > 0:  # 低度重疊
        reason.append(f"項目低度重疊(J={items_jaccard:.2f})")
    else:  # 完全不重疊
        score -= 0.3
        reason.append("項目完全不重疊")

    # 最終評分邏輯
    if violation_match and injury_match and items_jaccard > 0.7:
        final_score = 5
    elif score >= 4.5:
        final_score = 5
    elif score >= 4.0:
        final_score = 4
    elif score >= 3.5:
        final_score = 4  # 偏向 4 分
    elif score >= 2.8:
        final_score = 3
    elif score >= 2.3:
        final_score = 3  # 偏向 3 分
    elif score >= 1.8:
        final_score = 2
    else:
        final_score = 1

    return final_score, "；".join(reason) if reason else "責任類型不同"


def annotate_cases():
    """
    對所有案例對進行標註（賠償項目版）
    """
    print("="*80)
    print("🤖 AI 自動標註案例相似度 - 賠償項目版")
    print("="*80)
    print("賠償相似度 = Jaccard(項目集合)")
    print("="*80)
    print()

    # 讀取標註表
    input_path = '../09_輸入輸出資料/案例相似度標註表_50query.xlsx'
    print(f"📖 讀取標註表：{input_path}")
    df = pd.read_excel(input_path, sheet_name='標註表')
    print(f"   ✅ 共 {len(df)} 對 (query, 候選案例)")
    print()

    # 標註每一對
    print("🏷️  開始標註...")
    scores = []
    reasons = []

    for i, row in df.iterrows():
        summary_a = row['query摘要']
        summary_b = row['候選案例摘要']

        # 解析摘要
        info_a = parse_summary(summary_a)
        info_b = parse_summary(summary_b)

        # 計算相似度
        score, reason = calculate_similarity_score(info_a, info_b)

        scores.append(score)
        reasons.append(reason)

        if (i + 1) % 30 == 0:
            print(f"   進度：{i+1}/{len(df)}")

    # 將結果寫入 DataFrame
    df['相似度(1-5)'] = scores
    df['備註'] = reasons

    # 統計
    print()
    print("="*80)
    print("📊 標註統計")
    print("="*80)
    print()
    print("評分分布：")
    score_counts = df['相似度(1-5)'].value_counts().sort_index()
    for score, count in score_counts.items():
        percentage = count / len(df) * 100
        print(f"  {score}分：{count:3d}對 ({percentage:5.1f}%)")
    print()
    print(f"平均分數：{df['相似度(1-5)'].mean():.2f}")
    print(f"中位數：{df['相似度(1-5)'].median():.1f}")
    print()

    # 有效樣本統計
    low_similar = (df['相似度(1-5)'] <= 2).sum()
    medium = (df['相似度(1-5)'] == 3).sum()
    high_similar = (df['相似度(1-5)'] >= 4).sum()

    print("有效樣本統計（移除3分後）：")
    print(f"  不相似組（1-2分）：{low_similar}對")
    print(f"  相似組（4-5分）  ：{high_similar}對")
    print(f"  ────────────────────────")
    print(f"  有效樣本總數      ：{low_similar + high_similar}對")
    print(f"  移除（3分）       ：{medium}對")
    print()

    # 顯示範例
    print("="*80)
    print("📝 標註範例（前10對）")
    print("="*80)
    for i in range(min(10, len(df))):
        row = df.iloc[i]
        print(f"\n【第 {i+1} 對】query_id={row['query_id']}, 評分：{row['相似度(1-5)']} 分")
        print(f"  Query:")
        print(f"     {row['query摘要']}")
        print(f"  候選 ({row['候選案例case_id']}):")
        print(f"     {row['候選案例摘要']}")
        print(f"  理由: {row['備註']}")

    # 保存結果
    output_path = '../09_輸入輸出資料/案例相似度標註表_50query_AI標註.xlsx'
    print()
    print("="*80)
    print(f"💾 保存標註結果：{output_path}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 標註表
        df.to_excel(writer, sheet_name='AI標註結果', index=False)

        # 統計摘要
        stats_df = pd.DataFrame({
            '評分': [1, 2, 3, 4, 5],
            '數量': [
                (df['相似度(1-5)'] == i).sum() for i in [1, 2, 3, 4, 5]
            ],
            '百分比': [
                f"{(df['相似度(1-5)'] == i).sum() / len(df) * 100:.1f}%"
                for i in [1, 2, 3, 4, 5]
            ]
        })
        stats_df.to_excel(writer, sheet_name='統計摘要', index=False)

        # 分析說明
        analysis = pd.DataFrame({
            '分析項目': [
                '總案例對數',
                '平均相似度',
                '標準差',
                '高度相似（4-5分）',
                '中等相似（3分）',
                '低度相似（1-2分）',
                '有效樣本數',
                '',
                '標註方法',
                '賠償評估',
                '評分依據'
            ],
            '結果': [
                f"{len(df)} 對",
                f"{df['相似度(1-5)'].mean():.2f}",
                f"{df['相似度(1-5)'].std():.2f}",
                f"{high_similar} 對 ({high_similar / len(df) * 100:.1f}%)",
                f"{medium} 對 ({medium / len(df) * 100:.1f}%)",
                f"{low_similar} 對 ({low_similar / len(df) * 100:.1f}%)",
                f"{low_similar + high_similar} 對",
                '',
                'AI 自動標註（基於規則）',
                'Jaccard 相似度（項目集合）',
                '責任類型 > 違規行為 > 傷害結果 > 賠償項目'
            ]
        })
        analysis.to_excel(writer, sheet_name='標註分析', index=False)

        # 調整欄寬
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 100)  # 加寬以顯示項目
                worksheet.column_dimensions[column_letter].width = adjusted_width

    print(f"   ✅ 保存完成")
    print()
    print("="*80)
    print("🎉 標註完成！")
    print("="*80)
    print()
    print("📝 主要改進：")
    print("  • 賠償相似度用 Jaccard 相似度計算項目集合重疊度")
    print("  • 不看金額，只看項目組成（醫療費、看護費、慰撫金等）")
    print("  • 更符合案例檢索邏輯（相似案例有相似項目組合）")
    print()
    print("📝 下一步：")
    print("  1. 檢查標註結果是否合理")
    print("  2. 使用標註結果計算各層判別力")
    print("  3. 基於判別力確定最終權重")

    return df


if __name__ == "__main__":
    annotate_cases()
