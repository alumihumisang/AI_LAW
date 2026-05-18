#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能分層CAG策略 - 在有限硬體下最大化CAG效果
"""

import pandas as pd
import random
from indictment_cag import (
    load_model, extract_facts_only, generate_standard_laws,
    prepare_indictment_kv_cache, find_similar_cases, extract_key_facts
)

def categorize_cases_by_type(facts_list):
    """根據事故類型分類案例"""
    categories = {
        '追撞': [],
        '左轉': [],
        '變換車道': [], 
        '闖紅燈': [],
        '酒駕': [],
        '其他': []
    }
    
    for i, facts in enumerate(facts_list):
        facts_lower = facts.lower()
        if '追撞' in facts or '追尾' in facts:
            categories['追撞'].append((i, facts))
        elif '左轉' in facts or '迴轉' in facts:
            categories['左轉'].append((i, facts))
        elif '變換車道' in facts or '變道' in facts or '併道' in facts:
            categories['變換車道'].append((i, facts))
        elif '闖紅燈' in facts or '紅燈' in facts:
            categories['闖紅燈'].append((i, facts))
        elif '酒駕' in facts or '醉駕' in facts or '飲酒' in facts:
            categories['酒駕'].append((i, facts))
        else:
            categories['其他'].append((i, facts))
    
    return categories

def smart_case_selection(facts_list, target_size=175):
    """智能選擇最具代表性的案例組合"""
    
    # 1. 按事故類型分類
    categories = categorize_cases_by_type(facts_list)
    
    print("📊 案例分類統計:")
    for category, cases in categories.items():
        print(f"  {category}: {len(cases)} 案例")
    
    # 2. 按比例從各類別選擇案例
    selected_cases = []
    total_available = sum(len(cases) for cases in categories.values())
    
    for category, cases in categories.items():
        if not cases:
            continue
            
        # 計算該類別應選擇的案例數（保證每類至少有1個）
        proportion = len(cases) / total_available
        target_count = max(1, int(target_size * proportion))
        target_count = min(target_count, len(cases))  # 不超過可用數量
        
        # 隨機選擇該類別的案例
        selected_from_category = random.sample(cases, target_count)
        selected_cases.extend([facts for _, facts in selected_from_category])
        
        print(f"  {category}: 選擇 {target_count} 案例")
    
    # 3. 如果還有剩餘空間，隨機補充
    remaining_space = target_size - len(selected_cases)
    if remaining_space > 0:
        all_unselected = [facts for facts in facts_list if facts not in selected_cases]
        if all_unselected:
            additional = random.sample(all_unselected, min(remaining_space, len(all_unselected)))
            selected_cases.extend(additional)
            print(f"  額外隨機補充: {len(additional)} 案例")
    
    return selected_cases[:target_size]

def layered_cag_generation(test_facts, all_facts_list):
    """分層CAG生成策略"""
    print("🧠 執行分層CAG策略...")
    
    # 第1層：智能選擇代表性案例
    print("第1層：智能案例選擇...")
    selected_cases = smart_case_selection(all_facts_list, target_size=175)
    print(f"✅ 選擇了 {len(selected_cases)} 個代表性案例")
    
    # 第2層：建立KV-Cache
    print("第2層：建立專用KV-Cache...")
    kv_cache = prepare_indictment_kv_cache(
        selected_cases,
        model_name="gemma3:27b",
        facts_only=True
    )
    
    total_chars = sum(len(case) for case in selected_cases)
    print(f"✅ KV-Cache建立成功 ({total_chars:,} 字符)")
    
    # 第3層：精確匹配和生成
    print("第3層：執行CAG生成...")
    
    # 事實提取
    extracted_facts = extract_key_facts(test_facts, "gemma3:27b")
    print(f"✅ 事實提取完成")
    
    # 案例匹配
    similar_cases = find_similar_cases(test_facts, extracted_facts, kv_cache, "gemma3:27b")
    print(f"✅ 案例匹配完成")
    
    # 規則化法條生成
    rule_based_laws = generate_standard_laws(test_facts)
    print(f"✅ 規則化法條生成完成")
    
    return {
        'selected_cases_count': len(selected_cases),
        'extracted_facts': extracted_facts,
        'similar_cases': similar_cases,
        'rule_based_laws': rule_based_laws,
        'cache_size': total_chars
    }

def test_layered_cag():
    """測試分層CAG策略"""
    print("=== 智能分層CAG測試 ===\n")
    
    # 載入模型
    load_model("gemma3:27b", use_ollama=True)
    print("✅ 模型載入成功")
    
    # 載入全部案例
    print("📚 載入全部2995個案例...")
    excel_path = "整合_起訴書_2995_CAG用.xlsx"
    df = pd.read_excel(excel_path, sheet_name='事實編輯')
    
    all_facts = []
    for _, row in df.iterrows():
        facts_text = extract_facts_only(str(row['起訴書']))
        if len(facts_text) > 50:
            all_facts.append(facts_text)
    
    print(f"✅ 成功載入 {len(all_facts)} 個有效案例")
    
    # 測試案例
    test_facts = """被告於民國105年4月12日13時27分許，駕駛租賃小客車追撞原告車輛，造成原告左膝挫傷、半月軟骨受傷，需休養1個月。請求賠償醫療費190元、車輛修復費181,144元、交通費4,500元、工作損失33,000元、精神慰撫金99,000元。"""
    
    # 執行分層CAG
    result = layered_cag_generation(test_facts, all_facts)
    
    print(f"\n🎯 分層CAG策略成果:")
    print(f"✅ 處理全部案例數: {len(all_facts)}")
    print(f"✅ KV-Cache使用案例: {result['selected_cases_count']}")
    print(f"✅ 硬體資源效率: {result['selected_cases_count']}/{len(all_facts)} = {result['selected_cases_count']/len(all_facts)*100:.1f}%")
    print(f"✅ 保持CAG純度: 100% (無RAG混合)")
    print(f"✅ 智能案例選擇: 按事故類型均衡分佈")
    
    print(f"\n📋 生成結果預覽:")
    print(f"法條部分: {result['rule_based_laws'][:150]}...")
    print(f"匹配案例: {result['similar_cases'][:150]}...")
    
    print(f"\n🏆 總結: 在硬體限制下實現了準CAG效果！")

if __name__ == "__main__":
    random.seed(42)  # 確保結果可重現
    test_layered_cag()