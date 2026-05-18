#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡潔版起訴書生成器
專注於核心功能：多原告損害項目生成
"""

import re
import json
import subprocess
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DamageItem:
    """損害項目數據結構"""
    amount: int
    category: str
    description: str
    context: str


@dataclass
class PlaintiffDamage:
    """原告損害數據結構"""
    name: str
    items: List[DamageItem]
    total: int


class SimpleIndictmentGenerator:
    """簡潔版起訴書生成器"""
    
    def __init__(self, use_llm_formatting: bool = True, model_name: str = "llama3.1"):
        self.model_name = model_name
        
        # 檢查LLM服務可用性
        if use_llm_formatting:
            if self._check_ollama_availability():
                self.use_llm_formatting = True
                print(f"✅ Ollama服務已就緒，將使用{model_name}進行格式化優化")
            else:
                self.use_llm_formatting = False
                print("⚠️  Ollama服務不可用，將跳過LLM格式化")
        else:
            self.use_llm_formatting = False
        
        # 增強的分類關鍵詞系統（基於RAG系統優化）
        self.category_keywords = {
            # 醫療相關類別 - 按嚴重程度和類型細分
            '急救醫療費用': ['急救', '急診', '緊急', '救護車', '急救室', 'ER'],
            '手術費用': ['手術', '開刀', '麻醉', '手術室', '術後', '手術治療'],
            '住院費用': ['住院', '病房', '住院治療', '病床', '住院期間'],
            '門診醫療費用': ['門診', '看診', '診療', '診察', '複診', '回診'],
            '復健費用': ['復健', '物理治療', '職能治療', '語言治療', '針灸', '按摩'],
            '檢查費用': ['檢查', 'X光', 'CT', 'MRI', '斷層', '超音波', '抽血', '檢驗'],
            '藥品費用': ['藥品', '藥物', '醫藥費', '處方', '用藥', '藥費'],
            '預估醫療費用': ['預估醫療', '未來醫療', '預估', '未來', '後續醫療', '持續治療'],
            '醫療用品費用': ['醫療用品', '醫療器材', '輔具', '義肢', '拐杖', '輪椅', '支架'],
            
            # 牙科專門類別
            '牙齒治療費用': ['牙齒治療', '補牙', '根管', '牙周', '拔牙', '洗牙'],
            '假牙費用': ['假牙', '植牙', '牙套', '牙冠', '牙橋', '全口假牙'],
            
            # 照護類別
            '專業看護費用': ['專業看護', '看護師', '護理師', '醫護人員'],
            '家庭看護費用': ['家庭看護', '居家照護', '看護費用', '看護', '照護', '協助', '照顾'],
            '陪伴費用': ['陪伴', '陪同', '家屬陪伴', '陪護'],
            
            # 車輛損害類別
            '車輛修復費用': ['車輛修復', '修復費用', '修理', '修復', '維修'],
            '車輛零件費用': ['零件', '配件', '更換', '零組件'],
            '拖吊費用': ['拖吊', '救援', '拖車', '吊車'],
            '車輛檢驗費用': ['檢驗', '驗車', '檢測', '鑑定'],
            
            # 收入損失類別  
            '薪資損失': ['薪資損失', '工資損失', '薪水損失', '月薪', '底薪'],
            '營業損失': ['營業損失', '生意損失', '收入損失', '營收'],
            '工作能力減損': ['工作能力', '勞動能力', '能力減損', '殘廢', '失能'],
            '請假損失': ['請假', '病假', '事假', '無薪假', '停工'],
            
            # 交通相關類別
            '就醫交通費': ['就醫', '看病', '復診', '治療', '往返醫院'],
            '一般交通費用': ['交通費用', '往返', '車資', '油資', '過路費'],
            '計程車費用': ['計程車', 'taxi', '叫車', '車費'],
            
            # 精神損害類別
            '精神慰撫金': ['慰撫金', '慰撫', '精神', '痛苦', '身心', '精神慰撫金', '精神損害'],
            '身體痛苦': ['身體痛苦', '疼痛', '不適', '痛楚'],
            '生活品質降低': ['生活品質', '品質降低', '生活不便', '行動不便'],
            
            # 其他費用類別
            '營養費用': ['營養', '補品', '營養品', '保健'],
            '文件費用': ['文件', '證明', '診斷書', '報告書', '鑑定書'],
            '訴訟費用': ['訴訟', '律師', '法院', '訴訟費'],
            '其他費用': ['費用', '支出', '花費', '開銷', '雜費', '其他']
        }
        
        # 學習RAG系統：有效求償關鍵詞
        self.valid_claim_keywords = [
            '費用', '損失', '慰撫金', '賠償', '支出', '花費',
            '醫療', '修復', '修理', '交通', '看護', '手術',
            '假牙', '復健', '治療', '工作收入', '預估', '未來'
        ]
        
        # 學習RAG系統：排除關鍵詞
        self.exclude_keywords = [
            '日薪', '年度所得', '月收入', '總計', '合計', '小計',
            '證據', '收據', '發票', '可證', '每月薪資', '月薪為',
            '以每月', '以每日', '計算基礎'
        ]
    
    def generate_indictment(self, input_text: str) -> str:
        """主要生成函數"""
        try:
            print("📝 開始生成起訴書...")
            
            # 1. 提取基本信息
            accident_origin = self._extract_accident_origin(input_text)
            legal_basis = self._generate_legal_basis()
            
            # 2. 解析損害項目
            plaintiffs = self._extract_plaintiffs(input_text)
            damage_items = self._extract_damage_items(input_text)
            
            # 3. 智能分配項目到原告
            plaintiff_damages = self._assign_damages_to_plaintiffs(
                plaintiffs, damage_items, input_text
            )
            
            # 4. 生成完整起訴書
            indictment = self._build_indictment(
                accident_origin, legal_basis, plaintiff_damages
            )
            
            # 5. 可選的LLM格式化優化
            if self.use_llm_formatting:
                print("🎨 開始LLM格式化優化...")
                try:
                    formatted_indictment = self._format_with_llm(indictment)
                    if formatted_indictment:
                        indictment = formatted_indictment
                        print("✅ LLM格式化完成")
                    else:
                        print("⚠️  LLM格式化失敗，使用原始版本")
                except Exception as e:
                    print(f"⚠️  LLM格式化錯誤: {e}，使用原始版本")
            
            print("✅ 起訴書生成完成")
            return indictment
            
        except Exception as e:
            print(f"❌ 生成失敗: {e}")
            return f"生成失敗: {str(e)}"
    
    def _extract_accident_origin(self, text: str) -> str:
        """提取事故緣由"""
        # 查找事故緣由段落
        patterns = [
            r'一、事故發生緣由[：:]?\s*(.*?)(?=二、|三、|$)',
            r'一、(緣.*?)(?=二、|三、|$)',
            r'(緣.*?)(?=二、|三、|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                origin = match.group(1).strip()
                if origin and len(origin) > 10:  # 確保不是空的
                    if not origin.startswith('緣'):
                        origin = f"緣{origin}"
                    return origin
        
        return "緣被告駕駛車輛發生交通事故，應負賠償責任。"
    
    def _generate_legal_basis(self) -> str:
        """生成法律依據"""
        return """二、按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」、「汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。」、「不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。」、「不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。」民法第184條第1項前段、民法第191條之2、民法第193條第1項、民法第195條第1項前段分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任："""
    
    def _extract_plaintiffs(self, text: str) -> List[str]:
        """提取原告姓名"""
        plaintiffs = []
        
        # 1. 優先查找匿名化姓名（如甲○○○）
        special_pattern = r'原告([甲乙丙丁戊己庚辛壬癸][○〇０0][○〇０0][○〇０0]?)'
        special_matches = re.findall(special_pattern, text)
        for name in special_matches:
            if name not in plaintiffs:
                plaintiffs.append(name)
        
        # 2. 專門提取段落標題中的原告（這最準確）
        section_pattern = r'（[一二三四五]）原告([\u4e00-\u9fff○〇０0]{2,4})部分'
        section_matches = re.findall(section_pattern, text)
        for name in section_matches:
            if name not in plaintiffs and len(name) >= 2:
                plaintiffs.append(name)
        
        # 3. 如果從段落標題沒找到，嘗試其他方法
        if not plaintiffs:
            # 匿名姓名模式（更寬鬆）
            anonymous_pattern = r'原告([甲乙丙丁戊己庚辛壬癸][○〇０0]*)'
            anonymous_matches = re.findall(anonymous_pattern, text)
            for name in anonymous_matches:
                if name not in plaintiffs and len(name) >= 2:
                    plaintiffs.append(name)
            
            # 常見姓名模式
            common_names = ['陳慶華', '朱庭慧', '王小明', '李美麗', '張志強']
            for name in common_names:
                if f'原告{name}' in text and name not in plaintiffs:
                    plaintiffs.append(name)
            
            # 如果還是沒找到，使用保守的正則
            if not plaintiffs:
                # 只匹配緊跟在"原告"後面且後面有"因"、"駕駛"等動詞的姓名
                pattern = r'原告([\u4e00-\u9fff○〇０0]{2,4})(?=因|駕駛|於|搭載|騎乘)'
                matches = re.findall(pattern, text)
                for name in matches:
                    # 過濾掉明顯不是姓名的詞
                    invalid_names = ['損害', '痛苦', '部分', '受傷', '治療', '車禍', '受有', '則受', '兩人', '等傷', '情形']
                    if name not in invalid_names and name not in plaintiffs:
                        plaintiffs.append(name)
        
        # 如果找到的原告數量異常，只保留前兩個最可能的
        if len(plaintiffs) > 2:
            # 優先保留在段落標題中出現的
            valid_plaintiffs = []
            for name in plaintiffs:
                if f'原告{name}部分' in text:
                    valid_plaintiffs.append(name)
            
            if len(valid_plaintiffs) >= 2:
                plaintiffs = valid_plaintiffs[:2]
            else:
                plaintiffs = plaintiffs[:2]
        
        print(f"🔍 識別到原告: {plaintiffs}")
        return plaintiffs
    
    def _extract_damage_items(self, text: str) -> List[DamageItem]:
        """提取所有損害項目"""
        damage_items = []
        
        # 改進的金額提取邏輯 - 處理中文數字混合
        potential_amounts = []
        
        # 1. 先處理中文數字混合格式（如：2萬0185元、32萬4000元）
        chinese_mixed_pattern = r'(\d+)萬(\d+)元'
        for match in re.finditer(chinese_mixed_pattern, text):
            wan_part = int(match.group(1))
            yuan_part = int(match.group(2))
            amount = wan_part * 10000 + yuan_part
            potential_amounts.append((amount, match.start(), match.end()))
        
        # 2. 處理純中文數字（如：三萬元、30萬元）
        chinese_pattern = r'(\d+萬元|[一二三四五六七八九十]+萬元)'
        for match in re.finditer(chinese_pattern, text):
            chinese_str = match.group(1)
            if chinese_str[0].isdigit():
                # 處理如"30萬元"的格式
                num = int(chinese_str.split('萬')[0])
                amount = num * 10000
            else:
                # 處理純中文數字
                chinese_num = chinese_str.replace('萬元', '')
                amount = self._chinese_to_number(chinese_num) * 10000
            
            if amount >= 1000:
                potential_amounts.append((amount, match.start(), match.end()))
        
        # 3. 處理普通數字格式
        amount_pattern = r'(\d{1,3}(?:,\d{3})*|\d+)元'
        for match in re.finditer(amount_pattern, text):
            amount_str = match.group(1).replace(',', '')
            amount = int(amount_str)
            
            # 跳過太小的金額（可能是年份、日期等）
            if amount < 1000:
                continue
            
            # 獲取更大範圍的上下文來判斷
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(text), match.end() + 100)
            extended_context = text[start_pos:end_pos]
            
            # 跳過計算基礎
            if self._is_calculation_base(extended_context):
                print(f"⚠️  跳過計算基礎: {amount:,}元")
                continue
            
            potential_amounts.append((amount, match.start(), match.end()))
        
        # 去除重疊的金額（保留更大的金額）
        filtered_amounts = self._remove_overlapping_amounts(potential_amounts, text)
        
        # 對每個有效金額創建損害項目
        for amount, start_pos, end_pos in filtered_amounts:
            # 提取精確的上下文
            precise_context = self._get_precise_context(text, amount, start_pos)
            
            # 分類
            category = self._classify_amount(precise_context)
            
            damage_items.append(DamageItem(
                amount=amount,
                category=category,
                description=precise_context,
                context=precise_context
            ))
        
        print(f"🔍 提取到 {len(damage_items)} 個損害項目")
        for item in damage_items:
            print(f"  {item.amount:,}元 - {item.category} - {item.description[:50]}...")
        
        return damage_items
    
    def _remove_overlapping_amounts(self, amounts: List[Tuple[int, int, int]], text: str) -> List[Tuple[int, int, int]]:
        """移除重疊或包含關係的金額，保留最合理的"""
        if not amounts:
            return []
        
        # 先按位置排序，便於檢查重疊
        amounts.sort(key=lambda x: x[1])
        
        filtered = []
        used_amounts = set()  # 追蹤已使用的金額
        
        for amount, start, end in amounts:
            # 檢查這個金額是否已經被使用
            if amount in used_amounts:
                print(f"⚠️  跳過重複金額: {amount:,}元")
                continue
            
            # 檢查是否與已選擇的金額範圍重疊（位置上）
            overlaps = False
            for _, used_start, used_end in filtered:
                # 如果位置重疊超過50%，認為是重疊
                overlap_start = max(start, used_start)
                overlap_end = min(end, used_end)
                if overlap_end > overlap_start:
                    overlap_ratio = (overlap_end - overlap_start) / min(end - start, used_end - used_start)
                    if overlap_ratio > 0.5:
                        overlaps = True
                        break
            
            if not overlaps:
                # 檢查這個金額是否是有意義的損害項目
                context = text[max(0, start-50):min(len(text), end+50)]
                if self._is_meaningful_damage_amount(amount, context):
                    filtered.append((amount, start, end))
                    used_amounts.add(amount)
        
        return filtered
    
    def _is_meaningful_damage_amount(self, amount: int, context: str) -> bool:
        """判斷金額是否是有意義的損害項目（學習RAG系統邏輯）"""
        
        # 1. 明確的損害金額指標
        damage_indicators = [
            '醫療費用', '修理費用', '修復費用', '車損', '慰撫金', '看護費用',
            '支出', '花費', '損失', '費用', '請求', '賠償', '交通費用',
            '治療', '急診', '門診', '車輛', '精神', '爰請求', '看護', '照護'
        ]
        
        # 2. 明確的排除指標（這些通常是計算基礎而非最終求償）
        exclude_indicators = ['計算基礎', '證據', '收據', '發票', '可證']
        
        # 檢查是否包含明確的損害指標
        has_damage_indicator = any(indicator in context for indicator in damage_indicators)
        
        # 檢查是否包含排除指標  
        has_exclude_indicator = any(indicator in context for indicator in exclude_indicators)
        
        # 如果有明確的損害指標，優先接受
        if has_damage_indicator:
            return True
        
        # 如果有數字編號（如 1. 2. 3.），通常是列舉的損害項目
        if re.search(r'\d+\.\s*', context):
            return True
        
        # 如果有排除指標但沒有損害指標，才排除
        if has_exclude_indicator:
            print(f"⚠️  排除金額 {amount:,}元 (包含排除指標)")
            return False
        
        # 預設接受（避免過度排除）
        return True
    
    def _is_calculation_base(self, context: str) -> bool:
        """判斷是否為計算基礎（學習RAG系統）"""
        
        # 明確的計算基礎指標（這些通常不是最終求償金額）
        pure_base_indicators = ['每月薪資', '月收入', '日薪', '年度所得', '月薪為', '薪資為', '每月工資', '基本工資']
        
        # 明確的最終求償指標（這些絕對是賠償請求，不應被排除）
        final_claim_indicators = [
            '醫療費用', '看護費用', '修理費用', '修復費用', '慰撫金', '交通費用',
            '支出', '花費', '損失', '請求', '賠償', 
            '總計', '合計', '共計', '一共', '故請求'
        ]
        
        # 如果包含最終求償指標，絕對不是計算基礎
        if any(indicator in context for indicator in final_claim_indicators):
            return False
        
        # 檢查是否有明確的計算基礎指標
        has_pure_base = any(indicator in context for indicator in pure_base_indicators)
        
        # 檢查特定排除關鍵詞（非常嚴格）
        specific_exclude = ['計算基礎', '證據', '收據', '發票', '可證']
        has_exclude = any(keyword in context for keyword in specific_exclude)
        
        # 只有明確是計算基礎才排除
        return has_pure_base or has_exclude
    
    def _get_precise_context(self, text: str, amount: int, pos: int) -> str:
        """獲取金額的精確上下文"""
        # 向前找到最近的分隔符
        start = pos
        for i in range(pos - 1, max(0, pos - 100), -1):
            if text[i] in '，。、；\n':
                start = i + 1
                break
        
        # 向後找到金額結束位置
        amount_pattern = f'{amount:,}元|{amount}元'
        match = re.search(amount_pattern, text[pos:])
        if match:
            end = pos + match.end()
        else:
            end = pos + 20
        
        return text[start:end].strip()
    
    def _classify_amount(self, context: str) -> str:
        """分類金額項目 - 按特異性優先級"""
        
        # 定義類別優先級（越具體優先級越高）
        priority_categories = [
            # 最具體的醫療類別
            '急救醫療費用', '手術費用', '住院費用', '復健費用',
            '檢查費用', '藥品費用', '預估醫療費用', '醫療用品費用',
            
            # 牙科專門類別
            '假牙費用', '牙齒治療費用',
            
            # 照護類別
            '專業看護費用', '家庭看護費用', '陪伴費用',
            
            # 車輛損害類別
            '拖吊費用', '車輛檢驗費用', '車輛零件費用', '車輛修復費用',
            
            # 收入損失類別
            '薪資損失', '營業損失', '工作能力減損', '請假損失',
            
            # 交通類別
            '就醫交通費', '計程車費用', '一般交通費用',
            
            # 精神損害類別
            '身體痛苦', '生活品質降低', '精神慰撫金',
            
            # 其他類別
            '營養費用', '文件費用', '訴訟費用',
            
            # 最一般的類別
            '其他費用'
        ]
        
        # 先檢查明確的分類指標詞
        if '慰撫金' in context or '精神' in context:
            return '精神慰撫金'
        elif '看護費用' in context or '看護' in context or '照護' in context:
            return '家庭看護費用'
        elif '醫療費用' in context or '醫療' in context or '交通費用' in context:
            if '交通' in context:
                return '就醫交通費'
            elif '急救' in context:
                return '急救醫療費用'
            elif '手術' in context:
                return '手術費用'
            elif '住院' in context:
                return '住院費用'
            else:
                return '門診醫療費用'
        
        # 按優先級順序檢查其他類別
        for category in priority_categories:
            if category in self.category_keywords:
                keywords = self.category_keywords[category]
                if any(keyword in context for keyword in keywords):
                    return category
        
        return '其他費用'
    
    def _assign_damages_to_plaintiffs(
        self, 
        plaintiffs: List[str], 
        damage_items: List[DamageItem], 
        text: str
    ) -> List[PlaintiffDamage]:
        """智能分配損害項目到原告"""
        
        if len(plaintiffs) <= 1:
            # 單一原告，分配所有項目
            total = sum(item.amount for item in damage_items)
            return [PlaintiffDamage(
                name=plaintiffs[0] if plaintiffs else "原告",
                items=damage_items,
                total=total
            )]
        
        # 多原告情況 - 精確分配策略
        plaintiff_damages = []
        assigned_items = set()  # 追蹤已分配的項目
        
        for plaintiff in plaintiffs:
            plaintiff_items = []
            
            for i, item in enumerate(damage_items):
                # 跳過已分配的項目
                if i in assigned_items:
                    continue
                    
                # 檢查項目是否與該原告相關
                if self._is_item_related_to_plaintiff(item, plaintiff, text):
                    plaintiff_items.append(item)
                    assigned_items.add(i)
                    print(f"✅ 分配給{plaintiff}: {item.amount:,}元 ({item.category})")
            
            total = sum(item.amount for item in plaintiff_items)
            plaintiff_damages.append(PlaintiffDamage(
                name=plaintiff,
                items=plaintiff_items,
                total=total
            ))
        
        # 檢查是否有未分配的項目
        unassigned_items = [item for i, item in enumerate(damage_items) if i not in assigned_items]
        if unassigned_items:
            print(f"⚠️  發現 {len(unassigned_items)} 個未分配項目:")
            for item in unassigned_items:
                print(f"   {item.amount:,}元 - {item.category}")
            
            # 對於未分配的項目，嘗試根據段落結構分配
            for item in unassigned_items:
                assigned = False
                for i, plaintiff in enumerate(plaintiffs):
                    # 檢查項目是否在該原告的段落中
                    if self._is_item_in_plaintiff_section(item, plaintiff, text):
                        plaintiff_damages[i].items.append(item)
                        plaintiff_damages[i].total += item.amount
                        print(f"🔧 段落分配給{plaintiff}: {item.amount:,}元")
                        assigned = True
                        break
                
                # 如果還是無法分配，分配給第一個原告（避免遺失）
                if not assigned:
                    plaintiff_damages[0].items.append(item)
                    plaintiff_damages[0].total += item.amount
                    print(f"🔧 默認分配給{plaintiffs[0]}: {item.amount:,}元")
        
        print(f"🔍 最終分配結果:")
        for pd in plaintiff_damages:
            print(f"  {pd.name}: {len(pd.items)}個項目，總計{pd.total:,}元")
        
        return plaintiff_damages
    
    def _is_item_related_to_plaintiff(
        self, 
        item: DamageItem, 
        plaintiff: str, 
        text: str
    ) -> bool:
        """判斷項目是否與特定原告相關"""
        
        # 1. 檢查項目描述中是否包含原告姓名
        if plaintiff in item.description:
            return True
        
        # 2. 檢查項目上下文中是否包含原告姓名
        if plaintiff in item.context:
            return True
        
        # 3. 檢查更廣泛的上下文 - 在相同段落中查找
        # 找到金額在文本中的位置
        amount_pattern = f'{item.amount:,}元|{item.amount}元'
        matches = list(re.finditer(amount_pattern, text))
        
        for match in matches:
            # 獲取段落範圍（從前一個"（"到後一個"（"）
            start = match.start()
            paragraph_start = start
            paragraph_end = match.end()
            
            # 向前找段落開始
            for i in range(start - 1, max(0, start - 500), -1):
                if text[i] == '（' and i > 0 and text[i-1] in '一二三四五':
                    paragraph_start = i
                    break
            
            # 向後找段落結束
            for i in range(match.end(), min(len(text), match.end() + 500)):
                if text[i] == '（' and i + 5 < len(text) and text[i+3] == '）':
                    paragraph_end = i
                    break
            
            paragraph_context = text[paragraph_start:paragraph_end]
            
            # 檢查段落中是否包含該原告
            if f'原告{plaintiff}' in paragraph_context:
                return True
        
        return False
    
    def _is_item_in_plaintiff_section(self, item: DamageItem, plaintiff: str, text: str) -> bool:
        """檢查項目是否在指定原告的段落中"""
        
        # 找到該原告的段落範圍
        plaintiff_section_pattern = f'（[一二三四五]）原告{plaintiff}部分：'
        section_match = re.search(plaintiff_section_pattern, text)
        
        if not section_match:
            return False
        
        section_start = section_match.start()
        
        # 找到下一個段落的開始（或文檔結束）
        next_section_pattern = r'（[一二三四五]）原告[\u4e00-\u9fff]{2,4}部分：'
        next_matches = list(re.finditer(next_section_pattern, text))
        
        section_end = len(text)  # 默認到文檔結束
        for match in next_matches:
            if match.start() > section_start:
                section_end = match.start()
                break
        
        # 檢查項目的金額是否在這個段落中
        section_text = text[section_start:section_end]
        amount_pattern = f'{item.amount:,}元|{item.amount}元'
        
        return bool(re.search(amount_pattern, section_text))
    
    def _build_indictment(
        self, 
        accident_origin: str, 
        legal_basis: str, 
        plaintiff_damages: List[PlaintiffDamage]
    ) -> str:
        """構建完整起訴書"""
        
        lines = [
            f"一、{accident_origin}",
            "",
            legal_basis,
            "",
            "三、損害項目："
        ]
        
        # 為每個原告生成項目
        for i, plaintiff_damage in enumerate(plaintiff_damages):
            if not plaintiff_damage.items:
                continue
                
            chinese_num = self._get_chinese_number(i + 1)
            lines.append(f"（{chinese_num}）原告{plaintiff_damage.name}之損害：")
            
            # 按類別組織項目
            categories = {}
            for item in plaintiff_damage.items:
                if item.category not in categories:
                    categories[item.category] = []
                categories[item.category].append(item)
            
            # 生成每個類別的項目
            item_counter = 1
            for category, items in categories.items():
                total_amount = sum(item.amount for item in items)
                
                lines.append(f"{item_counter}. {category}：{total_amount:,}元")
                
                # 生成描述
                description = self._generate_description(category, total_amount, plaintiff_damage.name)
                lines.append(description)
                lines.append("")
                
                item_counter += 1
        
        # 添加總結
        if len(plaintiff_damages) > 1:
            summary_parts = []
            grand_total = 0
            
            for pd in plaintiff_damages:
                if pd.items:
                    category_summaries = []
                    categories = {}
                    for item in pd.items:
                        if item.category not in categories:
                            categories[item.category] = 0
                        categories[item.category] += item.amount
                    
                    for category, amount in categories.items():
                        category_summaries.append(f"{category}{amount:,}元")
                    
                    summary_parts.append(f"應賠償原告{pd.name}之損害，包含{'、'.join(category_summaries)}，總計{pd.total:,}元")
                    grand_total += pd.total
            
            if summary_parts:
                summary_num = self._get_chinese_number(len(plaintiff_damages) + 1)
                lines.append(f"（{summary_num}）綜上所陳，被告{'; '.join(summary_parts)}。兩原告之請求金額合計{grand_total:,}元，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。")
        
        return "\n".join(lines)
    
    def _get_chinese_number(self, num: int) -> str:
        """轉換為中文數字"""
        chinese_nums = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        if 1 <= num <= 10:
            return chinese_nums[num]
        return str(num)
    
    def _chinese_to_number(self, chinese_str: str) -> int:
        """將中文數字轉換為阿拉伯數字"""
        chinese_map = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        
        if chinese_str in chinese_map:
            return chinese_map[chinese_str]
        
        # 處理十幾的情況
        if chinese_str.startswith('十'):
            if len(chinese_str) == 1:
                return 10
            else:
                return 10 + chinese_map.get(chinese_str[1], 0)
        
        # 處理幾十的情況
        if '十' in chinese_str:
            parts = chinese_str.split('十')
            tens = chinese_map.get(parts[0], 0) * 10
            ones = chinese_map.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return tens + ones
        
        return 1  # 默認值
    
    def _generate_description(self, category: str, amount: int, plaintiff: str) -> str:
        """生成詳細的項目描述"""
        descriptions = {
            # 醫療相關描述
            '急救醫療費用': f"原告{plaintiff}因本次事故受傷，需緊急就醫急救，支出急救醫療費用{amount:,}元。",
            '手術費用': f"原告{plaintiff}因本次事故受傷，需接受手術治療，支出手術費用{amount:,}元。",
            '住院費用': f"原告{plaintiff}因本次事故受傷，需住院治療，支出住院費用{amount:,}元。",
            '門診醫療費用': f"原告{plaintiff}因本次事故受傷，需門診治療，支出門診醫療費用{amount:,}元。",
            '復健費用': f"原告{plaintiff}因本次事故受傷，需復健治療，支出復健費用{amount:,}元。",
            '檢查費用': f"原告{plaintiff}因本次事故受傷，需各項檢查以確定傷勢，支出檢查費用{amount:,}元。",
            '藥品費用': f"原告{plaintiff}因本次事故受傷，需購買藥品治療，支出藥品費用{amount:,}元。",
            '預估醫療費用': f"原告{plaintiff}因本次事故受傷，預估未來仍需持續醫療，預估醫療費用{amount:,}元。",
            '醫療用品費用': f"原告{plaintiff}因本次事故受傷，需購買醫療用品輔助治療，支出醫療用品費用{amount:,}元。",
            
            # 牙科描述
            '牙齒治療費用': f"原告{plaintiff}因本次事故導致牙齒受損，需牙科治療，支出牙齒治療費用{amount:,}元。",
            '假牙費用': f"原告{plaintiff}因本次事故導致牙齒缺失，需製作假牙，支出假牙費用{amount:,}元。",
            
            # 照護描述
            '專業看護費用': f"原告{plaintiff}因本次事故受傷，需專業看護照料，支出專業看護費用{amount:,}元。",
            '家庭看護費用': f"原告{plaintiff}因本次事故受傷，需家庭看護照顧，支出家庭看護費用{amount:,}元。",
            '陪伴費用': f"原告{plaintiff}因本次事故受傷，需家屬陪伴照護，支出陪伴費用{amount:,}元。",
            
            # 車輛損害描述
            '車輛修復費用': f"原告{plaintiff}所騎乘之車輛因本次事故受損，支出車輛修復費用{amount:,}元。",
            '車輛零件費用': f"原告{plaintiff}所騎乘之車輛因本次事故需更換零件，支出車輛零件費用{amount:,}元。",
            '拖吊費用': f"原告{plaintiff}所騎乘之車輛因本次事故需拖吊處理，支出拖吊費用{amount:,}元。",
            '車輛檢驗費用': f"原告{plaintiff}所騎乘之車輛因本次事故需檢驗鑑定，支出車輛檢驗費用{amount:,}元。",
            
            # 收入損失描述
            '薪資損失': f"原告{plaintiff}因本次事故受傷無法正常工作，造成薪資損失{amount:,}元。",
            '營業損失': f"原告{plaintiff}因本次事故受傷無法正常營業，造成營業損失{amount:,}元。",
            '工作能力減損': f"原告{plaintiff}因本次事故受傷導致工作能力減損，造成收入損失{amount:,}元。",
            '請假損失': f"原告{plaintiff}因本次事故受傷需請假治療，造成請假損失{amount:,}元。",
            
            # 交通費用描述
            '就醫交通費': f"原告{plaintiff}因本次事故受傷需就醫治療，支出就醫交通費{amount:,}元。",
            '一般交通費用': f"原告{plaintiff}因本次事故相關事務，支出交通費用{amount:,}元。",
            '計程車費用': f"原告{plaintiff}因本次事故需搭乘計程車處理相關事務，支出計程車費用{amount:,}元。",
            
            # 精神損害描述
            '精神慰撫金': f"原告{plaintiff}因本次車禍造成身體傷害及精神痛苦，請求精神慰撫金{amount:,}元。",
            '身體痛苦': f"原告{plaintiff}因本次事故受傷導致身體痛苦，請求痛苦賠償{amount:,}元。",
            '生活品質降低': f"原告{plaintiff}因本次事故受傷導致生活品質降低，請求賠償{amount:,}元。",
            
            # 其他費用描述
            '營養費用': f"原告{plaintiff}因本次事故受傷需補充營養，支出營養費用{amount:,}元。",
            '文件費用': f"原告{plaintiff}因本次事故需申請各項證明文件，支出文件費用{amount:,}元。",
            '訴訟費用': f"原告{plaintiff}因本次事故進行訴訟程序，支出訴訟費用{amount:,}元。",
            '其他費用': f"原告{plaintiff}因本次事故支出其他相關費用{amount:,}元。"
        }
        
        return descriptions.get(category, f"原告{plaintiff}因本次事故支出{category}{amount:,}元。")
    
    def _format_with_llm(self, indictment: str) -> Optional[str]:
        """使用LLM優化起訴書格式和語言"""
        
        prompt = f"""你是一位專業的法律文書專家，請參考以下標準起訴書範例格式，優化下面的起訴書。

