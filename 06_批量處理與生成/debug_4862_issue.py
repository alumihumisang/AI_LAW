#!/usr/bin/env python3
"""
調試4862元問題
"""

def debug_4862_issue():
    from universal_format_handler import UniversalFormatHandler
    
    handler = UniversalFormatHandler()
    
    # 測試文本
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
    
    print("🔍 調試4862元問題")
    print("=" * 80)
    
    # 提取項目
    items = handler.extract_damage_items(test_text)
    
    print(f"📊 找到的4862元項目:")
    for item in items:
        if item.amount == 4862:
            plaintiff_key = handler._extract_plaintiff_context(item)
            print(f"\n🔍 4862元項目:")
            print(f"  原告: {plaintiff_key}")
            print(f"  描述: {item.description}")
            print(f"  原始文本: {item.raw_text[:100]}...")
            print(f"  類型: {item.type}")
            print(f"  置信度: {item.confidence}")
            
            # 手動檢查這個項目為什麼分配給這個原告
            text_to_check = f"{item.description} {item.raw_text}"
            print(f"  檢查文本: {text_to_check[:150]}...")
            
            # 測試各種條件
            print(f"  條件檢查:")
            print(f"    包含'陳慶華': {'陳慶華' in text_to_check}")
            print(f"    包含'朱庭慧': {'朱庭慧' in text_to_check}")
            print(f"    包含'（一）': {'（一）' in text_to_check}")
            print(f"    包含'（二）': {'（二）' in text_to_check}")
            print(f"    包含'4,862': {'4,862' in text_to_check}")

if __name__ == "__main__":
    debug_4862_issue()