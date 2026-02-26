#!/usr/bin/env python3
"""
計算各層的 Fisher 判別力
基於 120 筆有效標註樣本（移除 3 分）
"""
import pandas as pd
import numpy as np
import os
import re


def parse_summary(summary):
    """解析摘要，提取各維度信息"""
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
        info['amount'] = int(amount_match.group(1)) * 10000  # 轉換為元

    return info


def calculate_dimension_similarity(info_a, info_b, dimension):
    """計算單一維度的相似度（0-1）"""

    if dimension == 'liability':
        # 責任類型：完全匹配或不匹配
        if info_a['liability'] == info_b['liability']:
            return 1.0
        else:
            return 0.0

    elif dimension == 'violation':
        # 違規行為：完全匹配、類似、不同
        if info_a['violation'] == info_b['violation']:
            return 1.0
        elif info_a['violation'] and info_b['violation']:
            # 部分違規有相似性
            similar_violations = [
                {'疏未注意', '違規', '貿然駛出'},
                {'闖紅燈', '違規左轉'},
            ]
            for group in similar_violations:
                if info_a['violation'] in group and info_b['violation'] in group:
                    return 0.6  # 類似但不完全相同
            return 0.0
        else:
            return 0.0

    elif dimension == 'injury':
        # 傷害結果：完全匹配、嚴重程度相近、不同
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
            if level_diff == 0:
                return 1.0
            elif level_diff == 1:
                return 0.6  # 相近
            elif level_diff == 2:
                return 0.3  # 有距離
            else:
                return 0.0  # 差異大
        else:
            return 0.0

    elif dimension == 'amount':
        # 金額：用對數尺度
        if not info_a['amount'] or not info_b['amount']:
            return 0.5  # 未知，給中性分

        amount_a = max(info_a['amount'], 10000)
        amount_b = max(info_b['amount'], 10000)

        import math
        log_diff = abs(math.log10(amount_b) - math.log10(amount_a))
        similarity = max(0.0, 1.0 - log_diff / 1.5)

        return similarity

    else:
        return 0.0


def calculate_fisher_discriminant(df_valid):
    """
    計算各維度的 Fisher 判別力

    Fisher 判別力 = (類間距離)² / (類內方差)
    - 類間距離：相似組和不相似組的均值差異
    - 類內方差：兩組內部的變異程度
    """

    dimensions = ['liability', 'violation', 'injury', 'amount']
    results = {}

    for dim in dimensions:
        print(f"\n{'='*60}")
        print(f"計算維度：{dim}")
        print('='*60)

        # 計算每對案例在該維度的相似度
        similarities = []
        labels = []  # 1 = 相似, 0 = 不相似

        for _, row in df_valid.iterrows():
            info_a = parse_summary(row['案例A摘要'])
            info_b = parse_summary(row['案例B摘要'])

            sim = calculate_dimension_similarity(info_a, info_b, dim)
            similarities.append(sim)

            # 標籤：4-5分為相似，1-2分為不相似
            label = 1 if row['相似度(1-5)'] >= 4 else 0
            labels.append(label)

        similarities = np.array(similarities)
        labels = np.array(labels)

        # 分成兩組
        similar_group = similarities[labels == 1]
        dissimilar_group = similarities[labels == 0]

        # 計算統計量
        mean_similar = np.mean(similar_group)
        mean_dissimilar = np.mean(dissimilar_group)
        var_similar = np.var(similar_group)
        var_dissimilar = np.var(dissimilar_group)

        # Fisher 判別力
        between_class_distance = abs(mean_similar - mean_dissimilar)
        within_class_variance = (var_similar + var_dissimilar) / 2

        if within_class_variance > 0:
            fisher_score = (between_class_distance ** 2) / within_class_variance
        else:
            fisher_score = 0.0

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
        print(f"\n相似組（4-5分）：")
        print(f"  樣本數：{len(similar_group)}")
        print(f"  平均相似度：{mean_similar:.3f}")
        print(f"  變異數：{var_similar:.3f}")

        print(f"\n不相似組（1-2分）：")
        print(f"  樣本數：{len(dissimilar_group)}")
        print(f"  平均相似度：{mean_dissimilar:.3f}")
        print(f"  變異數：{var_dissimilar:.3f}")

        print(f"\nFisher 判別力：")
        print(f"  類間距離：{between_class_distance:.3f}")
        print(f"  類內方差：{within_class_variance:.3f}")
        print(f"  Fisher Score = (類間距離)² / 類內方差")
        print(f"              = ({between_class_distance:.3f})² / {within_class_variance:.3f}")
        print(f"              = {fisher_score:.3f}")

    return results


def normalize_weights(fisher_scores):
    """將 Fisher 分數正規化為權重"""
    total = sum(fisher_scores.values())
    if total == 0:
        return {k: 0.25 for k in fisher_scores.keys()}  # 均分

    weights = {k: v / total for k, v in fisher_scores.items()}
    return weights


