#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
優化KV-Cache測試 - 只保留事實和法條部分
"""

import os
import pandas as pd
import random
from indictment_cag import load_model, prepare_indictment_kv_cache, generate_indictment_from_facts

def extract_facts_legal_only(document):
    """只提取事實和法條部分，去除賠償和結論"""
    
    # 找到賠償部分開始的標記
    compensation_markers = ['(一)', '（一）', '茲依原告所受損害', '查被告因上開侵權行為，致原告受有下列損害']
    
    end_pos = len(document)
    for marker in compensation_markers:
        if marker in document:
            pos = document.find(marker)
            if pos > 100:  # 確保不是在很前面的位置
                end_pos = min(end_pos, pos)
    
    # 提取事實和法條部分
    facts_legal = document[:end_pos].strip()
    
    # 確保以法條引用結束
    if '分別定有明文' in facts_legal:
        end_legal = facts_legal.rfind('分別定有明文') + len('分別定有明文')
        facts_legal = facts_legal[:end_legal] + '。'
    
    return facts_legal

def test_optimized_cache():
    """測試優化的KV-Cache"""
    print("=== 優化KV-Cache測試（只保留事實+法條）===\n")
    
    # 載入模型
    try:
        load_model("gemma3:27b", use_ollama=True)
        print("✅ 模型載入成功")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return

    # 載入和處理案例
    excel_path = "整合_起訴書_2995_CAG用.xlsx"
    main_df = pd.read_excel(excel_path, sheet_name='事實編輯')
    
    print("📋 處理案例數據...")
    
    # 處理所有案例，只保留事實+法條
    processed_documents = []
    original_total_chars = 0
    processed_total_chars = 0
    
    for i in range(min(800, len(main_df))):  # 處理更多案例以測試效果
        original_doc = str(main_df.iloc[i, 1]) if pd.notna(main_df.iloc[i, 1]) else ""
        
        if original_doc.strip() and original_doc != "nan" and len(original_doc) > 200:
            # 提取事實+法條部分
            facts_legal = extract_facts_legal_only(original_doc)
            
            if len(facts_legal) > 100:  # 確保提取有效
                processed_documents.append(facts_legal)
                original_total_chars += len(original_doc)
                processed_total_chars += len(facts_legal)
    
    print(f"✅ 處理完成：{len(processed_documents)} 個有效案例")
    print(f"📊 壓縮效果：{original_total_chars:,} → {processed_total_chars:,} 字符")
    print(f"📉 壓縮率：{(1 - processed_total_chars/original_total_chars)*100:.1f}%")
    
    # 隨機選擇案例進行測試
    random.seed(42)
    selected_docs = random.sample(processed_documents, min(500, len(processed_documents)))
    
    total_chars = sum(len(doc) for doc in selected_docs)
    estimated_tokens = total_chars // 4
    
    print(f"\n🧪 測試配置:")
    print(f"- 選擇案例數: {len(selected_docs)}")
    print(f"- KV-Cache大小: {total_chars:,} 字符 (~{estimated_tokens:,} tokens)")
    
    # 建立KV-Cache
    try:
        kv_cache = prepare_indictment_kv_cache(selected_docs, model_name="gemma3:27b")
        print("✅ KV-Cache建立成功")
    except Exception as e:
        print(f"❌ KV-Cache建立失敗: {e}")
        return
    
    # 測試案例匹配
    test_facts = """一、事故發生緣由：
被告於民國105年4月12日13時27分許，駕駛租賃小客車追撞原告車輛，造成原告左膝挫傷、半月軟骨受傷。

二、請求賠償：
1. 醫療復健費用190元
2. 車輛修復費用181,144元
3. 交通費用4,500元  
4. 工作收入損失33,000元
5. 慰撫金99,000元"""

    try:
        print("\n🔍 測試案例匹配能力...")
        
        from indictment_cag import find_similar_cases, extract_key_facts
        
        extracted_facts = extract_key_facts(test_facts, "gemma3:27b")
        similar_cases = find_similar_cases(test_facts, extracted_facts, kv_cache, "gemma3:27b")
        
        # 分析匹配結果
        if "案例編號" in similar_cases and any(char.isdigit() for char in similar_cases):
            print("✅ 成功找到具體案例編號")
            
            # 檢查是否找到多個案例
            import re
            case_numbers = re.findall(r'案例編號[：:]\s*(\d+)', similar_cases)
            if len(case_numbers) >= 2:
                print(f"✅ 找到多個案例: {case_numbers}")
            else:
                print(f"ℹ️ 找到案例數量: {len(case_numbers)}")
        else:
            print("❌ 未找到具體案例編號")
        
        print(f"\n📋 匹配結果預覽:")
        print("-" * 50)
        print(similar_cases[:400] + ("..." if len(similar_cases) > 400 else ""))
        print("-" * 50)
        
        # 測試完整生成
        print(f"\n🏗️ 測試完整起訴書生成...")
        
        result = generate_indictment_from_facts(
            accident_facts=test_facts,
            kv_cache=kv_cache,
            model_name="gemma3:27b"
        )
        
        # 檢查生成品質
        full_text = result.get("full_indictment", "")
        
        quality_checks = [
            ("包含一、二、格式", "一、" in full_text and "二、" in full_text),
            ("包含括號賠償格式", "（一）" in full_text and "（二）" in full_text),
            ("包含綜上所陳", "綜上所陳" in full_text),
            ("保留金額", "190元" in full_text and "181,144元" in full_text)
        ]
        
        print(f"📊 生成品質檢查:")
        for check_name, passed in quality_checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
        
        print(f"\n📄 生成內容長度: {len(full_text)} 字符")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_optimized_cache()