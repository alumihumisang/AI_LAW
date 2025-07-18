#!/usr/bin/env python3
"""
結構化法律文件金額處理器
專門處理起訴狀等結構化法律文件中的金額識別和計算問題
解決說明文字干擾、重複計算等問題
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from legal_amount_standardizer import LegalAmountStandardizer, LegalAmount

@dataclass
class StructuredItem:
    """結構化項目"""
    item_number: str        # 項目編號 (如 "1.", "2.")
    item_title: str         # 項目標題 (如 "醫療費用")
    main_amount: int        # 主要金額
    description: str        # 說明文字
    description_amounts: List[int]  # 說明中的金額（僅供參考）
    confidence: float       # 信心度

class StructuredLegalAmountProcessor:
    """結構化法律文件金額處理器"""
    
    def __init__(self):
        self.base_standardizer = LegalAmountStandardizer()
        
        # 結構化模式
        self.item_patterns = [
            # 標準編號格式：1. 項目名稱：金額
            r'(\d+)\.\s*([^：:]+)[：:]\s*([0-9,]+元)',
            # 中文編號：（一）、（二）等
            r'（([一二三四五六七八九十]+)）\s*([^：:]+)[：:]\s*([0-9,]+元)',
            # 英文編號：(1)、(2)等
            r'\((\d+)\)\s*([^：:]+)[：:]\s*([0-9,]+元)'
        ]
        
        # 說明文字標識
        self.description_markers = ['說明：', '說明:', '備註：', '備註:', '註：', '註:']
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def process_structured_document(self, text: str) -> Dict[str, Any]:
        """處理結構化法律文件"""
        print("📄 處理結構化法律文件...")
        
        # 步驟1: 分段處理
        sections = self._split_into_sections(text)
        
        # 步驟2: 識別結構化項目
        structured_items = []
        for section in sections:
            items = self._extract_structured_items(section)
            structured_items.extend(items)
        
        # 步驟3: 計算總金額
        total_calculation = self._calculate_structured_total(structured_items)
        
        # 步驟4: 驗證和報告
        validation_result = self._validate_against_conclusion(text, total_calculation['total'])
        
        return {
            'structured_items': [self._item_to_dict(item) for item in structured_items],
            'calculation': total_calculation,
            'validation': validation_result,
            'summary': {
                'total_amount': total_calculation['total'],
                'item_count': len(structured_items),
                'sections_processed': len(sections)
            }
        }
    
    def _split_into_sections(self, text: str) -> List[str]:
        """將文本分割為結構化段落"""
        # 按照法律文件的典型結構分段
        section_patterns = [
            r'（[一二三四五六七八九十]+）[^（]*?(?=（[一二三四五六七八九十]+）|$)',  # 中文編號段落
            r'\d+\.[^0-9]+?(?=\d+\.|$)',  # 數字編號段落
        ]
        
        sections = []
        remaining_text = text
        
        for pattern in section_patterns:
            matches = re.findall(pattern, remaining_text, re.DOTALL)
            sections.extend(matches)
        
        # 如果沒有明顯的結構，就按段落分割
        if not sections:
            sections = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        return sections
    
    def _extract_structured_items(self, section_text: str) -> List[StructuredItem]:
        """從段落中提取結構化項目"""
        items = []
        
        # 按行處理，識別項目
        lines = section_text.split('\n')
        current_item = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 檢查是否是新的項目開始
            item_match = self._match_item_line(line)
            if item_match:
                # 保存前一個項目
                if current_item:
                    items.append(current_item)
                
                # 開始新項目
                item_number, item_title, amount_text = item_match
                amount = self._extract_clean_amount(amount_text)
                
                current_item = StructuredItem(
                    item_number=item_number,
                    item_title=item_title.strip(),
                    main_amount=amount,
                    description="",
                    description_amounts=[],
                    confidence=0.9
                )
            
            # 檢查是否是說明文字
            elif current_item and any(marker in line for marker in self.description_markers):
                current_item.description = line
                # 提取說明中的金額（僅供參考，不計入總額）
                desc_amounts = self._extract_description_amounts(line)
                current_item.description_amounts = desc_amounts
        
        # 保存最後一個項目
        if current_item:
            items.append(current_item)
        
        return items
    
    def _match_item_line(self, line: str) -> Optional[Tuple[str, str, str]]:
        """匹配項目行"""
        for pattern in self.item_patterns:
            match = re.search(pattern, line)
            if match:
                return match.groups()
        return None
    
    def _extract_clean_amount(self, amount_text: str) -> int:
        """提取乾淨的金額數字"""
        try:
            # 移除逗號和"元"字
            clean_text = amount_text.replace(',', '').replace('元', '')
            return int(clean_text)
        except:
            return 0
    
    def _extract_description_amounts(self, description: str) -> List[int]:
        """提取說明文字中的金額（僅供參考）"""
        amounts = []
        # 查找說明中的金額
        amount_matches = re.findall(r'(\d{1,3}(?:,\d{3})*)\s*元', description)
        for match in amount_matches:
            try:
                amount = int(match.replace(',', ''))
                amounts.append(amount)
            except:
                continue
        return amounts
    
    def _calculate_structured_total(self, items: List[StructuredItem]) -> Dict[str, Any]:
        """計算結構化項目的總金額"""
        total = sum(item.main_amount for item in items)
        
        # 按類別統計
        categories = {}
        for item in items:
            title = item.item_title
            if title not in categories:
                categories[title] = []
            categories[title].append(item.main_amount)
        
        return {
            'total': total,
            'item_count': len(items),
            'categories': categories,
            'items_detail': [
                {
                    'number': item.item_number,
                    'title': item.item_title,
                    'amount': item.main_amount
                }
                for item in items
            ]
        }
    
    def _validate_against_conclusion(self, full_text: str, calculated_total: int) -> Dict[str, Any]:
        """與結論中的總金額進行驗證"""
        # 查找結論中的總金額
        conclusion_patterns = [
            r'總計\s*(?:新台幣)?\s*([0-9,]+)\s*元',
            r'合計\s*(?:新台幣)?\s*([0-9,]+)\s*元',
            r'賠償.*?總計\s*(?:新台幣)?\s*([0-9,]+)\s*元',
            r'請求.*?賠償.*?(?:新台幣)?\s*([0-9,]+)\s*元'
        ]
        
        claimed_total = None
        for pattern in conclusion_patterns:
            match = re.search(pattern, full_text)
            if match:
                try:
                    claimed_total = int(match.group(1).replace(',', ''))
                    break
                except:
                    continue
        
        validation = {
            'calculated_total': calculated_total,
            'claimed_total': claimed_total,
            'match': False,
            'difference': 0,
            'status': 'unknown'
        }
        
        if claimed_total is not None:
            validation['match'] = (calculated_total == claimed_total)
            validation['difference'] = claimed_total - calculated_total
            
            if validation['match']:
                validation['status'] = 'correct'
            elif validation['difference'] > 0:
                validation['status'] = 'understated'  # 少算了
            else:
                validation['status'] = 'overstated'   # 多算了
        
        return validation
    
    def _item_to_dict(self, item: StructuredItem) -> Dict[str, Any]:
        """將結構化項目轉換為字典"""
        return {
            'item_number': item.item_number,
            'item_title': item.item_title,
            'main_amount': item.main_amount,
            'formatted_amount': f"{item.main_amount:,}元",
            'description': item.description,
            'description_amounts': item.description_amounts,
            'confidence': item.confidence
        }
    
    def generate_corrected_conclusion(self, structured_result: Dict[str, Any]) -> str:
        """生成修正後的結論"""
        calculation = structured_result['calculation']
        validation = structured_result['validation']
        
        conclusion = "四、結論：\n"
        conclusion += "綜上所陳，各項損害明細如下：\n\n"
        
        # 列出所有項目
        for item in calculation['items_detail']:
            conclusion += f"{item['number']} {item['title']}：{item['amount']:,}元\n"
        
        total = calculation['total']
        conclusion += f"\n損害總計：新台幣{total:,}元整\n"
        
        # 如果有差異，說明修正
        if validation['claimed_total'] and not validation['match']:
            conclusion += f"\n（註：原起訴狀聲稱{validation['claimed_total']:,}元，"
            if validation['difference'] > 0:
                conclusion += f"少算{validation['difference']:,}元）"
            else:
                conclusion += f"多算{abs(validation['difference']):,}元）"
        
        conclusion += "\n\n請求被告連帶賠償原告損害總計新台幣" + f"{total:,}元整，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。"
        
        return conclusion

def test_structured_processor():
    """測試結構化處理器"""
    
    # 實際案例文本
    test_text = """
