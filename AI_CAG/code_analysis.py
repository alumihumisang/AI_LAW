#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代碼分析工具 - 分析cag_indictment_generator.py的結構
"""

import re

def analyze_code_structure():
    """分析代碼結構並提出重構建議"""
    
    print("=" * 80)
    print("📊 CAG程式碼結構分析")
    print("=" * 80)
    
    # 讀取主檔案
    with open('cag_indictment_generator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 分析方法
    methods = re.findall(r'def ([^(]+)\([^)]*\):', content)
    
    print(f"📋 總方法數量: {len(methods)}")
    print(f"📄 總行數: {len(content.splitlines())}")
    print(f"📝 平均每方法行數: {len(content.splitlines()) // len(methods)}")
    
    print(f"\n🔍 功能分類分析:")
    
    # 按功能分類方法
    categories = {
        '智能分類相關': [
            '_categorize_amounts_with_context', '_extract_amounts_with_context',
            '_extract_valid_claim_amounts', '_filter_amounts_by_keywords',
            '_categorize_amount_by_patterns', '_classify_amount_smart',
            'generate_compensation_with_smart_classification',
            '_generate_smart_description', '_is_unstructured_text',
            'generate_compensation_adaptive'
        ],
        '金額處理相關': [
            'extract_and_display_amounts', 'parse_amount', 'format_amount',
            'calculate_total_amount_for_item', 'convert_chinese_to_arabic_numbers',
            'convert_to_chinese_number', '_extract_amounts_simple',
            '_extract_amounts_from_text'
        ],
        '解析器相關': [
            'universal_parse_lawyer_input', 'parse_lawyer_items', 
            'parse_completed_indictment', 'extract_basic_info_only',
            'process_compensation_item', 'detect_input_type'
        ],
        '模板生成相關': [
            'enhanced_template_generation', 'generate_flexible_indictment',
            'format_compensation_section', 'generate_compensation_content',
            'generate_item_content', 'generate_rich_description',
            'generate_simple_item_description'
        ],
        'RAG/LLM整合': [
            'generate_compensation_with_rag_llm', 'smart_compensation_generation',
            '_generate_llm_based_compensation', 'find_similar_cases_cag'
        ],
        '主系統功能': [
            '__init__', 'welcome_message', 'setup_system', 'get_user_input',
            'run', 'display_results', 'generate_complete_indictment',
            'generate_legal_basis'
        ]
    }
    
    for category, category_methods in categories.items():
        found_methods = [m for m in methods if any(cm in m for cm in category_methods)]
        print(f"  📂 {category}: {len(found_methods)}個方法")
        for method in found_methods[:5]:  # 只顯示前5個
            print(f"     • {method}")
        if len(found_methods) > 5:
            print(f"     ... 還有{len(found_methods)-5}個方法")
    
    # 尋找重複或相似功能
    print(f"\n⚠️ 潜在重複功能:")
    
    # 金額提取相關的重複
    amount_methods = [m for m in methods if 'extract' in m and 'amount' in m]
    if len(amount_methods) > 1:
        print(f"  💰 金額提取方法: {len(amount_methods)}個")
        for method in amount_methods:
            print(f"     • {method}")
    
    # 分類相關的重複  
    classify_methods = [m for m in methods if 'categor' in m or 'classif' in m]
    if len(classify_methods) > 1:
        print(f"  🏷️ 分類方法: {len(classify_methods)}個")
        for method in classify_methods:
            print(f"     • {method}")
    
    # 生成相關的重複
    generate_methods = [m for m in methods if 'generate' in m and 'compensation' in m]
    if len(generate_methods) > 1:
        print(f"  📝 賠償生成方法: {len(generate_methods)}個")
        for method in generate_methods:
            print(f"     • {method}")
    
    print(f"\n🔧 重構建議:")
    print("1. 📦 創建獨立模組:")
    print("   • smart_classifier.py - 智能分類相關功能")
    print("   • amount_processor.py - 金額處理相關功能") 
    print("   • template_generator.py - 模板生成相關功能")
    print("   • text_parser.py - 文本解析相關功能")
    
    print("\n2. 🔄 整合重複功能:")
    print("   • 合併多個金額提取方法")
    print("   • 統一分類邏輯")
    print("   • 簡化生成流程")
    
    print("\n3. 🗑️ 清理廢棄代碼:")
    print("   • 移除unused方法")
    print("   • 清理重複的helper函數")
    print("   • 簡化過度複雜的方法")

if __name__ == "__main__":
    analyze_code_structure()