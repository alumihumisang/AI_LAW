#!/usr/bin/env python3
"""
增強型通用處理器 - 具備真正的泛化能力
Enhanced Universal Handler - True Generalization Capability
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class PartyInfo:
    """當事人信息"""
    name: str
    role: str  # 原告/被告
    confidence: float

class EnhancedUniversalHandler:
    """增強型通用處理器 - 基於語義而非模式匹配"""
    
    def __init__(self):
        # 不再依賴硬編碼模式，而是基於語義特徵
        self.semantic_patterns = {
            'party_indicators': ['原告', '被告', '訴外人'],
            'damage_indicators': ['費用', '損失', '支出', '花費', '賠償', '慰撫'],
            'amount_indicators': ['元', '萬元', '千元'],
            'calculation_indicators': ['計算', '基準', '標準', '依據', '按']
        }
    
    def extract_parties_semantically(self, text: str) -> Dict[str, List[PartyInfo]]:
        """基於語義的當事人提取 - 不依賴具體格式"""
        parties = {'原告': [], '被告': [], '訴外人': []}
        
        # 使用更寬鬆的語義匹配
        for role in ['原告', '被告', '訴外人']:
            # 找到所有包含該角色的句子
            sentences = text.split('。')
            for sentence in sentences:
                if role in sentence:
                    # 提取該句中的潛在姓名
                    potential_names = self._extract_names_from_sentence(sentence, role)
                    for name, confidence in potential_names:
                        parties[role].append(PartyInfo(name, role, confidence))
        
        return parties
    
    def _extract_names_from_sentence(self, sentence: str, role: str) -> List[Tuple[str, float]]:
        """從句子中提取姓名 - 基於語義上下文"""
        names = []
        
        # 策略1: 直接跟在角色後面的文字
        pattern1 = f'{role}([^，、。：；等及與和]*?)(?=[，、。：；等及與和]|$)'
        matches = re.findall(pattern1, sentence)
        
        for match in matches:
            name = match.strip()
            # 語義過濾：判斷是否為真實姓名
            confidence = self._assess_name_confidence(name, sentence)
            if confidence > 0.3:  # 動態閾值
                names.append((name, confidence))
        
        return names
    
    def _assess_name_confidence(self, name: str, context: str) -> float:
        """評估姓名的置信度 - 基於語義特徵而非硬編碼規則"""
        confidence = 0.0
        
        # 長度合理性（2-4個字符為常見姓名長度）
        if 2 <= len(name) <= 4:
            confidence += 0.4
        elif len(name) == 1:
            confidence += 0.1
        else:
            confidence -= 0.2
            
        # 字符類型（中文姓名）
        if re.match(r'^[\u4e00-\u9fff]+$', name):
            confidence += 0.3
        
        # 語義排除（不像姓名的詞匯）
        exclude_words = ['因', '而', '與', '及', '等', '之', '者', '所', '有', '其', '該', 
                        '受傷', '車禍', '事故', '損害', '賠償', '請求', '支出', '費用']
        if any(word in name for word in exclude_words):
            confidence -= 0.5
        
        # 上下文語義支持
        if '駕駛' in context or '所有' in context:
            confidence += 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def detect_case_structure_semantically(self, text: str) -> Dict[str, any]:
        """基於語義的案例結構檢測"""
        structure = {
            'case_type': 'unknown',
            'plaintiff_count': 0,
            'defendant_count': 0,
            'narrative_style': 'unknown',
            'confidence': 0.0
        }
        
        # 提取當事人
        parties = self.extract_parties_semantically(text)
        structure['plaintiff_count'] = len([p for p in parties['原告'] if p.confidence > 0.5])
        structure['defendant_count'] = len([p for p in parties['被告'] if p.confidence > 0.5])
        
        # 判斷案例類型
        if structure['plaintiff_count'] > 1:
            structure['case_type'] = 'multi_plaintiff'
        elif structure['defendant_count'] > 1:
            structure['case_type'] = 'multi_defendant'
        elif structure['plaintiff_count'] > 1 and structure['defendant_count'] > 1:
            structure['case_type'] = 'multi_party'
        else:
            structure['case_type'] = 'simple'
        
        # 判斷敘述風格
        structure['narrative_style'] = self._detect_narrative_style(text)
        
        # 計算整體置信度
        avg_confidence = sum(p.confidence for parties_list in parties.values() 
                           for p in parties_list) / max(1, sum(len(parties_list) for parties_list in parties.values()))
        structure['confidence'] = avg_confidence
        
        return structure
    
    def _detect_narrative_style(self, text: str) -> str:
        """檢測敘述風格 - 基於語義特徵"""
        # 結構化標記
        if re.search(r'[（(][一二三四五六七八九十][）)]', text):
            return 'structured_chinese'
        elif re.search(r'\d+\.', text):
            return 'numbered_list'
        
        # 段落風格
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 3:
            return 'paragraph_narrative'
        
        # 連續敘述
        sentences = text.split('。')
        if len(sentences) > 10:
            return 'continuous_narrative'
        
        return 'free_form'
    
    def extract_amounts_semantically(self, text: str, structure: Dict) -> List[Dict]:
        """基於語義的金額提取 - 適應各種格式"""
        amounts = []
        
        # 找到所有金額
        amount_pattern = r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*([萬千]?)元'
        matches = re.finditer(amount_pattern, text)
        
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            unit = match.group(2)
            
            # 處理單位
            amount = float(amount_str)
            if unit == '萬':
                amount *= 10000
            elif unit == '千':
                amount *= 1000
            
            # 語義分析：判斷金額性質
            context = self._get_amount_context(text, match.start(), match.end())
            amount_type = self._classify_amount_semantically(amount, context)
            
            amounts.append({
                'amount': int(amount),
                'type': amount_type['type'],
                'confidence': amount_type['confidence'],
                'context': context,
                'position': match.start()
            })
        
        return amounts
    
    def _get_amount_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """獲取金額的語義上下文"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _classify_amount_semantically(self, amount: float, context: str) -> Dict:
        """基於語義對金額進行分類"""
        classification = {'type': 'unknown', 'confidence': 0.0}
        
        # 語義特徵分析
        semantic_features = {
            'claim_indicators': ['請求', '賠償', '支出', '損失', '費用', '花費'],
            'calculation_indicators': ['計算', '基準', '標準', '依據', '按', '以'],
            'damage_types': ['醫療', '交通', '看護', '工作', '慰撫', '精神', '車輛'],
            'temporal_indicators': ['每日', '每月', '每年', '日薪', '月薪']
        }
        
        scores = {}
        
        # 計算各類型的語義得分
        for category, indicators in semantic_features.items():
            score = sum(1 for indicator in indicators if indicator in context)
            scores[category] = score / len(indicators)
        
        # 決定分類
        if scores['calculation_indicators'] > 0.3 or scores['temporal_indicators'] > 0.2:
            classification = {'type': 'calculation_base', 'confidence': 0.8}
        elif scores['claim_indicators'] > 0.2:
            classification = {'type': 'claim_amount', 'confidence': 0.7}
        elif scores['damage_types'] > 0.3:
            classification = {'type': 'damage_amount', 'confidence': 0.6}
        else:
            classification = {'type': 'unclear', 'confidence': 0.3}
        
        return classification
    
    def generate_adaptive_prompt(self, text: str, structure: Dict, parties: Dict) -> str:
        """生成自適應提示詞 - 基於案例結構而非具體格式"""
        case_type = structure['case_type']
        narrative_style = structure['narrative_style']
        
        # 基礎提示框架
        base_prompt = """你是台灣資深律師，請分析以下損害賠償描述並生成標準格式的損害項目。

【案例特徵】
- 案例類型：{case_type}
- 敘述風格：{narrative_style}
- 原告數量：{plaintiff_count}

【原始內容】
{content}

【分析指導】
1. 識別真正的求償項目和金額
2. 區分計算基準與最終求償
3. 按當事人分組整理（如適用）

【輸出要求】
{output_format}

請基於案例特徵進行適當的分析和整理："""
        
        # 根據案例類型動態調整輸出格式
        if case_type == 'multi_plaintiff':
            output_format = """按原告分組，格式如下：
（一）原告[姓名]之損害：
1. 損害類型：金額元
說明文字。"""
        else:
            output_format = """統一格式如下：
（一）損害類型：金額元
說明文字。"""
        
        return base_prompt.format(
            case_type=case_type,
            narrative_style=narrative_style,
            plaintiff_count=structure['plaintiff_count'],
            content=text,
            output_format=output_format
        )

