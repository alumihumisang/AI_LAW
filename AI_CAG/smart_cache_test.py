#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能KV-Cache測試 - 只載入最相關的案例
"""

import os
import pandas as pd
import random
from indictment_cag import load_model, prepare_indictment_kv_cache, generate_indictment_from_facts

def smart_case_selection(all_documents, target_size=100):
    """智能選擇最具代表性的案例"""
    
    # 策略1: 按長度分層採樣
    short_docs = [d for d in all_documents if len(d) < 800]
    medium_docs = [d for d in all_documents if 800 <= len(d) < 1500]
    long_docs = [d for d in all_documents if len(d) >= 1500]
    
    print(f"文檔分布: 短({len(short_docs)}) 中({len(medium_docs)}) 長({len(long_docs)})")
    
    # 按比例採樣
    selected = []
    selected.extend(random.sample(short_docs, min(target_size//4, len(short_docs))))
    selected.extend(random.sample(medium_docs, min(target_size//2, len(medium_docs))))
    selected.extend(random.sample(long_docs, min(target_size//4, len(long_docs))))
    
    # 如果還需要更多，隨機補充
    remaining = target_size - len(selected)
    if remaining > 0:
        remaining_docs = [d for d in all_documents if d not in selected]
        selected.extend(random.sample(remaining_docs, min(remaining, len(remaining_docs))))
    
    return selected[:target_size]

def test_smart_cache():
    """測試智能KV-Cache"""
    print("=== 智能KV-Cache測試 ===\n")
    
    # 載入模型
    try:
        load_model("gemma3:27b", use_ollama=True)
        print("✅ 模型載入成功")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return

    # 載入所有案例
    excel_path = "整合_起訴書_2995_CAG用.xlsx"
    main_df = pd.read_excel(excel_path, sheet_name='事實編輯')
    
    all_documents = []
    for i in range(len(main_df)):
        doc = str(main_df.iloc[i, 1]) if pd.notna(main_df.iloc[i, 1]) else ""
        if doc.strip() and doc != "nan" and len(doc) > 200:
            all_documents.append(doc)
    
    print(f"載入 {len(all_documents)} 個有效案例")
    
    # 測試不同的案例子集大小
    test_sizes = [50, 100, 200]
    
    for size in test_sizes:
        print(f"\n📊 測試 {size} 個案例的效果:")
        print("-" * 50)
        
        # 智能選擇案例
        selected_docs = smart_case_selection(all_documents, size)
        
        # 計算KV-Cache大小
        total_chars = sum(len(doc) for doc in selected_docs)
        print(f"KV-Cache大小: {total_chars:,} 字符 (~{total_chars//4:,} tokens)")
        
        # 建立KV-Cache
        try:
            kv_cache = prepare_indictment_kv_cache(selected_docs, model_name="gemma3:27b")
            print("✅ KV-Cache建立成功")
        except Exception as e:
            print(f"❌ KV-Cache建立失敗: {e}")
            continue
        
        # 測試案例匹配能力
        test_facts = """一、事故發生緣由：
被告於民國105年4月12日追撞原告，造成原告左膝受傷。

二、請求賠償：
1. 醫療費用190元
2. 車輛修復費用181,144元  
3. 精神慰撫金99,000元"""

        try:
            from indictment_cag import find_similar_cases, extract_key_facts
            
            # 測試案例匹配
            extracted_facts = extract_key_facts(test_facts, "gemma3:27b")
            similar_cases = find_similar_cases(test_facts, extracted_facts, kv_cache, "gemma3:27b")
            
            # 檢查是否找到具體案例
            if "案例編號" in similar_cases and any(char.isdigit() for char in similar_cases):
                print("✅ 成功找到具體案例編號")
            else:
                print("❌ 未找到具體案例編號")
            
            # 顯示匹配結果前200字符
            print(f"匹配結果: {similar_cases[:200]}...")
            
        except Exception as e:
            print(f"❌ 案例匹配測試失敗: {e}")

if __name__ == "__main__":
    random.seed(42)  # 確保結果可重現
    test_smart_cache()