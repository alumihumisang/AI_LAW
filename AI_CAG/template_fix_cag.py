#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
創建模板替換機制，直接填入正確的事實信息
"""

import re
from indictment_cag import (
    load_model, load_indictment_excel, prepare_indictment_kv_cache,
    extract_key_facts, generate_standard_laws
)
import ollama

def template_based_generation(accident_facts, kv_cache, model_name, use_rule_based_laws=True):
    """使用模板替換的起訴書生成"""
    
    # 第1階段：抽取事實
    extracted_facts = extract_key_facts(accident_facts, model_name)
    
    # 解析抽取的事實
    def extract_value(text, pattern):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else "未知"
    
    time_info = extract_value(extracted_facts, r'時間：([^\n]+)')
    location_info = extract_value(extracted_facts, r'地點：([^\n]+)')
    injury_info = extract_value(extracted_facts, r'傷害類型：([^\n]+)')
    
    # 從原始輸入中完整抽取事故發生緣由
    accident_origin_match = re.search(r'一、事故發生緣由[：:]?\s*(.*?)(?=二、|$)', accident_facts, re.DOTALL)
    if accident_origin_match:
        accident_origin = accident_origin_match.group(1).strip()
        # 確保以"緣"為開頭的完整敘述
        if not accident_origin.startswith('緣'):
            accident_origin = f"緣{accident_origin}"
    else:
        accident_origin = f"緣被告於{time_info}，駕駛小客車在{location_info}，因過失行為，與原告發生交通事故。"
    
    # 抽取原告受傷情形
    injury_details_match = re.search(r'二、原告受傷情形[：:]?\s*(.*?)(?=三、|$)', accident_facts, re.DOTALL)
    injury_details = injury_details_match.group(1).strip() if injury_details_match else ""
    
    medical_fee = extract_value(extracted_facts, r'醫療費用：([^\n]+)')
    repair_fee = extract_value(extracted_facts, r'車輛修復費：([^\n]+)')
    transport_fee = extract_value(extracted_facts, r'交通費：([^\n]+)')
    work_loss = extract_value(extracted_facts, r'工作損失：([^\n]+)')
    mental_damage = extract_value(extracted_facts, r'精神慰撫金：([^\n]+)')
    total_amount = extract_value(extracted_facts, r'總金額：([^\n]+)')
    
    # 檢查是否有預估醫療費用
    future_medical = extract_value(extracted_facts, r'預估醫療費用：([^\n]+)')
    if future_medical == "未知":
        # 嘗試從原始輸入中直接抽取
        future_medical_match = re.search(r'預估醫療費用[：:][^，。]*?(\d{1,3}(?:,\d{3})*|\d+)[元]', accident_facts)
        if future_medical_match:
            future_medical = future_medical_match.group(1) + "元"
    
    print(f"抽取的事實:")
    print(f"  時間: {time_info}")
    print(f"  地點: {location_info}")
    print(f"  傷害: {injury_info}")
    print(f"  事故緣由: {accident_origin[:50]}..." if len(accident_origin) > 50 else f"  事故緣由: {accident_origin}")
    print(f"  醫療費: {medical_fee}")
    print(f"  修復費: {repair_fee}")
    print(f"  交通費: {transport_fee}")
    print(f"  工作損失: {work_loss}")
    print(f"  精神慰撫金: {mental_damage}")
    if future_medical != "未知":
        print(f"  預估醫療費: {future_medical}")
    print(f"  總金額: {total_amount}")
    print()
    
    # 生成法條
    if use_rule_based_laws:
        legal_section = generate_standard_laws(accident_facts)
    else:
        legal_section = "二、按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」等相關法條定有明文。"
    
    # 智能描述生成引擎
    def generate_rich_description(category, amount, injury_details, accident_facts):
        """根據類別生成豐富描述"""
        if category == "醫療費用":
            # 提取醫院信息
            hospitals = re.findall(r'([^，。]*醫院[^，。]*|[^，。]*診所[^，。]*)', accident_facts)
            
            # 檢查是否有證明文件
            evidence = []
            if "診斷證明書" in accident_facts:
                evidence.append("診斷證明書")
            if "醫療費用收據" in accident_facts:
                evidence.append("醫療費用收據")
            if hospitals:
                evidence.append(f"{hospitals[0].strip()}開立之相關文件")
            
            evidence_text = "，有" + "、".join(evidence) + "為證" if evidence else ""
            
            if injury_details:
                injury_summary = injury_details.split('。')[0] if '。' in injury_details else injury_details[:60]
                return f"原告因本事故{injury_summary}，支出醫療費用新台幣{amount}{evidence_text}。"
            else:
                return f"原告因本事故受傷，支出醫療費用新台幣{amount}{evidence_text}。"
        
        elif category == "交通費":
            evidence = "，有停車費用收據為證" if "停車費" in accident_facts else ""
            return f"原告因就醫支出交通費用新台幣{amount}{evidence}。"
        
        elif category == "工作損失":
            evidence_parts = []
            if "診斷證明書" in accident_facts:
                evidence_parts.append("診斷證明書")
            if "薪資表" in accident_facts:
                evidence_parts.append("薪資表")
            
            # 提取休養時間
            rest_info = ""
            rest_match = re.search(r'休養[復健]*(\d+[至到]?\d*[週周月])', accident_facts)
            if rest_match:
                rest_info = f"原告需{rest_match.group(1)}休養復健，"
            
            evidence_text = "，有" + "、".join(evidence_parts) + "為證" if evidence_parts else ""
            return f"{rest_info}影響其工作能力，造成工作損失新台幣{amount}{evidence_text}。"
        
        elif category == "車輛修復費":
            vehicle_type = "機車" if "機車" in accident_facts else "車輛"
            evidence = "，有估價單為證" if "估價單" in accident_facts else ""
            return f"系爭{vehicle_type}因事故受損，支出修復費用共計新台幣{amount}{evidence}。"
        
        elif category == "預估醫療費用":
            future_desc = "未來開刀醫療" if "開刀" in accident_facts else "未來醫療"
            return f"原告主張因系爭事故而需支出{future_desc}費用新台幣{amount}。"
        
        elif category == "精神慰撫金":
            suffering_contexts = []
            if "多次就醫" in accident_facts:
                suffering_contexts.append("多次就醫，造成生活上的不便")
            elif "生活上的不便" in accident_facts:
                suffering_contexts.append("造成生活上的不便")
            
            if not suffering_contexts:
                suffering_contexts.append("身心受創")
            
            return f"原告因系爭傷害{suffering_contexts[0]}，請求精神慰撫金新台幣{amount}。"
        
        return f"原告因本事故，支出{category}新台幣{amount}。"
    
    # 動態生成賠償項目
    damage_items = []
    summary_items = []
    
    if medical_fee != "未知":
        rich_desc = generate_rich_description("醫療費用", medical_fee, injury_details, accident_facts)
        damage_items.append(f"（一）醫療費用：{medical_fee}\n{rich_desc}")
        summary_items.append(f"醫療費用{medical_fee}")
    
    if repair_fee != "未知":
        rich_desc = generate_rich_description("車輛修復費", repair_fee, injury_details, accident_facts)
        damage_items.append(f"（二）車輛修復費：{repair_fee}\n{rich_desc}")
        summary_items.append(f"車輛修復費{repair_fee}")
        
    if transport_fee != "未知":
        rich_desc = generate_rich_description("交通費", transport_fee, injury_details, accident_facts)
        damage_items.append(f"（三）交通費：{transport_fee}\n{rich_desc}")
        summary_items.append(f"交通費{transport_fee}")
        
    if work_loss != "未知":
        rich_desc = generate_rich_description("工作損失", work_loss, injury_details, accident_facts)
        damage_items.append(f"（四）工作損失：{work_loss}\n{rich_desc}")
        summary_items.append(f"工作損失{work_loss}")
        
    if future_medical != "未知":
        rich_desc = generate_rich_description("預估醫療費用", future_medical, injury_details, accident_facts)
        damage_items.append(f"（五）預估醫療費用：{future_medical}\n{rich_desc}")
        summary_items.append(f"預估醫療費用{future_medical}")
        
    if mental_damage != "未知":
        rich_desc = generate_rich_description("精神慰撫金", mental_damage, injury_details, accident_facts)
        damage_items.append(f"（六）精神慰撫金：{mental_damage}\n{rich_desc}")
        summary_items.append(f"精神慰撫金{mental_damage}")

    # 組合完整起訴書
    damages_text = "\n\n".join(damage_items)
    summary_text = "、".join(summary_items)
    
    indictment_template = f"""一、{accident_origin}

