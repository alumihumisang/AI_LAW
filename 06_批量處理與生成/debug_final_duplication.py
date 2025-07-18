#!/usr/bin/env python3
"""
最終調試重複計算問題
"""

def debug_final_duplication():
    from universal_format_handler import UniversalFormatHandler
    
    handler = UniversalFormatHandler()
    
    # 完整測試文本
    test_text = """三、損害項目：

（一）原告陳慶華之損害：
1. 醫療費用：1,036元
原告陳慶華因本次事故受傷就醫，支出醫療費用1,036元。
2. 車損修理費用：413,300元
原告陳慶華因本次事故車輛受損，支出修復費用413,300元。
3. 精神慰撫金：300,000元
原告陳慶華因被告拒絕承認肇事責任並誣指其肇事逃逸，承受精神痛苦，請求精神慰撫金300,000元。
（二）原告朱庭慧之損害：
1. 醫療費用：4,862元
原告朱庭慧因本次事故受傷就醫，支出醫療費用4,862元。
2. 薪資損失：3,225元
原告朱庭慧因本次事故請假，遭受薪資扣減3,225元。
3. 精神慰撫金：300,000元
原告朱庭慧因臉部留疤、自信受創且被告拒絕賠償，承受精神痛苦，請求精神慰撫金300,000元。"""
    
    print("🔍 最終調試重複計算問題")
    print("=" * 80)
    
    # 詳細分析去重過程
    print("1️⃣ 格式檢測:")
    format_info = handler.detect_format(test_text)
    print(f"   主要格式: {format_info['primary_format']}")
    
    print("\n2️⃣ 混合提取結果:")
    mixed_items = handler._extract_by_mixed_strategy(test_text)
    
    # 按金額分組統計
    amount_groups = {}
    for item in mixed_items:
        if item.amount not in amount_groups:
            amount_groups[item.amount] = []
        amount_groups[item.amount].append(item)
    
    print("   混合提取前按金額分組:")
    for amount, items_list in sorted(amount_groups.items()):
        print(f"     {amount:,}元: {len(items_list)}個")
        for i, item in enumerate(items_list):
            plaintiff_key = handler._extract_plaintiff_context(item)
            print(f"       {i+1}. 原告: {plaintiff_key} - 描述: {item.description[:40]}...")
    
    print("\n3️⃣ 去重處理:")
    deduplicated = handler._deduplicate_items(mixed_items)
    
    # 去重後統計
    dedup_groups = {}
    for item in deduplicated:
        if item.amount not in dedup_groups:
            dedup_groups[item.amount] = []
        dedup_groups[item.amount].append(item)
    
    print("   去重後按金額分組:")
    for amount, items_list in sorted(dedup_groups.items()):
        print(f"     {amount:,}元: {len(items_list)}個")
        for i, item in enumerate(items_list):
            plaintiff_key = handler._extract_plaintiff_context(item)
            print(f"       {i+1}. 原告: {plaintiff_key} - 描述: {item.description[:40]}...")
    
    print("\n4️⃣ 期望vs實際:")
    expected = {1036: 1, 413300: 1, 300000: 2, 4862: 1, 3225: 1}
    
    for amount, expected_count in expected.items():
        actual_count = len(dedup_groups.get(amount, []))
        status = "✅" if actual_count == expected_count else "❌"
        print(f"   {status} {amount:,}元: 期望{expected_count}個, 實際{actual_count}個")
    
    expected_total = sum(k*v for k,v in expected.items())
    actual_total = sum(item.amount for item in deduplicated)
    print(f"\n💰 總金額: 期望{expected_total:,}元, 實際{actual_total:,}元")

if __name__ == "__main__":
    debug_final_duplication()