三、損害項目：

（一）原告吳麗娟之損害：
1. 醫療費用：10,820元
   說明：原告吳麗娟因本次車禍支出臺北榮民總醫院1,490元、馬偕紀念醫院1,580元、內湖菁英診所6,000元及中醫1,750元等醫療費用。
2. 未來手術費用：264,379元
   說明：原告吳麗娟因本次車禍經榮民總醫院確診發生腰椎第一、二節脊椎滑脫，預計未來手術費用為264,379元。
3. 慰撫金：200,000元
   說明：原告吳麗娟因本次車禍除受外傷外，尚因受撞擊拉扯，須長期治療及復健，且未來尚須負擔沉重手術費用，故請求慰撫金200,000元。
4. 看護費用：152,500元
   說明：原告吳麗娟因本次車禍身體受猛烈撞擊震盪，養傷期間無生活自主能力，自107年7月24日起至107年11月23日止，平均分攤看護費用共計305,000元之半數。
5. 計程車車資：19,685元
   說明：原告吳麗娟因本次車禍受傷，搭乘計程車前往醫院就診及復健，平均分攤計程車車資39,370元之半數。

（二）原告陳碧翔之損害：
1. 醫療費用：13,180元
   說明：原告陳碧翔因本次車禍支出臺北榮民總醫院6,080元、馬偕紀念醫院1,500元及中醫費用5,600元等醫療費用。
