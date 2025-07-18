#!/usr/bin/env python3
"""
調試所有金額的去重問題
"""

def debug_all_amounts():
    from universal_format_handler import UniversalFormatHandler
    
    handler = UniversalFormatHandler()
    
    # 完整的測試文本
    test_text = """三、損害項目：

（一）原告陳慶華之損害：
1. 醫療費用：1,036元
原告陳慶華因本次事故受傷就醫，支出醫療費用1,036元。
2. 車損修理費用：413,300元
原告陳慶華因本次事故車輛受損，支出修復費用413,300元。
3. 精神慰撫金：300,000元
原告陳慶華因被告拒絕承認肇事責任及誣指肇事逃逸，遭受精神痛苦，請求精神慰撫金300,000元。

（二）原告朱庭慧之損害：
1. 醫療費用：4,862元
原告朱庭慧因本次事故受傷就醫，支出醫療費用4,862元。
2. 薪資損失：3,225元
原告朱庭慧因本次事故受傷請假，遭受薪資扣除3,225元。
3. 精神慰撫金：300,000元
原告朱庭慧因臉部留下疤痕、自信受創、業績下降，以及被告拒絕承認肇事責任，遭受精神痛苦，請求精神慰撫金300,000元。"""
    
    print("🔍 調試所有金額的去重問題")
    print("=" * 80)
    
    # 直接提取並分析
    items = handler.extract_damage_items(test_text)
    
    print(f"📊 最終提取結果:")
    print(f"總項目數: {len(items)}")
    
    # 按金額分組統計
    amount_counts = {}
    for item in items:
        amount = item.amount
        if amount not in amount_counts:
            amount_counts[amount] = []
        amount_counts[amount].append(item)
    
    print(f"\n📈 金額統計:")
    for amount, items_list in sorted(amount_counts.items()):
        plaintiff_contexts = []
        for item in items_list:
            plaintiff_key = handler._extract_plaintiff_context(item)
            plaintiff_contexts.append(plaintiff_key)
        
        print(f"  {amount:,}元: {len(items_list)}個 - 原告: {set(plaintiff_contexts)}")
        for i, item in enumerate(items_list):
            plaintiff_key = handler._extract_plaintiff_context(item)
            print(f"    {i+1}. 原告: {plaintiff_key} - 描述: {item.description[:30]}...")
    
    # 預期結果
    expected_amounts = {1036: 1, 413300: 1, 300000: 2, 4862: 1, 3225: 1}
    
    print(f"\n✅ 預期vs實際:")
    for amount, expected_count in expected_amounts.items():
        actual_count = len(amount_counts.get(amount, []))
        status = "✅" if actual_count == expected_count else "❌"
        print(f"  {status} {amount:,}元: 預期{expected_count}個, 實際{actual_count}個")
    
    total_expected = sum(expected_amounts.keys()) * sum(expected_amounts.values()) - sum(k*v for k,v in expected_amounts.items()) + sum(k*v for k,v in expected_amounts.items())
    total_actual = sum(item.amount for item in items)
    
    print(f"\n💰 總金額:")
    print(f"  預期: {1036 + 413300 + 300000*2 + 4862 + 3225:,}元")
    print(f"  實際: {total_actual:,}元")

if __name__ == "__main__":
    debug_all_amounts()