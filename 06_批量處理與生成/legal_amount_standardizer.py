#!/usr/bin/env python3
"""
法律文件金額標準化器 - 專門處理法律判決書中的各種金額格式
包含羅馬數字、中文數字、混合格式等的統一標準化處理
"""

import re
import json
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

@dataclass
class LegalAmount:
    """法律文件中的金額資訊"""
    original_text: str      # 原始文本
    amount_value: int       # 金額數值
    currency: str           # 幣種 (通常是新台幣)
    position: Tuple[int, int]  # 在文本中的位置
    confidence: float       # 解析信心度
    amount_type: str        # 金額類型(賠償金、訴訟費等)

class LegalAmountStandardizer:
    """法律文件金額標準化器"""
    
    def __init__(self):
        # 羅馬數字對照 (包含全形和半形)
        self.roman_numerals = {
            # 基本羅馬數字
            'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000,
            # 全形羅馬數字 
            'Ⅰ': 1, 'Ⅱ': 2, 'Ⅲ': 3, 'Ⅳ': 4, 'Ⅴ': 5, 'Ⅵ': 6, 'Ⅶ': 7, 'Ⅷ': 8, 'Ⅸ': 9, 'Ⅹ': 10,
            'Ⅺ': 11, 'Ⅻ': 12, 'ⅰ': 1, 'ⅱ': 2, 'ⅲ': 3, 'ⅳ': 4, 'ⅴ': 5, 'ⅵ': 6, 'ⅶ': 7, 'ⅷ': 8, 'ⅸ': 9, 'ⅹ': 10
        }
        
        # 中文數字對照
        self.chinese_numerals = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000, '萬': 10000, '億': 100000000,
            '壹': 1, '貳': 2, '參': 3, '肆': 4, '伍': 5, '陸': 6, '柒': 7, '捌': 8, '玖': 9,
            '拾': 10, '佰': 100, '仟': 1000
        }
        
        # 金額類型識別關鍵字
        self.amount_types = {
            '賠償': ['賠償', '給付', '損害', '損失'],
            '訴訟費': ['訴訟費', '裁判費', 'court_fee'],
            '律師費': ['律師費', '代理費'],
            '醫療費': ['醫療費', '醫藥費', '治療費'],
            '精神慰撫金': ['精神慰撫金', '慰撫金', '精神損害'],
            '利息': ['利息', '遲延利息'],
            '其他': ['費用', '支出', '成本']
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def standardize_document(self, text: str) -> Dict[str, Any]:
        """標準化整份法律文件中的金額"""
        
        # 步驟1: 提取所有金額
        amounts = self._extract_all_amounts(text)
        
        # 步驟2: 分類金額類型
        categorized_amounts = self._categorize_amounts(amounts, text)
        
        # 步驟3: 計算總金額
        total_calculation = self._calculate_totals(categorized_amounts)
        
        # 步驟4: 生成標準化文本
        standardized_text = self._generate_standardized_text(text, amounts)
        
        return {
            'original_text': text,
            'standardized_text': standardized_text,
            'amounts': [self._amount_to_dict(amt) for amt in amounts],
            'categorized_amounts': categorized_amounts,
            'calculations': total_calculation,
            'summary': {
                'total_amount': total_calculation.get('main_total', 0),
                'amount_count': len(amounts),
                'high_confidence_count': sum(1 for amt in amounts if amt.confidence > 0.8)
            }
        }
    
    def _extract_all_amounts(self, text: str) -> List[LegalAmount]:
        """提取文本中的所有金額"""
        amounts = []
        
        # 金額模式定義
        patterns = [
            # 1. 標準新台幣格式：新台幣123,456元
            (r'新台幣\s*(\d{1,3}(?:,\d{3})*)\s*元', self._parse_standard_amount, 1.0),
            
            # 2. 混合格式：12萬3,456元
            (r'(\d+萬\d{1,3}(?:,\d{3})*)\s*元', self._parse_mixed_wan_amount, 0.95),
            
            # 3. 純中文格式：十二萬三千四百五十六元
            (r'([一二三四五六七八九十百千萬億壹貳參肆伍陸柒捌玖拾佰仟]+)\s*元', self._parse_chinese_amount, 0.9),
            
            # 4. 羅馬數字格式：XII萬元 或 Ⅻ千元
            (r'([IVXLCDMⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫⅰⅱⅲⅳⅴⅵⅶⅷⅸⅹ]+)([千萬億]?)\s*元', self._parse_roman_amount, 0.85),
            
            # 5. 簡單數字：123,456元
            (r'(\d{1,3}(?:,\d{3})*)\s*元', self._parse_standard_amount, 0.95),
            
            # 6. 萬元格式：50萬元
            (r'(\d+)\s*萬\s*元', self._parse_wan_amount, 0.9),
            
            # 7. 千元格式：5千元
            (r'(\d+)\s*千\s*元', self._parse_qian_amount, 0.9),
        ]
        
        for pattern, parser, confidence in patterns:
            for match in re.finditer(pattern, text):
                try:
                    amount_value = parser(match.groups())
                    if amount_value and amount_value > 0:
                        amount = LegalAmount(
                            original_text=match.group(0),
                            amount_value=amount_value,
                            currency='新台幣',
                            position=match.span(),
                            confidence=confidence,
                            amount_type='未分類'
                        )
                        amounts.append(amount)
                except Exception as e:
                    self.logger.warning(f"解析金額失敗: {match.group(0)}, 錯誤: {e}")
        
        # 去除重疊的金額
        amounts = self._remove_overlapping_amounts(amounts)
        
        return amounts
    
    def _parse_standard_amount(self, groups: Tuple[str, ...]) -> int:
        """解析標準金額格式：123,456"""
        try:
            return int(groups[0].replace(',', ''))
        except:
            return 0
    
    def _parse_mixed_wan_amount(self, groups: Tuple[str, ...]) -> int:
        """解析混合萬元格式：12萬3,456"""
        try:
            text = groups[0]
            if '萬' in text:
                parts = text.split('萬')
                wan_part = int(parts[0])
                remainder = int(parts[1].replace(',', '')) if parts[1] else 0
                return wan_part * 10000 + remainder
            return 0
        except:
            return 0
    
    def _parse_chinese_amount(self, groups: Tuple[str, ...]) -> int:
        """解析中文數字金額"""
        try:
            chinese_text = groups[0]
            return self._chinese_to_number(chinese_text)
        except:
            return 0
    
    def _parse_roman_amount(self, groups: Tuple[str, ...]) -> int:
        """解析羅馬數字金額"""
        try:
            roman_text = groups[0]
            unit = groups[1] if len(groups) > 1 else ''
            
            base_value = self._roman_to_number(roman_text)
            
            if unit == '千':
                return base_value * 1000
            elif unit == '萬':
                return base_value * 10000
            elif unit == '億':
                return base_value * 100000000
            else:
                return base_value
        except:
            return 0
    
    def _parse_wan_amount(self, groups: Tuple[str, ...]) -> int:
        """解析萬元格式：50萬"""
        try:
            return int(groups[0]) * 10000
        except:
            return 0
    
    def _parse_qian_amount(self, groups: Tuple[str, ...]) -> int:
        """解析千元格式：5千"""
        try:
            return int(groups[0]) * 1000
        except:
            return 0
    
    def _roman_to_number(self, roman: str) -> int:
        """羅馬數字轉阿拉伯數字"""
        # 處理全形羅馬數字的直接對照
        if roman in self.roman_numerals:
            return self.roman_numerals[roman]
        
        # 處理傳統羅馬數字組合
        total = 0
        i = 0
        roman = roman.upper()
        
        while i < len(roman):
            if i + 1 < len(roman) and roman[i] in self.roman_numerals and roman[i + 1] in self.roman_numerals:
                if self.roman_numerals[roman[i]] < self.roman_numerals[roman[i + 1]]:
                    total += self.roman_numerals[roman[i + 1]] - self.roman_numerals[roman[i]]
                    i += 2
                else:
                    total += self.roman_numerals[roman[i]]
                    i += 1
            elif roman[i] in self.roman_numerals:
                total += self.roman_numerals[roman[i]]
                i += 1
            else:
                i += 1
        
        return total
    
    def _chinese_to_number(self, chinese: str) -> int:
        """中文數字轉阿拉伯數字"""
        if not chinese:
            return 0
        
        result = 0
        current = 0
        
        i = 0
        while i < len(chinese):
            char = chinese[i]
            if char in self.chinese_numerals:
                value = self.chinese_numerals[char]
                
                if value >= 10000:  # 萬、億
                    if current == 0:
                        current = 1
                    result += current * value
                    current = 0
                elif value >= 1000:  # 千
                    if current == 0:
                        current = 1
                    current *= value
                elif value >= 100:  # 百
                    if current == 0:
                        current = 1
                    current *= value
                elif value == 10:  # 十
                    if current == 0:
                        current = 10
                    else:
                        current *= 10
                else:  # 個位數
                    current = current + value if current > 0 else value
            i += 1
        
        return result + current
    
    def _remove_overlapping_amounts(self, amounts: List[LegalAmount]) -> List[LegalAmount]:
        """移除重疊的金額，保留信心度最高的"""
        amounts.sort(key=lambda x: x.position[0])
        
        filtered = []
        for amount in amounts:
            # 檢查是否與已有的金額重疊
            overlaps = False
            for existing in filtered:
                if self._positions_overlap(amount.position, existing.position):
                    # 如果當前金額信心度更高，替換
                    if amount.confidence > existing.confidence:
                        filtered.remove(existing)
                        break
                    else:
                        overlaps = True
                        break
            
            if not overlaps:
                filtered.append(amount)
        
        return filtered
    
    def _positions_overlap(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        """檢查兩個位置是否重疊"""
        return not (pos1[1] <= pos2[0] or pos2[1] <= pos1[0])
    
    def _categorize_amounts(self, amounts: List[LegalAmount], text: str) -> Dict[str, List[LegalAmount]]:
        """根據上下文對金額進行分類"""
        categorized = {category: [] for category in self.amount_types.keys()}
        
        for amount in amounts:
            # 獲取金額周圍的上下文
            start = max(0, amount.position[0] - 50)
            end = min(len(text), amount.position[1] + 50)
            context = text[start:end]
            
            # 根據關鍵字分類
            assigned = False
            for category, keywords in self.amount_types.items():
                if any(keyword in context for keyword in keywords):
                    amount.amount_type = category
                    categorized[category].append(amount)
                    assigned = True
                    break
            
            if not assigned:
                amount.amount_type = '其他'
                categorized['其他'].append(amount)
        
        return categorized
    
    def _calculate_totals(self, categorized_amounts: Dict[str, List[LegalAmount]]) -> Dict[str, Any]:
        """計算各類別的總金額"""
        calculations = {}
        
        # 計算各類別小計
        for category, amounts in categorized_amounts.items():
            if amounts:
                subtotal = sum(amt.amount_value for amt in amounts)
                calculations[f'{category}_subtotal'] = subtotal
                calculations[f'{category}_count'] = len(amounts)
        
        # 計算主要賠償金額（排除利息和費用）
        main_categories = ['賠償', '醫療費', '精神慰撫金']
        main_total = sum(calculations.get(f'{cat}_subtotal', 0) for cat in main_categories)
        calculations['main_total'] = main_total
        
        # 計算全部總金額
        all_total = sum(calculations.get(f'{cat}_subtotal', 0) for cat in categorized_amounts.keys())
        calculations['grand_total'] = all_total
        
        return calculations
    
    def _generate_standardized_text(self, original_text: str, amounts: List[LegalAmount]) -> str:
        """生成標準化文本"""
        text = original_text
        
        # 從後往前替換，避免位置偏移
        for amount in sorted(amounts, key=lambda x: x.position[0], reverse=True):
            start, end = amount.position
            standardized = f"新台幣{amount.amount_value:,}元"
            text = text[:start] + standardized + text[end:]
        
        return text
    
    def _amount_to_dict(self, amount: LegalAmount) -> Dict[str, Any]:
        """將LegalAmount轉換為字典"""
        return {
            'original_text': amount.original_text,
            'amount_value': amount.amount_value,
            'formatted_amount': f"{amount.amount_value:,}元",
            'currency': amount.currency,
            'position': amount.position,
            'confidence': amount.confidence,
            'amount_type': amount.amount_type
        }

def test_legal_standardizer():
    """測試法律文件金額標準化器"""
    standardizer = LegalAmountStandardizer()
    
    test_cases = [
        "判決被告應賠償原告新台幣十二萬三千四百五十六元",
        "被告應連帶給付原告醫療費用5,000元、精神慰撫金十萬元、看護費用二萬元", 
        "應賠償車輛修理費156,789元、營業損失30萬元、拖吊費2,000元",
        "判決賠償：慰撫金XX萬元、醫療費Ⅴ千元、工作損失15萬元",
        "判決被告應給付原告新台幣Ⅻ萬元及自起訴狀繕本送達翌日起至清償日止按年息百分之五計算之利息"
    ]
    
    print("⚖️  法律文件金額標準化器測試")
    print("="*80)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n📋 測試案例 {i}:")
        print(f"原始: {test_text}")
        
        result = standardizer.standardize_document(test_text)
        
        print(f"標準化: {result['standardized_text']}")
        print(f"主要金額: {result['summary']['total_amount']:,}元")
        print(f"金額數量: {result['summary']['amount_count']}")
        
        if result['amounts']:
            print("💰 金額明細:")
            for amt in result['amounts']:
                print(f"  - {amt['original_text']} → {amt['formatted_amount']} "
                      f"({amt['amount_type']}, 信心度: {amt['confidence']:.2f})")
        
        print("📊 分類統計:")
        for category, amounts in result['categorized_amounts'].items():
            if amounts:
                subtotal = sum(amt.amount_value for amt in amounts)
                print(f"  - {category}: {subtotal:,}元 ({len(amounts)}筆)")

if __name__ == "__main__":
    test_legal_standardizer()