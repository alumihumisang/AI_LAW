#!/usr/bin/env python3
"""
AI 自動標註案例相似度
基於明確的規則進行客觀標註
"""
import pandas as pd
import os
import re


def parse_summary(summary):
    """
    解析摘要，提取關鍵信息
    格式：被告{violation}導致原告{injury}，屬{liability}，判賠{amount}
    """
    info = {
        'violation': None,
        'injury': None,
        'liability': None,
        'amount': None
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

    # 提取金額（萬元）
    amount_match = re.search(r'約(\d+)萬元', summary)
    if amount_match:
        info['amount'] = int(amount_match.group(1))

    return info


def calculate_similarity_score(info_a, info_b):
    """
    計算兩個案例的相似度分數（1-5）

    規則：
    5分 = 責任類型相同 + 違規相同 + 傷害相同 + 金額接近（差距 < 30%）
    4分 = 責任類型相同 + (違規相同 OR 傷害相同) + 金額差距 < 2倍
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
    score = 3  # 基礎分數
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

    # 檢查金額
    if info_a['amount'] and info_b['amount']:
        ratio = max(info_a['amount'], info_b['amount']) / min(info_a['amount'], info_b['amount'])
        if ratio < 1.3:  # 差距 < 30%
            score += 0.5
            reason.append("金額接近")
        elif ratio < 2.0:  # 差距 < 2倍
            score += 0.3
            reason.append("金額相近")
        elif ratio > 5.0:  # 差距 > 5倍
            score -= 0.5
            reason.append("金額差異大")

    # 最終評分邏輯
    if violation_match and injury_match and score >= 4.5:
        return 5, "；".join(reason)
    elif score >= 4.0:
        return 4, "；".join(reason)
    elif score >= 3.5:
        return 4, "；".join(reason)  # 四捨五入到 4
    elif score >= 2.5:
        return 3, "；".join(reason)
    elif score >= 1.5:
        return 2, "；".join(reason)
    else:
        return 1, "；".join(reason)


def annotate_cases():
    """
    對所有案例對進行標註
    """
    print("=" * 80)
    print("🤖 AI 自動標註案例相似度")
    print("=" * 80)
    print()

    # 讀取標註表
    input_path = '../09_輸入輸出資料/案例相似度標註表_150對.xlsx'
    print(f"📖 讀取標註表：{input_path}")
    df = pd.read_excel(input_path, sheet_name='標註表')
    print(f"   ✅ 共 {len(df)} 對案例")
    print()

    # 標註每一對
    print("🏷️  開始標註...")
    scores = []
    reasons = []

    for i, row in df.iterrows():
        summary_a = row['案例A摘要']
        summary_b = row['案例B摘要']

        # 解析摘要
        info_a = parse_summary(summary_a)
        info_b = parse_summary(summary_b)

        # 計算相似度
        score, reason = calculate_similarity_score(info_a, info_b)

        scores.append(score)
        reasons.append(reason)

        if (i + 1) % 10 == 0:
            print(f"   進度：{i+1}/{len(df)}")

    # 將結果寫入 DataFrame
    df['相似度(1-5)'] = scores
    df['備註'] = reasons

    # 統計
    print()
    print("=" * 80)
    print("📊 標註統計")
    print("=" * 80)
    print()
    print("評分分布：")
    print(df['相似度(1-5)'].value_counts().sort_index())
    print()
    print(f"平均分數：{df['相似度(1-5)'].mean():.2f}")
    print(f"中位數：{df['相似度(1-5)'].median():.1f}")
    print()

    # 顯示範例
    print("=" * 80)
    print("📝 標註範例（前10對）")
    print("=" * 80)
    for i in range(min(10, len(df))):
        row = df.iloc[i]
        print(f"\n【案例對 {i+1}】評分：{row['相似度(1-5)']} 分")
        print(f"  A ({row['案例編號A']}): {row['案例A摘要']}")
        print(f"  B ({row['案例編號B']}): {row['案例B摘要']}")
        print(f"  理由: {row['備註']}")

    # 保存結果
    output_path = '../09_輸入輸出資料/案例相似度標註表_150對_AI標註完成.xlsx'
    print()
    print("=" * 80)
    print(f"💾 保存標註結果：{output_path}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 標註表
        df.to_excel(writer, sheet_name='AI標註結果', index=False)

        # 統計摘要
        stats_df = pd.DataFrame({
            '評分': [1, 2, 3, 4, 5],
            '數量': [
                (df['相似度(1-5)'] == 1).sum(),
                (df['相似度(1-5)'] == 2).sum(),
                (df['相似度(1-5)'] == 3).sum(),
                (df['相似度(1-5)'] == 4).sum(),
                (df['相似度(1-5)'] == 5).sum()
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
                '',
                '標註方法',
                '評分依據'
            ],
            '結果': [
                f"{len(df)} 對",
                f"{df['相似度(1-5)'].mean():.2f}",
                f"{df['相似度(1-5)'].std():.2f}",
                f"{((df['相似度(1-5)'] >= 4).sum())} 對 ({(df['相似度(1-5)'] >= 4).sum() / len(df) * 100:.1f}%)",
                f"{(df['相似度(1-5)'] == 3).sum()} 對 ({(df['相似度(1-5)'] == 3).sum() / len(df) * 100:.1f}%)",
                f"{(df['相似度(1-5)'] <= 2).sum()} 對 ({(df['相似度(1-5)'] <= 2).sum() / len(df) * 100:.1f}%)",
                '',
                'AI 自動標註（基於規則）',
                '責任類型 > 違規行為 > 傷害結果 > 賠償金額'
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
                adjusted_width = min(max_length + 2, 60)
                worksheet.column_dimensions[column_letter].width = adjusted_width

    print(f"   ✅ 保存完成")
    print()
    print("=" * 80)
    print("🎉 標註完成！")
    print("=" * 80)
    print()
    print("📝 下一步：")
    print("  1. 檢查標註結果是否合理")
    print("  2. 使用標註結果計算各層判別力")
    print("  3. 基於判別力確定最終權重")

    return df


if __name__ == "__main__":
    annotate_cases()
