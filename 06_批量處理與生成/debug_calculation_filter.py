#!/usr/bin/env python3
"""
調試計算基準過濾問題
"""

def debug_calculation_filter():
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
    
    print("🔍 調試計算基準過濾問題")
    print("=" * 80)
    
    # 執行混合提取
    mixed_items = handler._extract_by_mixed_strategy(test_text)
    print(f"1️⃣ 混合提取結果: {len(mixed_items)}個項目")
    
    # 執行去重
    deduplicated = handler._deduplicate_items(mixed_items)
    print(f"2️⃣ 去重後結果: {len(deduplicated)}個項目")
    
    # 檢查300,000元項目
    print(f"\n📊 去重後300,000元項目:")
    for item in deduplicated:
        if item.amount == 300000:
            plaintiff_key = handler._extract_plaintiff_context(item)
            print(f"  ✅ 找到300,000元項目 - 原告: {plaintiff_key}")
            print(f"    描述: {item.description[:50]}...")
            print(f"    原始文本: {item.raw_text[:100]}...")
    
    # 執行計算基準過濾
    print(f"\n3️⃣ 計算基準過濾:")
    filtered = handler._filter_calculation_bases(deduplicated)
    print(f"過濾後結果: {len(filtered)}個項目")
    
    # 檢查過濾後的300,000元項目
    print(f"\n📊 過濾後300,000元項目:")
    found_300k = False
    for item in filtered:
        if item.amount == 300000:
            found_300k = True
            plaintiff_key = handler._extract_plaintiff_context(item)
            print(f"  ✅ 保留300,000元項目 - 原告: {plaintiff_key}")
            print(f"    描述: {item.description[:50]}...")
    
    if not found_300k:
        print(f"  ❌ 沒有找到300,000元項目，已被過濾掉！")
    
    # 總結
    print(f"\n📋 項目變化:")
    print(f"  混合提取: {len(mixed_items)}個")
    print(f"  去重後: {len(deduplicated)}個")
    print(f"  過濾後: {len(filtered)}個")

if __name__ == "__main__":
    debug_calculation_filter()