【標準起訴書範例格式】：

一、緣被告於民國○年○月○日○時○分許，駕駛車牌號碼○○○號機車，沿○○路往○○方向行駛，行經○○路○○號前，本應注意車前狀況，並隨時採取必要之安全措施，而依當時情形，又無不能注意之情事，竟疏未注意及此，致撞擊前方由原告○○○所駕駛之車牌號碼○○○號機車，造成原告人車倒地受傷。

二、按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」、「汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。」、「不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。」、「不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。」民法第184條第1項前段、民法第191條之2、民法第193條第1項、民法第195條第1項前段分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任：

三、（一）醫療費用：新台幣○○○元
原告因本次車禍受傷，前往○○醫院治療，支出醫療費用新台幣○○○元。

（二）車輛修復費用：新台幣○○○元  
原告所騎乘之機車因本次車禍受損，修復費用新台幣○○○元。

（三）工作收入損失：新台幣○○○元
原告因本次車禍受傷無法工作，造成工作收入損失新台幣○○○元。

（四）精神慰撫金：新台幣○○○元
原告因本次車禍受有身體傷害及精神痛苦，請求精神慰撫金新台幣○○○元。

綜上所述，被告應賠償原告之損害總計新台幣○○○元，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。

【優化要求】：
1. 保持所有數字和金額完全不變
2. 參考上述範例格式，修正起訴書結構
3. 確保正確的中文編號順序：（一）、（二）、（三）等
4. 改善法律用語的專業性和準確性
5. 確保多原告案件的正確格式
6. 修正任何格式不一致的問題