def main():
    print("="*80)
    print("📊 Fisher 判別力分析")
    print("="*80)
    print()

    # 讀取標註結果
    input_path = '../09_輸入輸出資料/案例相似度標註表_150對_簡化版標註.xlsx'
    print(f"📖 讀取標註表：{input_path}")
    df = pd.read_excel(input_path, sheet_name='AI標註結果')
    print(f"   ✅ 共 {len(df)} 對案例")

    # 篩選有效樣本（移除 3 分）
    df_valid = df[df['相似度(1-5)'] != 3].copy()
    print(f"\n📋 有效樣本（移除 3 分）：{len(df_valid)} 對")
    print(f"   相似組（4-5分）：{(df_valid['相似度(1-5)'] >= 4).sum()} 對")
    print(f"   不相似組（1-2分）：{(df_valid['相似度(1-5)'] <= 2).sum()} 對")

    # 計算 Fisher 判別力
    results = calculate_fisher_discriminant(df_valid)

    # 彙總結果
    print("\n" + "="*80)
    print("📊 Fisher 判別力彙總")
    print("="*80)
    print()

    fisher_scores = {dim: results[dim]['fisher_score'] for dim in results}

    print("各維度 Fisher Score：")
    for dim, score in sorted(fisher_scores.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dim:15s}: {score:8.3f}")

    # 計算權重
    print("\n" + "="*80)
    print("⚖️  建議權重（基於 Fisher 判別力）")
    print("="*80)
    print()

    weights = normalize_weights(fisher_scores)

    print("正規化權重：")
    for dim, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dim:15s}: {weight:6.1%}")

    # 與預設權重比較
    print("\n" + "="*80)
    print("📈 與預設權重比較")
    print("="*80)
    print()

    # 預設權重（從維度設計文件）
    # 責任基礎 50% = liability 40% + party_structure 10%
    # 違規 15%, 傷害 10%, 法條 15%, 賠償 10%
    default_weights = {
        'liability': 0.40,
        'violation': 0.15,
        'injury': 0.10,
        'amount': 0.10
    }

    print(f"{'維度':<15} {'預設權重':>10} {'Fisher權重':>12} {'差異':>10}")
    print("-" * 50)
    for dim in ['liability', 'violation', 'injury', 'amount']:
        diff = weights[dim] - default_weights[dim]
        print(f"{dim:<15} {default_weights[dim]:>9.1%} {weights[dim]:>11.1%} {diff:>+9.1%}")

    # 保存結果
    output_path = '../09_輸入輸出資料/Fisher判別力分析結果.xlsx'
    print(f"\n💾 保存分析結果：{output_path}")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Fisher Score 詳細
        fisher_df = pd.DataFrame({
            '維度': list(results.keys()),
            '相似組平均': [results[d]['mean_similar'] for d in results],
            '不相似組平均': [results[d]['mean_dissimilar'] for d in results],
            '類間距離': [results[d]['between_distance'] for d in results],
            '類內方差': [results[d]['within_variance'] for d in results],
            'Fisher Score': [results[d]['fisher_score'] for d in results],
            '正規化權重': [weights[d] for d in results],
            '預設權重': [default_weights.get(d, 0) for d in results],
            '差異': [weights[d] - default_weights.get(d, 0) for d in results]
        })
        fisher_df = fisher_df.sort_values('Fisher Score', ascending=False)
        fisher_df.to_excel(writer, sheet_name='Fisher分析', index=False)

        # Sheet 2: 建議
        recommendations = pd.DataFrame({
            '分析結論': [
                '=== Fisher 判別力分析結果 ===',
                '',
                f'總樣本數：{len(df_valid)} 對',
                f'相似組：{(df_valid["相似度(1-5)"] >= 4).sum()} 對',
                f'不相似組：{(df_valid["相似度(1-5)"] <= 2).sum()} 對',
                '',
                '各維度 Fisher Score（由高至低）：',
                *[f'  {dim}: {fisher_scores[dim]:.3f}'
                  for dim in sorted(fisher_scores, key=fisher_scores.get, reverse=True)],
                '',
                '建議權重（基於 Fisher 判別力）：',
                *[f'  {dim}: {weights[dim]:.1%}'
                  for dim in sorted(weights, key=weights.get, reverse=True)],
                '',
                '結論：',
                f'  判別力最強：{max(fisher_scores, key=fisher_scores.get)}',
                f'  判別力最弱：{min(fisher_scores, key=fisher_scores.get)}',
                '',
                '註：Fisher Score 越高，代表該維度越能有效區分相似與不相似案例'
            ]
        })
        recommendations.to_excel(writer, sheet_name='分析結論', index=False)

    print("   ✅ 保存完成")
    print()
    print("="*80)
    print("🎉 分析完成！")
    print("="*80)
    print()
    print("📝 解讀說明：")
    print("  • Fisher Score 越高 → 該維度判別力越強")
    print("  • 類間距離大、類內方差小 → 判別效果好")
    print("  • 可以根據 Fisher 權重調整最終相似度公式")


if __name__ == "__main__":
    main()
