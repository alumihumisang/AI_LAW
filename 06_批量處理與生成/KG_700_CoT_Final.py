#!/usr/bin/env python3
"""
KG_700_CoT_Final.py
最終版本：整合結構化金額處理和CoT推理
完美解決法律文件中的金額計算問題
"""

import os
import re
import json
import requests
import time
import sys
from typing import List, Dict, Any, Optional
from collections import Counter

# 導入結構化處理器
try:
    from structured_legal_amount_processor import StructuredLegalAmountProcessor
    STRUCTURED_PROCESSOR_AVAILABLE = True
    print("✅ 結構化金額處理器載入成功")
except ImportError:
    STRUCTURED_PROCESSOR_AVAILABLE = False
    print("⚠️ 結構化金額處理器未找到")

# 導入標準化處理器作為備用
try:
    from legal_amount_standardizer import LegalAmountStandardizer
    BASIC_STANDARDIZER_AVAILABLE = True
    print("✅ 基本金額標準化器載入成功")
except ImportError:
    BASIC_STANDARDIZER_AVAILABLE = False
    print("⚠️ 基本金額標準化器未找到")

# 導入原有的 CoT 模組
try:
    from KG_700_CoT_Hybrid import HybridCoTGenerator, get_case_type, extract_parties, detect_special_relationships, get_applicable_laws
    COT_MODULES_AVAILABLE = True
    print("✅ CoT 模組載入成功")
except ImportError:
    COT_MODULES_AVAILABLE = False
    print("⚠️ CoT 模組未找到")

# ===== 基本設定 =====
LLM_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:27b"

