#!/usr/bin/env python3
"""
計算各維度的 Fisher 判別力（基於 50 query 標註）
"""
import pandas as pd
import numpy as np
import re


def parse_summary(summary):
    """解析摘要，提取各維度信息"""
    info = {
        'violation': None,
        'injury': None,
        'liability': None,
        'compensation_items': set()
    }

    # 提取違規
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

    # 提取賠償項目
    items_match = re.search(r'賠償項目：(.+)$', summary)
    if items_match:
        items_str = items_match.group(1)
        if items_str != '未明':
            items = re.split(r'[、,]', items_str)
            info['compensation_items'] = set(item.strip() for item in items if item.strip())

    return info


def calculate_dimension_similarity(info_a, info_b, dimension):
    """
    計算單一維度的相似度（0-1）

    這是 Fisher 分析的核心：
    - 把每個維度量化為 0-1 的相似度分數
    - 然後看「相似組」和「不相似組」在這個分數上的差異
    """

    if dimension == 'liability':
        # 責任類型：完全匹配=1.0，不匹配=0.0
        return 1.0 if info_a['liability'] == info_b['liability'] else 0.0

    elif dimension == 'violation':
        # 違規行為：完全匹配=1.0，類似=0.6，不同=0.0
        if info_a['violation'] == info_b['violation']:
            return 1.0
        elif info_a['violation'] and info_b['violation']:
            similar_violations = [
                {'疏未注意', '違規', '貿然駛出'},
                {'闖紅燈', '違規左轉'},
            ]
            for group in similar_violations:
                if info_a['violation'] in group and info_b['violation'] in group:
                    return 0.6
            return 0.0
        else:
            return 0.0

    elif dimension == 'injury':
        # 傷害結果：基於嚴重程度量化
        if info_a['injury'] == info_b['injury']:
            return 1.0
        elif info_a['injury'] and info_b['injury']:
            injury_levels = {
                '死亡': 5, '植物人': 5,
                '腦部傷害': 4,
                '骨折': 3,
                '擦傷/挫傷': 2,
                '受傷': 1
            }
            level_a = injury_levels.get(info_a['injury'], 1)
            level_b = injury_levels.get(info_b['injury'], 1)
            level_diff = abs(level_a - level_b)

            # 差距越小，相似度越高
            if level_diff == 0:
                return 1.0
            elif level_diff == 1:
                return 0.75
            elif level_diff == 2:
                return 0.5
            elif level_diff == 3:
                return 0.25
            else:
                return 0.0
        else:
            return 0.0

    elif dimension == 'items':
        # 賠償項目：用 Jaccard 相似度
        if not info_a['compensation_items'] and not info_b['compensation_items']:
            return 1.0
        if not info_a['compensation_items'] or not info_b['compensation_items']:
            return 0.0

        intersection = len(info_a['compensation_items'] & info_b['compensation_items'])
        union = len(info_a['compensation_items'] | info_b['compensation_items'])

        return intersection / union if union > 0 else 0.0

    else:
        return 0.0


