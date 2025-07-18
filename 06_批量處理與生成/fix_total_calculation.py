#!/usr/bin/env python3
"""
修復總金額計算問題的方案
"""

def create_unified_calculation_approach():
    """
    創建統一的金額計算方法，確保第三部分和第四部分使用相同的金額
    """
    
    print("🔧 修復總金額計算問題")
    print("=" * 60)
    print()
    
    print("💡 解決方案：統一金額計算管道")
    print()
    
    print("📋 當前問題：")
    print("1. 第三部分：使用LLM生成損害項目（準確）")
    print("2. 第四部分：重新提取已生成文本的金額（容易出錯）")
    print("3. 結果：兩個部分可能產生不同的金額計算")
    print()
    
    print("✅ 建議的修復方法：")
    print("方法1: 讓第四部分直接使用第三部分的提取結果")
    print("方法2: 統一使用同一個金額提取函數")
    print("方法3: 添加驗證機制，確保兩部分金額一致")
    print()
    
    print("🎯 具體實施步驟：")
    print("1. 修改generate_cot_conclusion_with_smart_amount_calculation函數")
    print("2. 讓它直接使用已提取的損害項目計算總額")
    print("3. 避免重新解析生成的文本")
    print("4. 添加金額一致性檢查")
    print()
    
    # 示例代碼
    print("💻 示例修復代碼：")
    print("""
def generate_cot_conclusion_with_unified_amounts(self, facts, damages, parties):
    '''使用統一的金額計算邏輯'''
    
    # 方法1: 直接從已生成的damages文本中提取結構化金額
    structured_amounts = self._extract_damage_items_from_text(damages)
    
    # 計算總金額
    total_amount = 0
    amount_details = []
    
    for plaintiff, items in structured_amounts.items():
        for item in items:
            total_amount += item['amount']
            amount_details.append(f"{item['name']}{item['amount']:,}元")
    
    # 生成結論，直接使用計算好的總額
    conclusion = self._generate_conclusion_with_known_total(
        facts, damages, parties, amount_details, total_amount
    )
    
    return conclusion
""")
    
    print()
    print("🔍 優點：")
    print("- 確保第三、四部分使用相同的金額")
    print("- 消除重複計算錯誤")
    print("- 提高計算準確性")
    print("- 簡化邏輯流程")

if __name__ == "__main__":
    create_unified_calculation_approach()