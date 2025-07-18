#!/usr/bin/env python3
"""
通用格式處理器 - 處理各種用戶輸入格式
Universal Format Handler - Handles Various User Input Formats
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class DamageItem:
    """損害項目數據結構"""
    type: str          # 損害類型 (醫療, 交通, 看護等)
    amount: int        # 金額
    description: str   # 描述
    raw_text: str      # 原始文本
    confidence: float  # 置信度 (0-1)

class UniversalFormatHandler:
    """通用格式處理器 - 自動檢測和處理各種輸入格式"""
    
    def __init__(self):
        # 各種可能的格式模式
        self.format_patterns = {
            # 結構化格式：（一）項目：金額
            'structured_chinese': [
                r'^[（(][一二三四五六七八九十㈠㈡㈢㈣㈤㈥㈦㈧㈨㈩][）)]\s*([^：]+)：\s*([0-9,]+)\s*元',
                r'^[（(]\d+[）)]\s*([^：]+)：\s*([0-9,]+)\s*元'
            ],
            
            # 數字格式：1. 項目：金額
            'numbered_list': [
                r'^(\d+)[\.\s]\s*([^：]+)：\s*([0-9,]+)\s*元',
                r'^(\d+)[\.\s]\s*([^0-9]+)\s+([0-9,]+)\s*元'
            ],
            
            # 自由格式：在文本中提取 項目XX元
            'free_format': [
                r'([^。，；,;]*(?:醫療|交通|看護|工作|損失|慰撫|精神|車輛|維修|修復)[^。，；,;]*?)(?:共計|合計|為|支出|請求|賠償)?\s*([0-9,]+)\s*元',
                r'([^。，；,;]*(?:費用|支出|花費|損失|慰撫金)[^。，；,;]*?)(?:共計|合計|為|支出|請求|賠償)?\s*([0-9,]+)\s*元'
            ],
            
            # 段落格式：每段包含一個損害項目
            'paragraph_format': [
                r'([^。]+(?:費用|損失|慰撫金)[^。]*)\s*([0-9,]+)\s*元'
            ]
        }
        
        # 損害類型關鍵詞對應
        self.damage_type_keywords = {
            '醫療費用': ['醫療', '治療', '就醫', '醫院', '診所', '手術', '復健', '藥費'],
            '交通費用': ['交通', '車資', '計程車', '公車', '捷運', '往返', '就醫交通'],
            '看護費用': ['看護', '照護', '照顧', '護理', '陪伴'],
            '工作損失': ['工作', '勞動', '薪資', '收入', '工資', '無法工作', '請假', '休養'],
            '精神慰撫金': ['慰撫', '精神', '痛苦', '身心', '心理'],
            '車輛損失': ['車輛', '機車', '汽車', '修復', '維修', '修理', '貶值'],
            '醫療器材': ['器材', '輔具', '輪椅', '助行器', '拐杖', '護具'],
            '其他費用': ['費用', '支出', '花費', '損失']
        }
        
        # 計算基準關鍵詞 (需要排除的)
        self.calculation_base_keywords = [
            '基本工資', '月薪', '日薪', '時薪', '薪資標準',
            '計算基準', '作為基準', '月工資應?為\\d+[,\\d]*元', '每月工資\\d+[,\\d]*元',
            '每日\\d+[,\\d]*元', '每月\\d+[,\\d]*元', '每年\\d+[,\\d]*元'
        ]
    
    def detect_format(self, text: str) -> Dict[str, any]:
        """檢測輸入文本的格式類型"""
        results = {
            'primary_format': None,
            'confidence': 0.0,
            'detected_formats': [],
            'structure_info': {},
            'is_multi_plaintiff': False,
            'plaintiff_count': 1
        }
        
        lines = text.strip().split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # 檢測多原告模式 - 修正錯誤判斷邏輯
        plaintiff_mentions = []
        for line in non_empty_lines:
            # 只匹配明確的原告姓名模式：原告[姓名]，原告[姓名]、原告[姓名]等
            # 必須是具體姓名，而非形容詞或動詞後的詞語
            plaintiff_matches = re.findall(r'原告([A-Za-z\u4e00-\u9fff]{2,4})(?=[，、；。\s]|$)', line)
            # 進一步過濾：排除常見的非姓名詞語
            excluded_terms = {'主張', '因此', '受傷', '因本', '為大', '所受', '後續', '需專', '出院', '住院'}
            valid_matches = [match for match in plaintiff_matches if match not in excluded_terms]
            plaintiff_mentions.extend(valid_matches)
        
        # 去重並計算原告數量 - 如果沒有明確姓名，視為單原告
        unique_plaintiffs = list(set(plaintiff_mentions))
        is_multi_plaintiff = len(unique_plaintiffs) > 1
        
        results['is_multi_plaintiff'] = is_multi_plaintiff
        results['plaintiff_count'] = len(unique_plaintiffs)
        
        format_scores = {}
        
        # 特殊處理：多原告案例
        if is_multi_plaintiff:
            # 檢查是否為多原告分段描述格式
            multi_plaintiff_score = 0
            for plaintiff in unique_plaintiffs:
                plaintiff_sections = len([line for line in non_empty_lines 
                                        if f'原告{plaintiff}' in line])
                if plaintiff_sections > 1:  # 該原告有多段描述
                    multi_plaintiff_score += 2
                else:
                    multi_plaintiff_score += 1
            
            format_scores['multi_plaintiff_narrative'] = {
                'score': multi_plaintiff_score,
                'confidence': min(multi_plaintiff_score / (len(unique_plaintiffs) * 2), 1.0),
                'matches': len(unique_plaintiffs)
            }
        
        # 檢測各種格式
        for format_name, patterns in self.format_patterns.items():
            score = 0
            matches = 0
            
            for line in non_empty_lines:
                for pattern in patterns:
                    if re.search(pattern, line):
                        matches += 1
                        score += 1.0
            
            if matches > 0:
                # 計算格式置信度
                confidence = min(matches / len(non_empty_lines), 1.0)
                format_scores[format_name] = {
                    'score': score,
                    'confidence': confidence,
                    'matches': matches
                }
        
        # 確定主要格式
        if format_scores:
            primary_format = max(format_scores.keys(), 
                               key=lambda x: format_scores[x]['confidence'])
            results['primary_format'] = primary_format
            results['confidence'] = format_scores[primary_format]['confidence']
            results['detected_formats'] = list(format_scores.keys())
            results['structure_info'] = format_scores
        
        return results
    
    def extract_damage_items(self, text: str) -> List[DamageItem]:
        """通用損害項目提取 - 適應各種格式"""
        format_info = self.detect_format(text)
        primary_format = format_info.get('primary_format')
        is_multi_plaintiff = format_info.get('is_multi_plaintiff', False)
        plaintiff_count = format_info.get('plaintiff_count', 1)
        
        print(f"🔍 檢測到主要格式: {primary_format} (置信度: {format_info['confidence']:.2f})")
        if is_multi_plaintiff:
            print(f"🔍 檢測到多原告案例: {plaintiff_count}名原告")
        
        damage_items = []
        
        # 特殊處理多原告案例
        if is_multi_plaintiff and primary_format == 'multi_plaintiff_narrative':
            damage_items = self._extract_multi_plaintiff_damages(text, format_info)
        elif primary_format and format_info['confidence'] > 0.3:
            # 使用檢測到的格式進行提取
            damage_items = self._extract_by_format(text, primary_format)
        
        # 如果結構化提取失敗或結果不足，使用混合策略
        # 修改條件：總是使用混合策略補充，然後通過去重來處理重複項目
        print("🔄 使用混合提取策略補充小額金額")
        mixed_items = self._extract_by_mixed_strategy(text)
        damage_items.extend(mixed_items)
        
        # 去重和合併相似項目
        damage_items = self._deduplicate_items(damage_items)
        
        # 排除計算基準項目
        damage_items = self._filter_calculation_bases(damage_items)
        
        return damage_items
    
    def _extract_by_format(self, text: str, format_type: str) -> List[DamageItem]:
        """根據特定格式提取損害項目"""
        items = []
        patterns = self.format_patterns.get(format_type, [])
        
        # 首先嘗試中文數字混合格式（高優先級）
        items.extend(self._extract_chinese_number_amounts(text))
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    groups = match.groups()
                    
                    if format_type in ['structured_chinese', 'numbered_list']:
                        if len(groups) >= 2:
                            if format_type == 'numbered_list':
                                item_desc = groups[1].strip()
                                amount_str = groups[2].strip()
                            else:
                                item_desc = groups[0].strip()
                                amount_str = groups[1].strip()
                    else:
                        if len(groups) >= 2:
                            item_desc = groups[0].strip()
                            amount_str = groups[1].strip()
                        else:
                            continue
                    
                    try:
                        amount = int(amount_str.replace(',', ''))
                        if amount >= 10:  # 降低門檻以包含小額費用  # 排除小額
                            damage_type = self._classify_damage_type(item_desc)
                            items.append(DamageItem(
                                type=damage_type,
                                amount=amount,
                                description=item_desc,
                                raw_text=line,
                                confidence=0.8
                            ))
                    except ValueError:
                        continue
        
        return items
    
    def _extract_chinese_number_amounts(self, text: str) -> List[DamageItem]:
        """專門提取中文數字混合格式金額（如：5萬4,741元）"""
        items = []
        
        chinese_number_patterns = [
            r'(\d+)萬(\d{1,4}(?:,\d{3})*)\s*元',  # 5萬4,741元、2萬0,900元
            r'(\d+)萬\s*元',  # 18萬元、42萬元、99萬元
            r'(\d+)千(\d{1,3})\s*元'  # 3千500元
        ]
        
        for pattern in chinese_number_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    if '萬' in match.group(0):
                        if len(match.groups()) == 2 and match.group(2):
                            # 如：5萬4,741元
                            wan_part = int(match.group(1)) * 10000
                            digit_part_str = match.group(2).replace(',', '')  # 移除逗號
                            digit_part = int(digit_part_str)
                            amount = wan_part + digit_part
                        else:
                            # 如：18萬元
                            amount = int(match.group(1)) * 10000
                    elif '千' in match.group(0):
                        # 如：3千500元
                        qian_part = int(match.group(1)) * 1000
                        digit_part = int(match.group(2)) if match.group(2) else 0
                        amount = qian_part + digit_part
                    else:
                        continue
                    
                    if amount >= 10:  # 降低門檻以包含小額費用
                        # 分析上下文 - 增加檢查範圍以確保包含完整信息
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context = text[start:end]
                        
                        damage_type = self._classify_damage_type(context)
                        items.append(DamageItem(
                            type=damage_type,
                            amount=amount,
                            description=f"中文數字格式: {context[:30]}...",
                            raw_text=match.group(0),
                            confidence=0.9
                        ))
                except (ValueError, AttributeError):
                    continue
        
        return items
    
    def _extract_by_mixed_strategy(self, text: str) -> List[DamageItem]:
        """混合策略提取 - 當格式檢測失敗時使用"""
        items = []
        
        # 策略1: 使用正規表達式提取所有可能的金額和描述
        amount_patterns = [
            r'([^。，；\n]*(?:費用|損失|慰撫金|支出|花費|賠償)[^。，；\n]*?)(?:為|支出|請求|賠償)?\s*([0-9,]+)\s*元',
            r'([^。，；\n]*(?:醫療|交通|看護|工作|車輛|精神)[^。，；\n]*?)(?:為|支出|請求|賠償)?\s*([0-9,]+)\s*元'
        ]
        
        for pattern in amount_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                desc = match.group(1).strip()
                amount_str = match.group(2).strip()
                
                # 排除包含總和關鍵詞的項目
                if any(keyword in desc for keyword in ['共計', '合計', '總計', '小計', '計']):
                    continue
                
                try:
                    amount = int(amount_str.replace(',', ''))
                    if amount >= 10:  # 降低門檻以包含小額費用
                        damage_type = self._classify_damage_type(desc)
                        items.append(DamageItem(
                            type=damage_type,
                            amount=amount,
                            description=desc,
                            raw_text=match.group(0),
                            confidence=0.6
                        ))
                except ValueError:
                    continue
        
        # 策略2: 中文數字混合格式提取（如：5萬4,741元、18萬元、2萬0,900元）
        chinese_number_patterns = [
            r'(\d+)萬(\d{1,4}(?:,\d{3})*)\s*元',  # 5萬4,741元、2萬0,900元
            r'(\d+)萬\s*元',  # 18萬元
            r'(\d+)千(\d{1,3})\s*元'  # 3千500元
        ]
        
        for pattern in chinese_number_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    if '萬' in match.group(0):
                        if len(match.groups()) == 2 and match.group(2):
                            # 如：5萬4,741元
                            wan_part = int(match.group(1)) * 10000
                            digit_part_str = match.group(2).replace(',', '')  # 移除逗號
                            digit_part = int(digit_part_str)
                            amount = wan_part + digit_part
                        else:
                            # 如：18萬元
                            amount = int(match.group(1)) * 10000
                    elif '千' in match.group(0):
                        # 如：3千500元
                        qian_part = int(match.group(1)) * 1000
                        digit_part = int(match.group(2)) if match.group(2) else 0
                        amount = qian_part + digit_part
                    else:
                        continue
                    
                    if amount >= 10:  # 降低門檻以包含小額費用
                        # 分析上下文
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context = text[start:end]
                        
                        if self._has_damage_keywords(context):
                            damage_type = self._classify_damage_type(context)
                            items.append(DamageItem(
                                type=damage_type,
                                amount=amount,
                                description=f"中文數字混合: {context[:50]}...",
                                raw_text=match.group(0),
                                confidence=0.8
                            ))
                except (ValueError, AttributeError):
                    continue
        
        # 策略3: 簡單的金額提取 + 上下文分析
        simple_amounts = re.finditer(r'([0-9,]+)\s*元', text)
        for match in simple_amounts:
            amount_str = match.group(1)
            try:
                amount = int(amount_str.replace(',', ''))
                if amount < 10:  # 降低門檻以包含小額費用
                    continue
                
                # 分析上下文
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]
                
                # 更精確的總和判斷：檢查金額是否直接跟在總和關鍵詞後面
                amount_in_text = f"{amount_str}元"
                is_total_amount = False
                for keyword in ['共計', '合計', '總計', '小計']:
                    if keyword + amount_in_text in context or keyword + " " + amount_in_text in context:
                        is_total_amount = True
                        break
                
                if is_total_amount:
                    continue
                
                # 檢查是否包含損害相關關鍵詞
                if self._has_damage_keywords(context):
                    damage_type = self._classify_damage_type(context)
                    items.append(DamageItem(
                        type=damage_type,
                        amount=amount,
                        description=f"提取自上下文: {context[:50]}...",
                        raw_text=context,
                        confidence=0.4
                    ))
            except ValueError:
                continue
        
        return items
    
    def _classify_damage_type(self, text: str) -> str:
        """分類損害類型"""
        text_lower = text.lower()
        
        for damage_type, keywords in self.damage_type_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return damage_type
        
        return '其他費用'
    
    def _has_damage_keywords(self, text: str) -> bool:
        """檢查文本是否包含損害相關關鍵詞"""
        damage_keywords = []
        for keywords in self.damage_type_keywords.values():
            damage_keywords.extend(keywords)
        
        return any(keyword in text for keyword in damage_keywords)
    
    def _deduplicate_items(self, items: List[DamageItem]) -> List[DamageItem]:
        """去重和合併相似項目 - 改進版本"""
        if not items:
            return items
        
        # 按金額分組，優先選擇高置信度項目
        amount_groups = {}
        for item in items:
            if item.amount not in amount_groups:
                amount_groups[item.amount] = []
            amount_groups[item.amount].append(item)
        
        deduplicated = []
        processed_amounts = set()
        
        # 優先處理中文數字格式（高置信度）
        for item in sorted(items, key=lambda x: x.confidence, reverse=True):
            if item.amount in processed_amounts:
                continue
                
            # 檢查是否是其他金額的一部分 - 改進版本
            is_partial = False
            for other_item in items:
                if other_item.amount != item.amount and other_item.amount > item.amount:
                    # 更精確的檢查：只有當小金額確實是大金額的後綴部分時才認為是重複
                    # 例如：4741 是 54741 的一部分，但 50 不是 5000 的一部分
                    item_str = str(item.amount)
                    other_str = str(other_item.amount)
                    
                    # 只有當小金額是大金額的後綴且前面有足夠的數字時才認為是部分
                    if (other_str.endswith(item_str) and 
                        len(other_str) > len(item_str) and
                        len(item_str) >= 3):  # 只對3位數以上的金額進行此檢查
                        # 進一步檢查：確保不是巧合的重複（如50與5000）
                        if len(other_str) == len(item_str) + 1:
                            # 如果只是多一位數，可能是不同的金額（如50vs500）
                            continue
                        is_partial = True
                        print(f"🔍 【去重】{item.amount}元 被視為 {other_item.amount}元 的一部分")
                        break
            
            if not is_partial:
                deduplicated.append(item)
                processed_amounts.add(item.amount)
        
        return deduplicated
    
    def _filter_calculation_bases(self, items: List[DamageItem]) -> List[DamageItem]:
        """過濾計算基準項目"""
        filtered = []
        
        for item in items:
            is_calculation_base = False
            
            # 檢查當前金額本身是否是計算基準
            # 檢查多種金額格式：帶逗號和不帶逗號的
            amount_str_with_comma = f"{item.amount:,}元"
            amount_str_no_comma = f"{item.amount}元"
            
            prefix_context = item.description  # 默認使用描述
            
            # 先嘗試在原始文本中找到金額位置 - 擴大檢查範圍
            full_text = item.raw_text if hasattr(item, 'raw_text') and item.raw_text else ""
            
            for amount_format in [amount_str_with_comma, amount_str_no_comma]:
                if amount_format in full_text:
                    pos = full_text.find(amount_format)
                    # 檢查金額前面的100個字符（增加檢查範圍）
                    prefix_start = max(0, pos - 100)
                    prefix_context = full_text[prefix_start:pos + len(amount_format)]
                    break
                # 也檢查描述中是否包含金額
                elif amount_format in item.description:
                    # 如果在描述中找到金額，使用描述作為上下文
                    prefix_context = item.description
            
            # 另外檢查描述文本
            if item.description and len(item.description) > len(prefix_context):
                prefix_context = item.description
            
            # 檢查金額前面是否直接包含計算基準關鍵詞 - 增強版
            calculation_base_indicators = [
                '每個月月薪', '月薪', '日薪', '時薪', '基本工資',
                '每日照護費用', '每日.*作為計算基準', '作為計算基準',
                '每月.*計算', '依每月.*計算', '每月.*減少',
                '勞動能力.*減少', '勞動能力.*損失.*計算',
                '每月工資.*為', '月工資.*為', '每日.*元作為計算基準'
            ]
            
            # 精確檢查：金額是否直接跟在基準詞後面
            for base_keyword in calculation_base_indicators:
                # 使用正則表達式進行更精確的匹配
                import re as regex_module
                if '.*' in base_keyword:
                    # 正則表達式模式
                    if regex_module.search(base_keyword, prefix_context):
                        is_calculation_base = True
                        print(f"🔍 【排除計算基準】{item.amount:,}元 - 匹配正則模式: {base_keyword}")
                        break
                else:
                    # 精確文本匹配
                    if base_keyword in prefix_context:
                        base_pos = prefix_context.find(base_keyword)
                        
                        # 檢查多種金額格式
                        amount_patterns = [
                            f'{item.amount:,}元',
                            f'{item.amount}元',
                            item.raw_text  # 原始中文數字格式如「7萬2,800元」
                        ]
                        
                        amount_pos = -1
                        for pattern in amount_patterns:
                            pos = prefix_context.find(pattern)
                            if pos != -1:
                                amount_pos = pos
                                break
                        
                        if amount_pos > base_pos and (amount_pos - base_pos) < 30:  # 增加距離到30字符
                            # 進一步檢查：基準詞和金額之間不應該有明確的求償詞
                            between_text = prefix_context[base_pos:amount_pos]
                            # 排除明確的求償動詞，但保留描述性詞語
                            exclusion_words = ['請求', '賠償', '支出', '受有', '損失為', '共計']
                            has_exclusion = any(word in between_text for word in exclusion_words)
                            
                            # 特殊情況：如果包含"作為計算基準"則強制認定為計算基準
                            if '作為計算基準' in prefix_context:
                                has_exclusion = False
                            
                            if not has_exclusion:
                                is_calculation_base = True
                                print(f"🔍 【排除計算基準】{item.amount:,}元 - 匹配關鍵詞: {base_keyword}")
                                break
            
            # 特殊檢查：如果金額後面緊跟"計算"
            if f"{item.amount}元計算" in prefix_context.replace(',', ''):
                is_calculation_base = True
            
            if not is_calculation_base:
                filtered.append(item)
            else:
                print(f"🔍 【排除計算基準】{item.amount:,}元 - {item.description[:30]}...")
        
        return filtered
    
    def _extract_multi_plaintiff_damages(self, text: str, format_info: dict) -> List[DamageItem]:
        """專門處理多原告案例的損害提取"""
        items = []
        
        # 從format_info中獲取原告列表（如果可用）
        plaintiff_mentions = []
        for line in text.split('\n'):
            plaintiff_matches = re.findall(r'原告([^，、。\s]+)', line)
            plaintiff_mentions.extend(plaintiff_matches)
        
        unique_plaintiffs = list(set(plaintiff_mentions))
        print(f"🔍 【多原告處理】發現原告: {unique_plaintiffs}")
        
        # 為每個原告分別提取損害項目
        for plaintiff in unique_plaintiffs:
            plaintiff_text = ""
            
            # 提取該原告的相關文本
            for line in text.split('\n'):
                if f'原告{plaintiff}' in line:
                    plaintiff_text += line + "\n"
            
            if plaintiff_text:
                print(f"🔍 【多原告處理】處理原告{plaintiff}的損害")
                # 使用混合策略提取該原告的損害
                plaintiff_items = self._extract_by_mixed_strategy(plaintiff_text)
                
                # 為每個項目標記原告
                for item in plaintiff_items:
                    item.description = f"原告{plaintiff}: {item.description}"
                    items.append(item)
        
        return items
    
    def format_output(self, items: List[DamageItem], style: str = 'structured') -> str:
        """格式化輸出"""
        if not items:
            return ""
        
        if style == 'structured':
            return self._format_structured(items)
        elif style == 'simple':
            return self._format_simple(items)
        else:
            return self._format_natural(items)
    
    def _format_structured(self, items: List[DamageItem]) -> str:
        """結構化格式輸出"""
        output_lines = []
        chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        
        for i, item in enumerate(items):
            if i < len(chinese_nums):
                num = chinese_nums[i]
            else:
                num = str(i + 1)
            
            output_lines.append(f"（{num}）{item.type}：{item.amount:,}元")
            if item.description and len(item.description) > 5:
                # 清理描述，移除重複的金額信息
                clean_desc = re.sub(r'\d+[,\d]*\s*元', '', item.description).strip()
                if clean_desc:
                    output_lines.append(f"原告因本次事故{clean_desc}。")
            output_lines.append("")
        
        return '\n'.join(output_lines)
    
    def _format_simple(self, items: List[DamageItem]) -> str:
        """簡單格式輸出"""
        output_lines = []
        for item in items:
            output_lines.append(f"{item.type}：{item.amount:,}元")
        return '\n'.join(output_lines)
    
    def _format_natural(self, items: List[DamageItem]) -> str:
        """自然語言格式輸出"""
        if not items:
            return ""
        
        parts = []
        for item in items:
            parts.append(f"{item.type}{item.amount:,}元")
        
        total = sum(item.amount for item in items)
        
        return f"請求賠償{('、'.join(parts))}，總計{total:,}元。"

def test_universal_handler():
    """測試通用格式處理器"""
    handler = UniversalFormatHandler()
    
    # 測試用例1: 結構化格式
    test1 = """