def calculate_fisher_discriminant(df_valid):
    """
    計算各維度的 Fisher 判別力

    Fisher Score = (類間距離)² / (類內方差)

    - 類間距離：相似組和不相似組的平均值差異
    - 類內方差：兩組內部的變異程度
    - 分數越高 → 該維度越能有效區分相似/不相似案例
    """

    dimensions = ['liability', 'violation', 'injury', 'items']
    results = {}

    print("="*80)
    print("📊 Fisher 判別力分析")
    print("="*80)
    print()
    print("目標：評估各維度區分「相似」vs「不相似」案例的能力")
    print()
    print(f"有效樣本數：{len(df_valid)} 對")
    print(f"  - 相似組（4-5分）：{(df_valid['相似度(1-5)'] >= 4).sum()} 對")
    print(f"  - 不相似組（1-2分）：{(df_valid['相似度(1-5)'] <= 2).sum()} 對")
    print()

    for dim in dimensions:
        print("="*80)
        print(f"維度：{dim}")
        print("="*80)

        # Step 1: 計算每對案例在該維度的相似度
        similarities = []
        labels = []

        for _, row in df_valid.iterrows():
            info_query = parse_summary(row['query摘要'])
            info_candidate = parse_summary(row['候選案例摘要'])

            sim = calculate_dimension_similarity(info_query, info_candidate, dim)
            similarities.append(sim)

            # 標籤：4-5分為相似(1)，1-2分為不相似(0)
            label = 1 if row['相似度(1-5)'] >= 4 else 0
            labels.append(label)

        similarities = np.array(similarities)
        labels = np.array(labels)

        # Step 2: 分成兩組
        similar_group = similarities[labels == 1]
        dissimilar_group = similarities[labels == 0]

        # Step 3: 計算統計量
        mean_similar = np.mean(similar_group)
        mean_dissimilar = np.mean(dissimilar_group)
        var_similar = np.var(similar_group)
        var_dissimilar = np.var(dissimilar_group)

        # Step 4: 計算 Fisher Score
        between_class_distance = abs(mean_similar - mean_dissimilar)
        within_class_variance = (var_similar + var_dissimilar) / 2

        if within_class_variance > 1e-6:  # 避免除以 0
            fisher_score = (between_class_distance ** 2) / within_class_variance
        else:
            # 如果方差接近 0（組內幾乎沒變化），給一個很高的分數
            fisher_score = (between_class_distance ** 2) / 0.001

        # 保存結果
        results[dim] = {
            'mean_similar': mean_similar,
            'mean_dissimilar': mean_dissimilar,
            'between_distance': between_class_distance,
            'within_variance': within_class_variance,
            'fisher_score': fisher_score,
            'n_similar': len(similar_group),
            'n_dissimilar': len(dissimilar_group)
        }

        # 顯示結果
        print(f"\n【相似組】（{len(similar_group)} 對）")
        print(f"  平均相似度：{mean_similar:.3f}")
        print(f"  變異數：{var_similar:.3f}")
        print(f"  分布範例：{similar_group[:5]}")

        print(f"\n【不相似組】（{len(dissimilar_group)} 對）")
        print(f"  平均相似度：{mean_dissimilar:.3f}")
        print(f"  變異數：{var_dissimilar:.3f}")
        print(f"  分布範例：{dissimilar_group[:5]}")

        print(f"\n【Fisher 判別力】")
        print(f"  類間距離 = |{mean_similar:.3f} - {mean_dissimilar:.3f}| = {between_class_distance:.3f}")
        print(f"  類內方差 = ({var_similar:.3f} + {var_dissimilar:.3f}) / 2 = {within_class_variance:.3f}")
        print(f"  Fisher Score = ({between_class_distance:.3f})² / {within_class_variance:.3f}")
        print(f"               = {fisher_score:.3f}")

        # 解讀
        if fisher_score > 10:
            interpretation = "🟢 極強判別力"
        elif fisher_score > 1:
            interpretation = "🟡 中等判別力"
        else:
            interpretation = "🔴 弱判別力"
        print(f"  → {interpretation}")
        print()

    return results


def normalize_weights(fisher_scores):
    """將 Fisher 分數正規化為權重"""
    total = sum(fisher_scores.values())
    if total == 0:
        return {k: 0.25 for k in fisher_scores.keys()}

    weights = {k: v / total for k, v in fisher_scores.items()}
    return weights


