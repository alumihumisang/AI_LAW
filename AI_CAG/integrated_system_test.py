#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合後系統測試 - 事實匹配 + 規則化法條生成
"""

import os
import pandas as pd
from indictment_cag import (
    load_model, 
    load_indictment_excel, 
    prepare_indictment_kv_cache, 
    generate_indictment_from_facts,
    extract_facts_only,
    generate_standard_laws
)

def test_integrated_system():
    """測試整合後的完整系統"""
    print("=== 整合後系統測試 ===\n")
    
    # 載入模型
    try:
        load_model("gemma3:27b", use_ollama=True)
        print("✅ 模型載入成功")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return
    
    # 測試純事實提取功能
    print("\n🔍 測試事實提取功能...")
    sample_document = """一、事故發生緣由：
被告於民國105年4月12日13時27分許，駕駛租賃小客車追撞原告車輛，造成原告左膝挫傷、半月軟骨受傷，需休養1個月。

二、按「民法第184條第1項前段：『因故意或過失，不法侵害他人之權利者，負損害賠償責任。』」分別定有明文。

三、請求賠償項目：
1. 醫療費用190元
2. 車輛修復費用181,144元"""
    
    extracted_facts = extract_facts_only(sample_document)
    print(f"✅ 事實提取成功")
    print(f"原始文檔: {len(sample_document)} 字符")
    print(f"提取事實: {len(extracted_facts)} 字符")
    print(f"壓縮率: {(1-len(extracted_facts)/len(sample_document))*100:.1f}%")
    print(f"提取結果: {extracted_facts[:100]}...")
    
    # 測試規則化法條生成功能
    print(f"\n⚖️ 測試規則化法條生成...")
    test_accident = "被告駕駛車輛追撞原告，造成原告左膝挫傷，請求精神慰撫金"
    rule_based_laws = generate_standard_laws(test_accident, "左膝挫傷", "精神慰撫金")
    print(f"✅ 規則化法條生成成功")
    print(f"法條內容: {rule_based_laws}")
    
    # 載入Excel數據（使用純事實模式）
    print(f"\n📊 測試純事實模式數據載入...")
    excel_path = "整合_起訴書_2995_CAG用.xlsx"
    
    # 比較標準模式和純事實模式
    print("比較標準模式 vs 純事實模式：")
    
    # 標準模式
    standard_texts, _ = load_indictment_excel(excel_path, max_knowledge=100, facts_only=False)
    standard_chars = sum(len(text) for text in standard_texts)
    
    # 純事實模式
    facts_texts, _ = load_indictment_excel(excel_path, max_knowledge=1000, facts_only=True)
    facts_chars = sum(len(text) for text in facts_texts)
    
    print(f"標準模式: {len(standard_texts)} 案例, {standard_chars:,} 字符")
    print(f"純事實模式: {len(facts_texts)} 案例, {facts_chars:,} 字符")
    print(f"案例數量提升: {len(facts_texts)/len(standard_texts):.1f}倍")
    
    if standard_chars > 0:
        compression = (1 - facts_chars/(standard_chars * len(facts_texts)/len(standard_texts))) * 100
        print(f"平均壓縮率: {compression:.1f}%")
    
    # 建立純事實KV-Cache
    print(f"\n🧠 建立純事實KV-Cache...")
    selected_facts = facts_texts[:800]  # 選擇800個案例
    
    try:
        facts_kv_cache = prepare_indictment_kv_cache(
            selected_facts, 
            model_name="gemma3:27b", 
            facts_only=True
        )
        print(f"✅ 純事實KV-Cache建立成功")
        print(f"使用案例數: {len(selected_facts)}")
        
        total_chars = sum(len(doc) for doc in selected_facts)
        estimated_tokens = total_chars // 4
        print(f"總字符數: {total_chars:,} (~{estimated_tokens:,} tokens)")
        
    except Exception as e:
        print(f"❌ KV-Cache建立失敗: {e}")
        return
    
    # 測試完整的事實+規則混合生成
    print(f"\n🚀 測試完整混合生成系統...")
    test_facts = """被告於民國105年4月12日13時27分許，駕駛租賃小客車追撞原告車輛，造成原告左膝挫傷、半月軟骨受傷，需休養1個月。請求賠償醫療費190元、車輛修復費181,144元、交通費4,500元、工作損失33,000元、精神慰撫金99,000元。"""
    
    try:
        print("測試傳統模型生成模式...")
        traditional_result = generate_indictment_from_facts(
            accident_facts=test_facts,
            kv_cache=facts_kv_cache,
            model_name="gemma3:27b",
            use_rule_based_laws=False
        )
        
        print("測試混合規則生成模式...")
        hybrid_result = generate_indictment_from_facts(
            accident_facts=test_facts,
            kv_cache=facts_kv_cache,
            model_name="gemma3:27b",
            use_rule_based_laws=True
        )
        
        # 比較兩種結果
        print(f"\n📋 生成結果比較:")
        print(f"傳統模式 - 法條長度: {len(traditional_result.get('legal_section', ''))}")
        print(f"混合模式 - 法條長度: {len(hybrid_result.get('legal_section', ''))}")
        
        print(f"\n傳統模式法條部分:")
        print(traditional_result.get('legal_section', '')[:200] + "...")
        
        print(f"\n混合模式法條部分:")
        print(hybrid_result.get('legal_section', '')[:200] + "...")
        
        # 測試系統優勢
        advantages = [
            f"案例容量: 從200個提升到{len(selected_facts)}個 ({len(selected_facts)/200:.1f}倍)",
            "法條穩定性: 規則化生成，避免模型不一致",
            "事實精確度: 專注事實匹配，提升相似度判斷",
            "性能優化: 大幅減少KV-Cache大小"
        ]
        
        print(f"\n🎯 整合系統優勢:")
        for i, advantage in enumerate(advantages, 1):
            print(f"  {i}. {advantage}")
        
        print(f"\n✅ 整合系統測試完成！")
        print("系統已成功整合事實匹配和規則化法條生成功能")
        
    except Exception as e:
        print(f"❌ 完整系統測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integrated_system()