（一）醫療費用：43,795元
原告因本次事故受傷，於慈濟醫院神經外科、身心科就醫治療，支出醫療費用共計43,795元。
（二）交通費：9,600元
原告因本次事故導致行動不便，自110年5月14日至111年8月2日就醫產生交通費用共計9,600元。
（三）醫療器材：6,000元
原告因本次事故步態不穩，需輔助行動，購買輪椅、助行器支出共計6,000元。
    """
    
    # 測試用例2: 自由格式（你的新案例）
    test2 = """
原告主張其因丁○○上開過失行為，支出醫療及就診交通費用合計255830元，並有聯新國際醫院（下稱聯新醫院）診斷證明書為證。另按親屬間之看護應比照一般看護情形，認被害人受有相當於看護費之損害，命加害人賠償；又按聯新醫院於110年3月18日出具之診斷證明書記載：「……，於民國111年7月13日06：44入急診就醫治療，……於民國111年8月25日出院，共住院3日，09月01日門診追蹤治療，宜休養3個月」，故原告於入院期間（111年7月13日至111年7月15日）需專人照顧，又原告受脊椎間盤部分切除及神經減壓手術，以及自111年9月1日起算3個月，合計4.5月有看護之必要，以每日2000元作為計算基準，共請求270000元。又原告自111年7月13日至111年11月30日共4.5月期間無法工作，請假在家休養，無法工作，以111年度每月基本工資25250元計算，受有之薪資損失為113625元。原告因上開車禍事故，受有左側肩膀挫傷、左側前胸壁挫傷、下背和骨盆挫傷及第4、5腰椎第1薦椎椎間盤破裂伴有神經根壓迫之傷害，則原告受有身體及精神痛苦，堪可認定，是原告請求被告賠償慰撫金300000元。
    """
    
    # 測試用例3: 數字列表格式
    test3 = """
1. 醫療費用：182,690元
2. 看護費用：246,000元
3. 交通費用：10,380元
4. 醫療用品費用：4,464元
5. 無法工作損失：485,000元
6. 精神慰撫金：1,559,447元
    """
    
    test_cases = [
        ("結構化格式", test1),
        ("自由格式", test2),
        ("數字列表格式", test3)
    ]
    
    for name, test_text in test_cases:
        print(f"\n{'='*60}")
        print(f"測試案例: {name}")
        print(f"{'='*60}")
        
        # 檢測格式
        format_info = handler.detect_format(test_text)
        print(f"檢測結果: {format_info}")
        
        # 提取損害項目
        items = handler.extract_damage_items(test_text)
        print(f"\n提取到 {len(items)} 個損害項目:")
        for item in items:
            print(f"- {item.type}: {item.amount:,}元 (置信度: {item.confidence:.2f})")
        
        # 格式化輸出
        formatted = handler.format_output(items, 'structured')
        print(f"\n結構化輸出:\n{formatted}")
        
        total = sum(item.amount for item in items)
        print(f"總計: {total:,}元")

if __name__ == "__main__":
    test_universal_handler()