【原始起訴書】：
{indictment}

請提供格式優化後的起訴書："""

        try:
            # 準備Ollama請求
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # 較低的創造性，保持準確性
                    "top_p": 0.9,
                    "num_predict": 2048  # 允許較長的輸出
                }
            }
            
            # 調用Ollama API
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate",
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps(data)],
                capture_output=True,
                text=True,
                timeout=120  # 2分鐘超時
            )
            
            if result.returncode == 0 and result.stdout:
                response_data = json.loads(result.stdout)
                formatted_text = response_data.get("response", "").strip()
                
                if formatted_text and len(formatted_text) > 100:  # 確保有實質內容
                    return formatted_text
                else:
                    print("⚠️  LLM返回內容過短，可能格式化失敗")
                    return None
            else:
                print(f"⚠️  Ollama API調用失敗: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("⚠️  LLM格式化超時")
            return None
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON解析錯誤: {e}")
            return None
        except Exception as e:
            print(f"⚠️  LLM格式化意外錯誤: {e}")
            return None
    
    def _check_ollama_availability(self) -> bool:
        """檢查Ollama服務是否可用"""
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False


def main():
    """主函數"""
    print("🎯 簡潔版起訴書生成器（增強版）")
    print("🔧 配置選項：")
    
    # 詢問是否使用LLM格式化
    use_llm = input("是否啟用LLM格式化優化？ (y/N): ").strip().lower()
    use_llm_formatting = use_llm in ['y', 'yes', 'true', '1']
    
    # 如果啟用LLM，詢問模型
    model_name = "llama3.1"
    if use_llm_formatting:
        custom_model = input(f"LLM模型名稱 (預設: {model_name}): ").strip()
        if custom_model:
            model_name = custom_model
    
    generator = SimpleIndictmentGenerator(
        use_llm_formatting=use_llm_formatting,
        model_name=model_name
    )
    
    print("\n📋 請輸入完整的車禍案件資料（輸入 'END' 結束）：")
    
    lines = []
    while True:
        line = input()
        if line.upper() == 'END':
            break
        lines.append(line)
    
    if not lines:
        print("❌ 輸入不能為空")
        return
    
    input_text = '\n'.join(lines)
    result = generator.generate_indictment(input_text)
    
    print("\n" + "="*60)
    print("📄 生成的起訴書：")
    print("="*60)
    print(result)
    print("="*60)


if __name__ == "__main__":
    main()