class FinalCoTGenerator:
    """最終版 CoT 生成器：完美解決金額計算問題"""
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.llm_url = LLM_URL
        
        # 初始化處理器
        if STRUCTURED_PROCESSOR_AVAILABLE:
            self.structured_processor = StructuredLegalAmountProcessor()
        else:
            self.structured_processor = None
        
        if BASIC_STANDARDIZER_AVAILABLE:
            self.basic_standardizer = LegalAmountStandardizer()
        else:
            self.basic_standardizer = None
        
        if COT_MODULES_AVAILABLE:
            self.base_generator = HybridCoTGenerator(model_name)
        else:
            self.base_generator = None
        
        # 檢查LLM連接
        self.llm_available = self._check_llm_connection()
    
    def _check_llm_connection(self) -> bool:
        """檢查LLM連接"""
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def call_llm(self, prompt: str, timeout: int = 180) -> str:
        """調用LLM"""
        if not self.llm_available:
            return "❌ LLM服務不可用"
        
        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json()["response"].strip()
            else:
                return f"❌ LLM API錯誤: {response.status_code}"
                
        except Exception as e:
            return f"❌ LLM調用失敗: {str(e)}"
    
    def analyze_compensation_structure(self, compensation_text: str) -> Dict[str, Any]:
        """智能分析賠償結構"""
        print("🔍 智能分析賠償結構...")
        
        # 檢測文本結構類型
        structure_type = self._detect_structure_type(compensation_text)
        
        if structure_type == "structured" and self.structured_processor:
            print("📋 檢測到結構化文件，使用結構化處理器")
            result = self.structured_processor.process_structured_document(compensation_text)
            result['processing_method'] = 'structured'
            result['structure_type'] = structure_type
        elif self.basic_standardizer:
            print("📝 使用基本標準化處理器")
            basic_result = self.basic_standardizer.standardize_document(compensation_text)
            result = {
                'total_amount': basic_result['calculations'].get('main_total', 0),
                'amounts': basic_result['amounts'],
                'standardized_text': basic_result['standardized_text'],
                'processing_method': 'basic',
                'structure_type': structure_type
            }
        else:
            print("⚠️ 使用基本文本處理")
            result = {
                'total_amount': 0,
                'amounts': [],
                'standardized_text': compensation_text,
                'processing_method': 'text_only',
                'structure_type': structure_type
            }
        
        return result
    
    def _detect_structure_type(self, text: str) -> str:
        """檢測文本結構類型"""
        # 檢查結構化模式
        structured_patterns = [
            r'\d+\.\s*[^：:]+[：:]\s*[0-9,]+元',  # 1. 項目：金額
            r'（[一二三四五六七八九十]+）.*?[：:]\s*[0-9,]+元',  # （一）項目：金額
            r'說明：.*?[0-9,]+元'  # 說明：...金額
        ]
        
        structured_matches = sum(1 for pattern in structured_patterns 
                               if re.search(pattern, text))
        
        if structured_matches >= 2:
            return "structured"
        elif "元" in text:
            return "semi_structured"
        else:
            return "unstructured"
    
    def generate_perfect_conclusion(self, compensation_text: str, parties: dict, original_query: str = None) -> str:
        """生成完美的結論（解決所有金額問題）"""
        print("🎯 生成完美結論...")
        
        # 步驟1: 智能結構分析
        analysis_result = self.analyze_compensation_structure(compensation_text)
        
        # 步驟2: 構建完美提示詞
        prompt = self._build_perfect_prompt(
            compensation_text,
            parties,
            analysis_result,
            original_query
        )
        
        # 步驟3: 調用LLM
        conclusion = self.call_llm(prompt)
        
        # 步驟4: 後處理和驗證
        final_conclusion = self._post_process_perfect_conclusion(
            conclusion,
            analysis_result
        )
        
        return final_conclusion
    
    def _build_perfect_prompt(self, compensation_text: str, parties: dict, analysis_result: Dict[str, Any], original_query: str = None) -> str:
        """構建完美的提示詞"""
        
        plaintiff = parties.get("原告", "原告")
        defendant = parties.get("被告", "被告")
        
        # 根據分析結果調整提示詞
        if analysis_result['processing_method'] == 'structured':
            # 結構化處理結果
            structured_items = analysis_result.get('structured_items', [])
            calculation = analysis_result.get('calculation', {})
            validation = analysis_result.get('validation', {})
            
            items_summary = "\n📋 已識別的損害項目："
            for item in structured_items:
                items_summary += f"\n• {item['item_title']}: {item['formatted_amount']}"
            
            items_summary += f"\n\n💰 計算分析："
            items_summary += f"\n• 正確總計: {calculation.get('total', 0):,}元"
            
            if validation.get('claimed_total'):
                items_summary += f"\n• 原起訴狀聲稱: {validation['claimed_total']:,}元"
                if validation.get('difference', 0) != 0:
                    if validation['difference'] < 0:
                        items_summary += f"\n• ❌ 原起訴狀少算了: {abs(validation['difference']):,}元"
                    else:
                        items_summary += f"\n• ❌ 原起訴狀多算了: {validation['difference']:,}元"
                    items_summary += f"\n• ✅ 請使用正確金額: {calculation.get('total', 0):,}元"
        
        else:
            # 基本處理結果
            total_amount = analysis_result.get('total_amount', 0)
            amounts = analysis_result.get('amounts', [])
            
            items_summary = "\n📋 已識別的金額項目："
            for amount in amounts:
                items_summary += f"\n• {amount.get('original_text', '')}: {amount.get('formatted_amount', '')}"
            
            items_summary += f"\n\n💰 計算總額: {total_amount:,}元"
        
        # 構建提示詞
        prompt = f"""你是台灣資深律師，請根據以下分析結果生成專業的起訴狀結論段落。

🎯 重要指示：
1. 必須使用正確的金額計算，避免重複計算說明文字中的金額
2. 結論必須包含完整的項目明細
3. 總金額必須準確無誤
4. 採用標準的法律文書格式

👥 當事人資訊：
原告：{plaintiff}
被告：{defendant}

📄 損害賠償分析：
{compensation_text}

{items_summary}

🏛️ 請生成專業的結論段落，包括：
1. 損害項目明細列表
2. 正確的總金額計算
3. 標準的結論格式
4. 利息計算條款

格式要求：
- 開頭：「四、結論：」
- 中間：列舉各項損害明細
- 結尾：總計金額和利息請求

請確保金額計算絕對正確！"""

        return prompt
    
    def _post_process_perfect_conclusion(self, conclusion: str, analysis_result: Dict[str, Any]) -> str:
        """後處理完美結論"""
        
        # 添加處理資訊
        processing_info = f"\n\n💡 處理資訊：\n"
        processing_info += f"處理方法：{analysis_result.get('processing_method', 'unknown')}\n"
        processing_info += f"結構類型：{analysis_result.get('structure_type', 'unknown')}\n"
        
        if analysis_result.get('processing_method') == 'structured':
            calculation = analysis_result.get('calculation', {})
            validation = analysis_result.get('validation', {})
            
            processing_info += f"正確總額：{calculation.get('total', 0):,}元\n"
            if validation.get('claimed_total'):
                processing_info += f"原聲稱額：{validation['claimed_total']:,}元\n"
                if validation.get('difference', 0) != 0:
                    processing_info += f"差額修正：{abs(validation['difference']):,}元\n"
        
        return conclusion + processing_info
    
    def generate_complete_document_final(self, accident_facts: str, compensation_text: str, similar_cases: List[str] = None) -> Dict[str, Any]:
        """生成完整文件（最終版）"""
        print("📄 生成完整起訴狀文件（最終版）...")
        
        # 分析案件資訊
        if COT_MODULES_AVAILABLE:
            parties = extract_parties(accident_facts)
            case_type = get_case_type(accident_facts)
            applicable_laws = get_applicable_laws(accident_facts, compensation_text)
        else:
            parties = {"原告": "原告", "被告": "被告"}
            case_type = "一般案件"
            applicable_laws = ["民法第184條第1項前段"]
        
        # 智能分析賠償結構
        compensation_analysis = self.analyze_compensation_structure(compensation_text)
        
        result = {
            "案件類型": case_type,
            "當事人": parties,
            "適用法條": applicable_laws,
            "賠償分析": compensation_analysis,
            "處理方法": compensation_analysis.get('processing_method', 'unknown')
        }
        
        try:
            # 生成各段落
            if self.base_generator:
                result["事實"] = self.base_generator.generate_standard_facts(accident_facts, similar_cases)
                result["法條"] = self.base_generator.generate_standard_laws(applicable_laws)
                result["損害"] = self.base_generator.generate_standard_compensation(compensation_text, parties)
            else:
                result["事實"] = self._generate_simple_facts(accident_facts)
                result["法條"] = self._generate_simple_laws(applicable_laws)
                result["損害"] = compensation_text
            
            # 最終版結論
            result["結論"] = self.generate_perfect_conclusion(compensation_text, parties, accident_facts)
            
        except Exception as e:
            result["錯誤"] = str(e)
        
        return result
    
    def _generate_simple_facts(self, accident_facts: str) -> str:
        """簡化版事實生成"""
        prompt = f"請根據以下事實撰寫起訴狀事實段落：\n{accident_facts}"
        return self.call_llm(prompt)
    
    def _generate_simple_laws(self, applicable_laws: List[str]) -> str:
        """簡化版法條生成"""
        laws_text = "、".join(applicable_laws)
        prompt = f"請根據以下法條撰寫起訴狀法條段落：\n{laws_text}"
        return self.call_llm(prompt)