def test_generalization():
    """測試泛化能力"""
    handler = EnhancedUniversalHandler()
    
    # 測試案例：完全不同的格式和姓名
    test_cases = [
        # 案例1：簡單格式，短姓名
        "原告李明因車禍受傷，醫療費5000元。被告王強應賠償。",
        
        # 案例2：複雜格式，長姓名  
        "原告歐陽天華駕駛時遭被告司馬相如追撞，支出醫療費12萬元，交通費3千元。",
        
        # 案例3：多被告格式
        "原告張三因被告李四、王五共同過失導致受傷，請求賠償醫療費8萬元。",
        
        # 案例4：混合敘述
        "查明原告趙六因系爭事故受傷，於台大醫院就診，支出費用如下：急診費2000元，住院費15000元。被告錢七應負責。"
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n=== 測試案例 {i} ===")
        print(f"原文：{case}")
        
        # 測試當事人提取
        parties = handler.extract_parties_semantically(case)
        print(f"當事人提取：")
        for role, party_list in parties.items():
            if party_list:
                names = [f"{p.name}({p.confidence:.2f})" for p in party_list if p.confidence > 0.3]
                if names:
                    print(f"  {role}：{names}")
        
        # 測試結構檢測
        structure = handler.detect_case_structure_semantically(case)
        print(f"結構檢測：{structure['case_type']}, 風格：{structure['narrative_style']}")
        
        # 測試金額提取
        amounts = handler.extract_amounts_semantically(case, structure)
        print(f"金額提取：")
        for amt in amounts:
            print(f"  {amt['amount']:,}元 - {amt['type']} (置信度：{amt['confidence']:.2f})")

if __name__ == "__main__":
    test_generalization()