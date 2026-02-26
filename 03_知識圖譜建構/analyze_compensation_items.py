#!/usr/bin/env python3
"""
分析所有案例的賠償項目類型
提取常見的賠償項目並統計分布
"""
import pandas as pd
import re
from collections import Counter


def extract_compensation_items(text):
    """
    從損害賠償項目文字中提取項目類型
    返回項目集合（set）
    """
    if not text or pd.isna(text):
        return set()

    text = str(text)
    items = set()

    # 定義常見賠償項目及其關鍵字
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
                break  # 找到一個關鍵字就加入，不重複

    return items


def main():
    print("="*80)
    print("📊 分析賠償項目分布")
    print("="*80)
    print()

    # 讀取資料
    df = pd.read_excel('../09_輸入輸出資料/整合_起訴書_四段(FINAL)_6057.xlsx')
    print(f"📖 讀取 {len(df)} 筆案例")
    print()

    # 提取所有賠償項目
    print("🔍 提取賠償項目...")
    all_items = []
    case_items = {}  # 記錄每個案例的項目

    for i, row in df.iterrows():
        items = extract_compensation_items(row['損害賠償項目'])
        case_items[row['case_id']] = items
        all_items.extend(items)

        if (i + 1) % 1000 == 0:
            print(f"   進度：{i+1}/{len(df)}")

    # 統計分布
    item_counter = Counter(all_items)

    print()
    print("="*80)
    print("📊 賠償項目分布統計")
    print("="*80)
    print()
    print(f"{'項目類型':<15} {'案例數':>10} {'百分比':>10}")
    print("-"*40)

    for item, count in item_counter.most_common():
        percentage = count / len(df) * 100
        print(f"{item:<15} {count:>10} {percentage:>9.1f}%")

    print()
    print(f"總共識別出 {len(item_counter)} 種賠償項目類型")

    # 分析項目組合
    print()
    print("="*80)
    print("📊 常見項目組合（前 20 名）")
    print("="*80)
    print()

    combo_counter = Counter()
    for case_id, items in case_items.items():
        if len(items) > 0:
            # 將項目集合轉為 frozenset 以便計數
            combo_counter[frozenset(items)] += 1

    print(f"{'項目組合':<60} {'案例數':>10}")
    print("-"*72)

    for combo, count in combo_counter.most_common(20):
        combo_str = '、'.join(sorted(combo))
        print(f"{combo_str:<60} {count:>10}")

    # 項目數量分布
    print()
    print("="*80)
    print("📊 每案例平均項目數")
    print("="*80)
    print()

    item_counts = [len(items) for items in case_items.values()]
    count_dist = Counter(item_counts)

    print(f"{'項目數':>10} {'案例數':>10} {'百分比':>10}")
    print("-"*35)

    for num, count in sorted(count_dist.items()):
        percentage = count / len(df) * 100
        print(f"{num:>10} {count:>10} {percentage:>9.1f}%")

    avg_items = sum(item_counts) / len(item_counts)
    print()
    print(f"平均每案例有 {avg_items:.2f} 種賠償項目")

    # 儲存結果
    print()
    print("="*80)
    print("💾 儲存案例項目資料...")

    # 建立 DataFrame
    items_df = pd.DataFrame({
        'case_id': list(case_items.keys()),
        'compensation_items': [','.join(sorted(items)) if items else '' for items in case_items.values()],
        'item_count': [len(items) for items in case_items.values()]
    })

    output_path = '../09_輸入輸出資料/案例賠償項目統計.xlsx'
    items_df.to_excel(output_path, index=False)

    print(f"✅ 已儲存至：{output_path}")
    print()

    # 顯示範例
    print("="*80)
    print("📝 案例範例（隨機 10 筆）")
    print("="*80)

    for case_id in items_df.sample(10)['case_id']:
        items = case_items[case_id]
        print(f"\n案例 {case_id}：{', '.join(sorted(items)) if items else '（無）'}")


if __name__ == "__main__":
    main()