2. 假牙裝置費用：24,000元
   說明：原告陳碧翔因本次車禍頭部右側遭受重擊，假牙脫落，需重新安裝假牙裝置，費用為24,000元。
3. 慰撫金：200,000元
   說明：原告陳碧翔因本次車禍除受外傷外，尚因受撞擊拉扯，須長期治療及復健，以及重裝假牙的時間，造成生活多處不便，故請求慰撫金200,000元。
4. 看護費用：152,500元
   說明：原告陳碧翔因本次車禍身體受猛烈撞擊震盪，養傷期間無生活自主能力，自107年7月24日起至107年11月23日止，平均分攤看護費用共計305,000元之半數。
5. 計程車車資：19,685元
   說明：原告陳碧翔因本次車禍受傷，搭乘計程車前往醫院就診及復健，平均分攤計程車車資39,370元之半數。

四、結論：
綜上所陳，請求被告連帶賠償原告損害總計新台幣858,748元整，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。
"""
    
    print("🧪 結構化法律文件處理器測試")
    print("=" * 80)
    
    processor = StructuredLegalAmountProcessor()
    result = processor.process_structured_document(test_text)
    
    print("📊 結構化項目識別結果:")
    for i, item in enumerate(result['structured_items'], 1):
        print(f"{i:2d}. [{item['item_number']}] {item['item_title']}: {item['formatted_amount']}")
        if item['description_amounts']:
            print(f"     說明中的金額: {[f'{amt:,}元' for amt in item['description_amounts']]} (僅供參考)")
    
    print(f"\n💰 計算結果:")
    calc = result['calculation']
    print(f"項目總數: {calc['item_count']}")
    print(f"計算總額: {calc['total']:,}元")
    
    print(f"\n🔍 驗證結果:")
    val = result['validation']
    print(f"計算總額: {val['calculated_total']:,}元")
    if val['claimed_total']:
        print(f"聲稱總額: {val['claimed_total']:,}元")
        print(f"狀態: {val['status']}")
        if val['difference'] != 0:
            if val['difference'] > 0:
                print(f"❌ 起訴狀少算了 {val['difference']:,}元")
            else:
                print(f"❌ 起訴狀多算了 {abs(val['difference']):,}元")
        else:
            print(f"✅ 金額計算正確")
    
    # 生成修正後的結論
    print(f"\n📝 修正後的結論:")
    corrected = processor.generate_corrected_conclusion(result)
    print(corrected)

if __name__ == "__main__":
    test_structured_processor()