def main():
    print()
    print("="*80)
    print("🔬 Fisher 判別力分析 - 基於 50 筆真實 Query")
    print("="*80)
    print()

    # 讀取標註結果
    input_path = '../09_輸入輸出資料/案例相似度標註表_50query_AI標註.xlsx'
    print(f"📖 讀取標註表：{input_path}")
    df = pd.read_excel(input_path, sheet_name='AI標註結果')
    print(f"   ✅ 共 {len(df)} 對")
    print()

    # 篩選有效樣本（移除 3 分）
    df_valid = df[df['相似度(1-5)'] != 3].copy()
    print(f"📋 有效樣本（移除 3 分）：{len(df_valid)} 對")
    print(f"   相似組（4-5分）：{(df_valid['相似度(1-5)'] >= 4).sum()} 對")
    print(f"   不相似組（1-2分）：{(df_valid['相似度(1-5)'] <= 2).sum()} 對")
    print()

    # 計算 Fisher 判別力
    results = calculate_fisher_discriminant(df_valid)

    # 彙總結果
    print()
    print("="*80)
    print("📊 Fisher 判別力彙總")
    print("="*80)
    print()

    fisher_scores = {dim: results[dim]['fisher_score'] for dim in results}

    # 排序顯示
    sorted_dims = sorted(fisher_scores.items(), key=lambda x: x[1], reverse=True)

    print(f"{'維度':<15} {'Fisher Score':>15} {'判別力':>12}")
    print("-"*45)
    for dim, score in sorted_dims:
        if score > 10:
            strength = "🟢 極強"
        elif score > 1:
            strength = "🟡 中等"
        else:
            strength = "🔴 弱"
        print(f"{dim:<15} {score:>15.3f} {strength:>12}")

    # 計算權重
    print()
    print("="*80)
    print("⚖️  建議權重（基於 Fisher 判別力）")
    print("="*80)
    print()

    weights = normalize_weights(fisher_scores)

    print("正規化權重（Fisher Score / 總和）：")
    print()
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    for dim, weight in sorted_weights:
        print(f"  {dim:<15}: {weight:>6.1%}")

    # 與預設權重比較
    print()
    print("="*80)
    print("📈 與預設權重比較")
    print("="*80)
    print()

    # 預設權重
    default_weights = {
        'liability': 0.50,  # 責任類型
        'violation': 0.15,  # 違規
        'injury': 0.10,     # 傷害
        'items': 0.10       # 賠償（簡化，不包含法條）
    }

    print(f"{'維度':<15} {'預設權重':>12} {'Fisher權重':>12} {'差異':>10}")
    print("-"*52)
    for dim in ['liability', 'violation', 'injury', 'items']:
        diff = weights[dim] - default_weights[dim]
        print(f"{dim:<15} {default_weights[dim]:>11.1%} {weights[dim]:>11.1%} {diff:>+9.1%}")

    # 保存結果
    output_path = '../09_輸入輸出資料/Fisher判別力分析_Query版.xlsx'
    print()
    print("="*80)
    print(f"💾 保存分析結果：{output_path}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Fisher Score 詳細
        fisher_df = pd.DataFrame({
            '維度': list(results.keys()),
            '相似組平均': [results[d]['mean_similar'] for d in results],
            '不相似組平均': [results[d]['mean_dissimilar'] for d in results],
            '類間距離': [results[d]['between_distance'] for d in results],
            '類內方差': [results[d]['within_variance'] for d in results],
            'Fisher Score': [results[d]['fisher_score'] for d in results],
            'Fisher權重': [weights[d] for d in results],
            '預設權重': [default_weights.get(d, 0) for d in results],
            '差異': [weights[d] - default_weights.get(d, 0) for d in results]
        })
        fisher_df = fisher_df.sort_values('Fisher Score', ascending=False)
        fisher_df.to_excel(writer, sheet_name='Fisher分析', index=False)

        # Sheet 2: 結論
        conclusions = pd.DataFrame({
            '分析結論': [
                '=== Fisher 判別力分析結果（基於 50 Query）===',
                '',
                f'總樣本數：{len(df_valid)} 對（移除 3 分）',
                f'相似組：{(df_valid["相似度(1-5)"] >= 4).sum()} 對',
                f'不相似組：{(df_valid["相似度(1-5)"] <= 2).sum()} 對',
                '',
                '各維度 Fisher Score（由高至低）：',
                *[f'  {dim}: {fisher_scores[dim]:.3f}'
                  for dim, _ in sorted_dims],
                '',
                '建議權重（基於 Fisher 判別力）：',
                *[f'  {dim}: {weights[dim]:.1%}'
                  for dim, _ in sorted_weights],
                '',
                '關鍵發現：',
                f'  判別力最強：{sorted_dims[0][0]} (Fisher={sorted_dims[0][1]:.3f})',
                f'  判別力最弱：{sorted_dims[-1][0]} (Fisher={sorted_dims[-1][1]:.3f})',
                '',
                '說明：',
                '  • Fisher Score 越高 → 該維度越能有效區分相似/不相似案例',
                '  • 類間距離大、類內方差小 → 判別效果好',
                '  • Fisher 權重 = Fisher Score / 總和'
            ]
        })
        conclusions.to_excel(writer, sheet_name='分析結論', index=False)

    print("   ✅ 保存完成")
    print()
    print("="*80)
    print("🎉 分析完成！")
    print("="*80)
    print()
    print("📝 關鍵發現：")
    print(f"  • 判別力最強：{sorted_dims[0][0]} (Fisher Score = {sorted_dims[0][1]:.3f})")
    print(f"  • 判別力最弱：{sorted_dims[-1][0]} (Fisher Score = {sorted_dims[-1][1]:.3f})")
    print()
    print("💡 建議：")
    print("  根據 Fisher 判別力調整權重，可以提升系統檢索效果")
    print("  判別力強的維度應該獲得更高的權重")


if __name__ == "__main__":
    main()
