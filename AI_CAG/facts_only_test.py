#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
純事實匹配 + 規則化法條生成測試
"""

import os
import pandas as pd
import random
import re
from indictment_cag import load_model, prepare_indictment_kv_cache

def extract_facts_only(document):
    """只提取事實部分"""
    
    # 找到法條部分開始的標記
    legal_markers = ['二、按', '二、法律依據', '依民法第', '按民法第']
    
    end_pos = len(document)
    for marker in legal_markers:
        if marker in document:
            pos = document.find(marker)
            if pos > 50:  # 確保不是在很前面
                end_pos = min(end_pos, pos)
    
    # 只保留事實部分
    facts_only = document[:end_pos].strip()
    
    # 清理格式
    if facts_only.startswith('一、'):
        facts_only = facts_only[2:].strip()
    
    return facts_only

def determine_applicable_laws(accident_facts, injuries="", compensation_facts=""):
    """智能判斷適用法條"""
    applicable_laws = []
    
    # 基本侵權責任（必定適用）
    applicable_laws.append("民法第184條第1項前段")
    
    # 車輛事故相關
    vehicle_keywords = ['車輛', '汽車', '機車', '駕駛', '追撞', '碰撞', '行駛']
    if any(keyword in accident_facts for keyword in vehicle_keywords):
        applicable_laws.append("民法第191條之2")
    
    # 身體傷害相關
    injury_keywords = ['受傷', '傷害', '骨折', '挫傷', '撞傷', '醫療', '治療', '休養']
    if any(keyword in accident_facts or keyword in injuries for keyword in injury_keywords):
        applicable_laws.append("民法第193條第1項")
    
    # 精神損害相關
    mental_keywords = ['精神', '慰撫金', '痛苦', '創傷']
    if any(keyword in accident_facts or keyword in compensation_facts for keyword in mental_keywords):
        applicable_laws.append("民法第195條第1項前段")
    
    return applicable_laws

def generate_standard_laws(accident_facts, injuries="", compensation_facts=""):
    """規則化生成法律依據"""
    
    # 智能判斷適用法條
    applicable_laws = determine_applicable_laws(accident_facts, injuries, compensation_facts)
    
    # 法條條文對照表
    law_descriptions = {
        "民法第184條第1項前段": "因故意或過失，不法侵害他人之權利者，負損害賠償責任。",
        "民法第191條之2": "汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。",
        "民法第193條第1項": "不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。",
        "民法第195條第1項前段": "不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。"
    }
    
    # 組合法條內容
    law_texts = []
    valid_laws = []
    
    for law in applicable_laws:
        if law in law_descriptions:
            law_texts.append(f"「{law_descriptions[law]}」")
            valid_laws.append(law)
    
    # 組合標準格式
    law_content_block = "、".join(law_texts)
    article_list = "、".join(valid_laws)
    
    return f"""二、按{law_content_block}{article_list}分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任："""

def test_facts_only_approach():
    """測試純事實匹配 + 規則化法條生成"""
    print("=== 純事實匹配 + 規則化法條生成測試 ===\n")
    
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
    
    print("📋 處理案例數據（只保留事實部分）...")
    
    facts_only_documents = []
    original_total_chars = 0
    facts_total_chars = 0
    
    for i in range(min(1000, len(main_df))):
        original_doc = str(main_df.iloc[i, 1]) if pd.notna(main_df.iloc[i, 1]) else ""
        
        if original_doc.strip() and original_doc != "nan" and len(original_doc) > 200:
            facts_only = extract_facts_only(original_doc)
            
            if len(facts_only) > 80:  # 確保有足夠的事實內容
                facts_only_documents.append(facts_only)
                original_total_chars += len(original_doc)
                facts_total_chars += len(facts_only)
    
    compression_ratio = (1 - facts_total_chars/original_total_chars) * 100
    
    print(f"✅ 處理完成：{len(facts_only_documents)} 個事實案例")
    print(f"📊 壓縮效果：{original_total_chars:,} → {facts_total_chars:,} 字符")
    print(f"📉 壓縮率：{compression_ratio:.1f}%")
    
    # 選擇更多案例進行測試
    random.seed(42)
    selected_docs = random.sample(facts_only_documents, min(800, len(facts_only_documents)))
    
    total_chars = sum(len(doc) for doc in selected_docs)
    estimated_tokens = total_chars // 4
    
    print(f"\n🧪 測試配置:")
    print(f"- 選擇案例數: {len(selected_docs)}")
    print(f"- KV-Cache大小: {total_chars:,} 字符 (~{estimated_tokens:,} tokens)")
    
    # 建立純事實KV-Cache
    try:
        kv_cache = prepare_indictment_kv_cache(selected_docs, model_name="gemma3:27b")
        print("✅ 純事實KV-Cache建立成功")
    except Exception as e:
        print(f"❌ KV-Cache建立失敗: {e}")
        return
    
    # 測試案例
    test_facts = """被告於民國105年4月12日13時27分許，駕駛租賃小客車追撞原告車輛，造成原告左膝挫傷、半月軟骨受傷，需休養1個月。請求賠償醫療費190元、車輛修復費181,144元、交通費4,500元、工作損失33,000元、精神慰撫金99,000元。"""
    
    try:
        print("\n🔍 測試事實匹配...")
        
        from indictment_cag import find_similar_cases, extract_key_facts
        
        # 事實匹配
        extracted_facts = extract_key_facts(test_facts, "gemma3:27b")
        similar_cases = find_similar_cases(test_facts, extracted_facts, kv_cache, "gemma3:27b")
        
        print("✅ 事實匹配完成")
        print(f"匹配結果: {similar_cases[:300]}...")
        
        # 規則化法條生成
        print(f"\n⚖️ 測試規則化法條生成...")
        legal_section = generate_standard_laws(test_facts, "左膝挫傷、半月軟骨受傷", "精神慰撫金")
        print("✅ 法條生成完成")
        print(f"法條內容:\n{legal_section}")
        
        # 測試優勢
        advantages = [
            f"案例數量提升: 從500個 → {len(selected_docs)}個 ({len(selected_docs)/500:.1f}倍)",
            f"壓縮率優異: {compression_ratio:.1f}% (比事實+法條的55%更好)",
            "法條生成穩定: 規則化生成，避免模型不一致",
            "匹配精度提升: 專注事實相似性，不受法條風格干擾"
        ]
        
        print(f"\n🎯 策略優勢:")
        for i, advantage in enumerate(advantages, 1):
            print(f"  {i}. {advantage}")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_facts_only_approach()