{legal_section}查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任：

{damages_text}

（七）綜上所陳，被告應賠償原告之損害，包含{summary_text}，總計{total_amount}，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。"""

    return {
        'full_indictment': indictment_template,
        'extracted_facts': extracted_facts,
        'legal_basis': legal_section
    }

# 測試
if __name__ == "__main__":
    print("🔧 載入CAG系統...")
    load_model("gemma3:27b", use_ollama=True)
    
    case_database, _ = load_indictment_excel(
        "整合_起訴書_2995_CAG用.xlsx",
        max_knowledge=175,
        facts_only=True
    )
    
    kv_cache = prepare_indictment_kv_cache(
        case_database,
        model_name="gemma3:27b",
        facts_only=True
    )
    
    print("✅ CAG系統載入完成")
    print()

    test_case = """
一、事故發生緣由：
被告於民國105年4月12日13時27分許，駕駛租賃小客車在台北市中山區中山北路與民生東路口，因未保持安全距離，追撞原告駕駛之自用小客車。

二、原告受傷情形：
原告因本次車禍受有左膝挫傷、半月軟骨受傷等傷害，經醫師診斷需休養1個月，無法正常工作。

三、請求賠償的事實根據：
1. 醫療費用：190元
2. 車輛修復費：181,144元  
3. 交通費：4,500元
4. 工作損失：33,000元
5. 精神慰撫金：99,000元
總計請求賠償317,834元
    """.strip()

    print("📝 測試案例：")
    print(test_case)
    print()
    
    print("🔄 開始模板生成...")
    result = template_based_generation(test_case, kv_cache, "gemma3:27b")
    
    print("✅ 生成完成！")
    print()
    
    print("📋 生成結果：")
    print("="*80)
    print(result['full_indictment'])
    print("="*80)