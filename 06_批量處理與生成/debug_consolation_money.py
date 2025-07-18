#!/usr/bin/env python3
"""
調試慰撫金去重問題
"""

def debug_consolation_money():
    from KG_700_CoT_Hybrid import HybridCoTGenerator
    
    generator = HybridCoTGenerator()
    
    # 測試多原告相同慰撫金的案例
    compensation_text = """三、損害項目：

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
    
    print("🔍 調試慰撫金去重問題")
    print("=" * 80)
    print(f"測試文本包含兩個30萬元慰撫金")
    print("=" * 80)
    
    # 測試金額提取
    amounts = generator._extract_valid_claim_amounts(compensation_text)
    
    print(f"📊 提取結果:")
    print(f"提取到的金額: {amounts}")
    print(f"金額數量: {len(amounts)}")
    print(f"總計: {sum(amounts):,}元")
    
    # 分析300,000元的出現次數
    consolation_count = amounts.count(300000)
    print(f"\n🔍 慰撫金分析:")
    print(f"300,000元出現次數: {consolation_count}")
    
    # 預期結果
    expected_amounts = [1036, 413300, 300000, 4862, 3225, 300000]  # 應該有兩個30萬元
    expected_total = sum(expected_amounts)
    
    print(f"\n✅ 預期結果:")
    print(f"預期金額: {expected_amounts}")
    print(f"預期總計: {expected_total:,}元")
    print(f"實際總計: {sum(amounts):,}元")
    
    if consolation_count == 2:
        print(f"\n🎉 慰撫金計算正確：兩個原告各自的30萬元都被保留")
    elif consolation_count == 1:
        print(f"\n❌ 慰撫金被錯誤去重：只保留了一個30萬元")
    else:
        print(f"\n⚠️ 慰撫金計算異常：發現{consolation_count}個30萬元")
    
    # 測試通用格式處理器的去重邏輯
    print(f"\n🔄 測試通用格式處理器:")
    if generator.format_handler:
        damage_items = generator.format_handler.extract_damage_items(compensation_text)
        print(f"通用格式處理器提取到 {len(damage_items)} 個項目:")
        consolation_items = [item for item in damage_items if item.amount == 300000]
        print(f"其中30萬元項目: {len(consolation_items)} 個")
        
        for i, item in enumerate(consolation_items):
            print(f"  項目{i+1}: {item.amount:,}元 - {item.description[:50]}...")

if __name__ == "__main__":
    debug_consolation_money()