def test_final_generator():
    """測試最終版生成器"""
    
    # 使用實際有問題的案例
    test_case = {
        "accident_facts": "被告駕駛汽車因過失撞擊原告吳麗娟和陳碧翔，造成兩原告受傷住院",
        "compensation_text": """
三、損害項目：

（一）原告吳麗娟之損害：
1. 醫療費用：6,720元
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
1. 醫療費用：12,180元
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
    }
    
    print("🧪 最終版CoT生成器測試")
    print("測試實際有計算錯誤的案例")
    print("=" * 80)
    
    generator = FinalCoTGenerator()
    
    # 分析賠償結構
    print("📊 賠償結構分析:")
    analysis = generator.analyze_compensation_structure(test_case['compensation_text'])
    
    if analysis.get('processing_method') == 'structured':
        calc = analysis.get('calculation', {})
        val = analysis.get('validation', {})
        
        print(f"✅ 正確總計: {calc.get('total', 0):,}元")
        print(f"❌ 原起訴狀: {val.get('claimed_total', 0):,}元")
        if val.get('difference', 0) != 0:
            if val['difference'] < 0:
                print(f"💡 少算了: {abs(val['difference']):,}元")
            else:
                print(f"💡 多算了: {val['difference']:,}元")
    
    # 生成修正後的結論
    if generator.llm_available:
        print(f"\n📝 生成修正後的結論:")
        parties = {"原告": "吳麗娟、陳碧翔", "被告": "被告"}
        corrected_conclusion = generator.generate_perfect_conclusion(
            test_case['compensation_text'], 
            parties,
            test_case['accident_facts']
        )
        
        print(corrected_conclusion[:500] + "..." if len(corrected_conclusion) > 500 else corrected_conclusion)
    else:
        print("⚠️ LLM不可用，跳過結論生成")

def main():
    """主程序"""
    print("🏆 最終版CoT起訴狀生成器")
    print("完美解決法律文件中的所有金額計算問題")
    print("=" * 80)
    
    choice = input("""請選擇操作：
1. 測試最終版生成器
2. 生成完整起訴狀
3. 僅分析金額結構

請輸入選擇 (1-3): """).strip()
    
    if choice == "1":
        test_final_generator()
        
    elif choice == "2":
        print("\n請輸入案件資訊:")
        accident_facts = input("事實描述: ").strip()
        compensation_text = input("損害賠償: ").strip()
        
        if accident_facts and compensation_text:
            generator = FinalCoTGenerator()
            result = generator.generate_complete_document_final(accident_facts, compensation_text)
            
            print("\n" + "=" * 60)
            print("📄 生成結果:")
            for key, value in result.items():
                if key != "錯誤":
                    print(f"\n【{key}】")
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, (str, int, float)):
                                print(f"  {sub_key}: {sub_value}")
                    elif isinstance(value, list):
                        print(f"  {', '.join(str(v) for v in value)}")
                    else:
                        print(f"  {value}")
        else:
            print("❌ 請提供完整的事實和損害描述")
            
    elif choice == "3":
        compensation_text = input("請輸入損害賠償文本: ").strip()
        if compensation_text:
            generator = FinalCoTGenerator()
            analysis = generator.analyze_compensation_structure(compensation_text)
            
            print("\n📊 金額結構分析結果:")
            print(f"處理方法: {analysis.get('processing_method')}")
            print(f"結構類型: {analysis.get('structure_type')}")
            
            if analysis.get('processing_method') == 'structured':
                calc = analysis.get('calculation', {})
                print(f"正確總額: {calc.get('total', 0):,}元")
        else:
            print("❌ 請提供損害賠償文本")
    
    else:
        print("❌ 無效選擇")

if __name__ == "__main__":
    main()