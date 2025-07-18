#!/usr/bin/env python3
"""
KG_700_Semantic_Universal.py
基於語義理解的通用法律文件處理系統
真正的泛化能力，不依賴硬編碼模式匹配
"""

import os
import re
import json
import requests
import time
import sys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# ===== 基本設定 =====
LLM_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:27b"

@dataclass
class PartyInfo:
    """當事人信息"""
    name: str
    role: str  # 原告/被告
    confidence: float

@dataclass
class AmountInfo:
    """金額信息"""
    amount: int
    amount_type: str  # claim/calculation_base/unclear
    description: str
    confidence: float
    context: str

@dataclass
class CaseStructure:
    """案例結構"""
    case_type: str  # single/multi_plaintiff/multi_defendant/multi_party
    plaintiff_count: int
    defendant_count: int
    narrative_style: str
    confidence: float

class SemanticLegalProcessor:
    """基於語義理解的法律文件處理器"""
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.llm_url = LLM_URL
        
        # 檢查LLM連接
        self.llm_available = self._check_llm_connection()
        
    def _check_llm_connection(self) -> bool:
        """檢查LLM服務是否可用"""
        try:
            response = requests.post(
                self.llm_url,
                json={"model": self.model_name, "prompt": "test", "stream": False},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return 'response' in result
            return False
        except Exception as e:
            print(f"⚠️ LLM服務不可用，將使用基本模式: {e}")
            return False
    
    def call_llm(self, prompt: str, timeout: int = 60) -> str:
        """調用LLM"""
        if not self.llm_available:
            return "LLM服務不可用"
            
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
                result = response.json()
                return result.get("response", "").strip()
            else:
                return f"LLM調用失敗: {response.status_code}"
                
        except Exception as e:
            return f"LLM調用錯誤: {e}"
    
    def extract_parties_semantically(self, text: str) -> Dict[str, List[PartyInfo]]:
        """基於語義理解提取當事人 - 完全依賴LLM語義理解"""
        print("🤖 使用語義理解提取當事人...")
        
        prompt = f"""你是法律文件分析專家，請從以下文本中提取所有當事人的完整姓名。

【文本內容】
{text}

【提取要求】
1. 只提取「原告」、「被告」、「訴外人」的真實姓名
2. **重要**：必須保持姓名的完整性，絕對不可截斷或省略任何字
3. **重要**：如果原文是「原告羅靖崴」，必須提取完整的「羅靖崴」三個字
4. **重要**：如果原文是「原告歐陽天華」，必須提取完整的「歐陽天華」四個字
5. 忽略職稱、描述性文字，只要純粹的姓名
6. 如果沒有具體姓名，就用「原告」、「被告」表示

【輸出格式】
請輸出JSON格式，例如：
{{
    "原告": ["張三", "李四"],
    "被告": ["王五"],
    "訴外人": ["趙六"]
}}

【重要提醒】
- 姓名完整性是最重要的，絕對不能截斷
- 複姓（如歐陽、司馬、上官等）必須完整保留
- 三字姓名、四字姓名都必須完整保留

請分析並輸出JSON："""

        try:
            response = self.call_llm(prompt, timeout=90)
            
            # 解析JSON回應
            try:
                # 嘗試直接解析JSON
                parties_data = json.loads(response)
            except:
                # 如果JSON解析失敗，嘗試提取JSON部分
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    parties_data = json.loads(json_match.group(0))
                else:
                    print(f"❌ JSON解析失敗: {response}")
                    return self._fallback_party_extraction(text)
            
            # 轉換為PartyInfo格式
            result = {"原告": [], "被告": [], "訴外人": []}
            
            for role, names in parties_data.items():
                if role in result and isinstance(names, list):
                    for name in names:
                        if isinstance(name, str) and len(name.strip()) > 0:
                            # 語義評估姓名置信度
                            confidence = self._assess_name_confidence_semantic(name, text)
                            result[role].append(PartyInfo(name.strip(), role, confidence))
            
            print(f"🎯 語義提取結果:")
            for role, party_list in result.items():
                if party_list:
                    names = [f"{p.name}({p.confidence:.2f})" for p in party_list]
                    print(f"   {role}: {names}")
            
            return result
            
        except Exception as e:
            print(f"❌ 語義提取失敗: {e}")
            return self._fallback_party_extraction(text)
    
    def _assess_name_confidence_semantic(self, name: str, context: str) -> float:
        """基於語義評估姓名置信度"""
        confidence = 0.5  # 基礎置信度
        
        # 長度合理性
        if 2 <= len(name) <= 4:
            confidence += 0.3
        elif len(name) == 1:
            confidence += 0.1
        
        # 字符類型（中文姓名）
        if re.match(r'^[\u4e00-\u9fff]+$', name):
            confidence += 0.2
        
        # 在上下文中的出現頻率
        appearances = context.count(name)
        if appearances > 1:
            confidence += 0.1
        
        # 常見法律用詞排除
        legal_terms = ['因', '而', '受', '有', '之', '損', '害', '費', '用', '元', '賠', '償']
        if any(term in name for term in legal_terms):
            confidence -= 0.3
        
        return max(0.1, min(1.0, confidence))
    
    def _fallback_party_extraction(self, text: str) -> Dict[str, List[PartyInfo]]:
        """備用當事人提取方法"""
        print("🔄 使用備用提取方法...")
        result = {"原告": [], "被告": [], "訴外人": []}
        
        # 簡單模式：至少能識別有當事人存在
        if "原告" in text:
            result["原告"].append(PartyInfo("原告", "原告", 0.5))
        if "被告" in text:
            result["被告"].append(PartyInfo("被告", "被告", 0.5))
            
        return result
    
    def analyze_case_structure_semantically(self, text: str, parties: Dict[str, List[PartyInfo]]) -> CaseStructure:
        """基於語義分析案例結構"""
        print("🔍 分析案例結構...")
        
        plaintiff_count = len([p for p in parties["原告"] if p.confidence > 0.3])
        defendant_count = len([p for p in parties["被告"] if p.confidence > 0.3])
        
        # 判斷案例類型
        if plaintiff_count > 1 and defendant_count > 1:
            case_type = "multi_party"
        elif plaintiff_count > 1:
            case_type = "multi_plaintiff"
        elif defendant_count > 1:
            case_type = "multi_defendant"
        else:
            case_type = "single"
        
        # 判斷敘述風格 - 基於語義特徵
        narrative_style = self._detect_narrative_style_semantic(text)
        
        # 計算結構置信度
        confidence = min(1.0, (plaintiff_count + defendant_count) * 0.3)
        
        structure = CaseStructure(
            case_type=case_type,
            plaintiff_count=plaintiff_count,
            defendant_count=defendant_count,
            narrative_style=narrative_style,
            confidence=confidence
        )
        
        print(f"📊 案例結構: {case_type}, 風格: {narrative_style}, 原告: {plaintiff_count}, 被告: {defendant_count}")
        
        return structure
    
    def _detect_narrative_style_semantic(self, text: str) -> str:
        """基於語義檢測敘述風格"""
        # 結構化標記
        if re.search(r'[（(][一二三四五六七八九十][）)]', text):
            return 'structured_chinese'
        elif re.search(r'\d+\.', text):
            return 'numbered_list'
        
        # 基於語義密度
        sentences = text.split('。')
        if len(sentences) > 15:
            return 'detailed_narrative'
        elif len(sentences) > 8:
            return 'standard_narrative'
        else:
            return 'simple_narrative'
    
    def extract_amounts_semantically(self, text: str, structure: CaseStructure) -> List[AmountInfo]:
        """基於語義理解提取金額"""
        print("💰 使用語義理解提取金額...")
        
        prompt = f"""你是法律文件分析專家，請從以下損害賠償描述中提取所有相關金額並分類。

【文本內容】
{text}

【案例特徵】
- 案例類型: {structure.case_type}
- 原告數量: {structure.plaintiff_count}

【分析要求】
1. 找出所有金額數字
2. 區分每個金額的性質：
   - claim_amount: 最終的求償金額（如"請求賠償10萬元"、"支出醫療費5萬元"）
   - calculation_base: 計算基準數據（如"月薪3萬元"、"每日2000元作為計算基準"）
   - unclear: 性質不明確的金額

【特別注意】
- "XXX元計算"、"作為計算基準"、"月薪"、"日薪"等通常是calculation_base
- "請求"、"賠償"、"支出"、"損失"等通常是claim_amount

【輸出格式】
請輸出JSON格式，例如：
[
    {{"amount": 50000, "type": "claim_amount", "description": "醫療費用", "context": "支出醫療費用5萬元"}},
    {{"amount": 30000, "type": "calculation_base", "description": "月薪基準", "context": "月薪3萬元計算"}}
]

請分析並輸出JSON："""

        try:
            response = self.call_llm(prompt, timeout=120)
            
            # 解析JSON回應
            try:
                amounts_data = json.loads(response)
            except:
                json_match = re.search(r'\\[.*\\]', response, re.DOTALL)
                if json_match:
                    amounts_data = json.loads(json_match.group(0))
                else:
                    print(f"❌ 金額JSON解析失敗，使用備用方法")
                    return self._fallback_amount_extraction(text)
            
            # 轉換為AmountInfo格式
            result = []
            for item in amounts_data:
                if isinstance(item, dict) and "amount" in item:
                    amount_info = AmountInfo(
                        amount=int(item.get("amount", 0)),
                        amount_type=item.get("type", "unclear"),
                        description=item.get("description", ""),
                        confidence=0.8,  # LLM語義分析的高置信度
                        context=item.get("context", "")
                    )
                    result.append(amount_info)
            
            print(f"💰 語義提取金額結果:")
            for amt in result:
                print(f"   {amt.amount:,}元 - {amt.amount_type} ({amt.description})")
            
            return result
            
        except Exception as e:
            print(f"❌ 語義金額提取失敗: {e}")
            return self._fallback_amount_extraction(text)
    
    def _fallback_amount_extraction(self, text: str) -> List[AmountInfo]:
        """備用金額提取方法"""
        print("🔄 使用備用金額提取...")
        result = []
        
        # 基本的金額模式匹配
        amount_pattern = r'(\\d+(?:,\\d{3})*(?:\\.\\d{2})?)\\s*([萬千]?)元'
        matches = re.finditer(amount_pattern, text)
        
        for match in matches:
            amount_str = match.group(1).replace(',', '')
            unit = match.group(2)
            
            amount = float(amount_str)
            if unit == '萬':
                amount *= 10000
            elif unit == '千':
                amount *= 1000
            
            if amount >= 100:  # 排除小額
                result.append(AmountInfo(
                    amount=int(amount),
                    amount_type="unclear",
                    description="備用提取",
                    confidence=0.3,
                    context=match.group(0)
                ))
        
        return result
    
    def generate_compensation_semantically(self, text: str, structure: CaseStructure, parties: Dict[str, List[PartyInfo]], amounts: List[AmountInfo]) -> str:
        """基於語義理解生成損害賠償項目"""
        print("📝 使用語義理解生成損害項目...")
        
        # 提取有效的求償金額
        claim_amounts = [amt for amt in amounts if amt.amount_type == "claim_amount"]
        
        # 構建智能提示詞
        prompt = self._build_semantic_prompt(text, structure, parties, claim_amounts)
        
        try:
            result = self.call_llm(prompt, timeout=180)
            
            # 後處理：清理和驗證
            result = self._post_process_compensation(result, claim_amounts)
            
            return result
            
        except Exception as e:
            print(f"❌ 語義生成失敗: {e}")
            return self._fallback_compensation_generation(text, parties, amounts)
    
    def _build_semantic_prompt(self, text: str, structure: CaseStructure, parties: Dict[str, List[PartyInfo]], amounts: List[AmountInfo]) -> str:
        """構建基於語義的智能提示詞"""
        
        # 動態提取當事人信息
        plaintiff_names = [p.name for p in parties["原告"] if p.confidence > 0.3]
        defendant_names = [p.name for p in parties["被告"] if p.confidence > 0.3]
        
        plaintiff_str = "、".join(plaintiff_names) if plaintiff_names else "原告"
        defendant_str = "、".join(defendant_names) if defendant_names else "被告"
        
        # 提取金額信息
        amount_summary = []
        for amt in amounts:
            amount_summary.append(f"{amt.amount:,}元({amt.description})")
        
        # 根據案例類型選擇格式策略
        if structure.case_type == "multi_plaintiff":
            format_instruction = f"""按原告分組格式：
（一）原告[姓名]之損害：
1. 損害類型：金額元
原告[姓名]因本次事故[簡潔理由]，支出/受有[損害類型]金額元。

（二）原告[姓名]之損害：
1. 損害類型：金額元
原告[姓名]因本次事故[簡潔理由]，支出/受有[損害類型]金額元。"""
        else:
            format_instruction = """統一格式：
（一）損害類型：金額元
原告因本次事故[簡潔理由]，支出/受有[損害類型]金額元。"""
        
        prompt = f"""你是台灣資深律師，請基於以下分析結果生成專業的損害賠償項目。

【案例分析結果】
- 案例類型：{structure.case_type}
- 敘述風格：{structure.narrative_style}
- 原告：{plaintiff_str}（{structure.plaintiff_count}名）
- 被告：{defendant_str}
- 識別金額：{amount_summary}

【原始損害描述】
{text}

【生成要求】
1. **重要**：只使用已識別的有效求償金額，忽略計算基準
2. **重要**：保持原告姓名的完整性，不可截斷
3. **重要**：按案例類型使用適當的分組格式
4. 每項理由1-2句話，簡潔明瞭
5. 使用千分位逗號格式顯示金額
6. 不要包含總計、綜上所述等結論性文字

【輸出格式】
{format_instruction}

【嚴格禁止】
- 不可截斷或修改原告姓名
- 不可包含計算基準金額
- 不可創造不存在的損害項目
- 不可包含總金額計算

請基於案例特徵生成專業的損害項目："""

        return prompt
    
    def _post_process_compensation(self, text: str, amounts: List[AmountInfo]) -> str:
        """後處理損害賠償文本"""
        # 基本清理
        lines = text.split('\\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not any(keyword in line for keyword in ['總計', '綜上', '合計']):
                cleaned_lines.append(line)
        
        return '\\n'.join(cleaned_lines)
    
    def _fallback_compensation_generation(self, text: str, parties: Dict[str, List[PartyInfo]], amounts: List[AmountInfo]) -> str:
        """備用損害項目生成"""
        print("🔄 使用備用生成方法...")
        
        result_lines = []
        chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        
        claim_amounts = [amt for amt in amounts if amt.amount_type in ["claim_amount", "unclear"]]
        
        for i, amt in enumerate(claim_amounts):
            if i < len(chinese_nums):
                num = chinese_nums[i]
                result_lines.append(f"（{num}）損害項目：{amt.amount:,}元")
                result_lines.append(f"原告因本次事故受有損害，請求賠償{amt.amount:,}元。")
                result_lines.append("")
        
        return '\\n'.join(result_lines)
    
    def generate_cot_conclusion_semantic(self, accident_facts: str, compensation_text: str, parties: Dict[str, List[PartyInfo]], amounts: List[AmountInfo]) -> str:
        """基於語義理解生成CoT結論"""
        print("🧠 使用語義理解生成CoT結論...")
        
        # 計算總金額
        claim_amounts = [amt for amt in amounts if amt.amount_type == "claim_amount"]
        total_amount = sum(amt.amount for amt in claim_amounts)
        
        # 提取當事人姓名
        plaintiff_names = [p.name for p in parties["原告"] if p.confidence > 0.3]
        defendant_names = [p.name for p in parties["被告"] if p.confidence > 0.3]
        
        plaintiff_str = "、".join(plaintiff_names) if plaintiff_names else "原告"
        defendant_str = "、".join(defendant_names) if defendant_names else "被告"
        
        prompt = f"""你是台灣資深律師，請使用Chain of Thought推理方式生成專業的起訴狀結論段落。

【當事人資訊】
原告：{plaintiff_str}
被告：{defendant_str}

【案件事實】
{accident_facts}

【損害賠償內容】
{compensation_text}

【智能金額分析】
有效求償金額：{[amt.amount for amt in claim_amounts]}
正確總計：{total_amount:,}元

【CoT推理步驟】
步驟1: 分析案件性質和當事人責任
步驟2: 從損害賠償內容中識別各項損害項目
步驟3: 驗證各項金額的合理性
步驟4: 形成簡潔精確的結論

【輸出要求】
- 開頭：「四、結論：」
- 格式：一段式連續文字，不要條列式
- 內容：綜合敘述損害項目和總金額
- **重要**：必須使用正確的總計金額{total_amount:,}元
- **重要**：保持當事人姓名完整性

請生成專業的結論段落："""

        try:
            result = self.call_llm(prompt, timeout=180)
            return result if result else "四、結論：\\n（語義生成失敗，請檢查輸入內容）"
        except Exception as e:
            print(f"❌ 結論生成失敗: {e}")
            return f"四、結論：\\n綜上所陳，被告應賠償原告損害總計{total_amount:,}元。"
    
    def process_case_semantically(self, text: str) -> Dict[str, Any]:
        """完整的語義化案例處理流程"""
        print("🚀 開始語義化處理流程...")
        print("=" * 80)
        
        results = {}
        
        try:
            # 1. 語義提取當事人
            parties = self.extract_parties_semantically(text)
            results["parties"] = parties
            
            # 2. 分析案例結構
            structure = self.analyze_case_structure_semantically(text, parties)
            results["structure"] = structure
            
            # 3. 語義提取金額
            amounts = self.extract_amounts_semantically(text, structure)
            results["amounts"] = amounts
            
            # 4. 生成損害項目
            compensation = self.generate_compensation_semantically(text, structure, parties, amounts)
            results["compensation"] = compensation
            
            # 5. 生成結論
            conclusion = self.generate_cot_conclusion_semantic(text, compensation, parties, amounts)
            results["conclusion"] = conclusion
            
            # 6. 統計信息
            claim_amounts = [amt for amt in amounts if amt.amount_type == "claim_amount"]
            total_amount = sum(amt.amount for amt in claim_amounts)
            
            results["summary"] = {
                "total_amount": total_amount,
                "claim_count": len(claim_amounts),
                "plaintiff_count": structure.plaintiff_count,
                "defendant_count": structure.defendant_count,
                "confidence": structure.confidence
            }
            
            print("✅ 語義化處理完成！")
            return results
            
        except Exception as e:
            print(f"❌ 語義化處理失敗: {e}")
            results["error"] = str(e)
            return results

def test_semantic_system():
    """測試語義化系統"""
    processor = SemanticLegalProcessor()
    
    # 測試案例：你提供的多原告案例
    test_case = """
查原告羅靖崴因系爭車禍受有前揭傷害而前往聯新醫院就診，有聯新醫院診斷證明書可作為證據，其因而支出醫療費用2,443元、交通費1,235元。
原告羅靖崴因本件事故受傷，需在家休養16日而無法工作，又原告羅靖崴每月工資應為37,778元，又依聯新醫院診斷證明書分別於110年12月4日及111年1月10日建議原告羅靖崴應休養3日及兩週，是原告羅靖崴應有17日不能工作，但原告羅靖崴僅請求16日工資損失，因此請求不能工作之損失20,148元
原告羅靖崴因本件車禍而受有頭部外傷併輕微腦震盪之傷害，影響日常生活甚鉅，於精神上可能承受之無形痛苦，故請求被告賠償10,000元精神慰撫金。

原告邱品妍因系爭車禍受有前揭傷害同樣前往聯新醫院醫治，有聯新醫院診斷證明書作為證據，其因而支出醫療費用57,550元、交通費22,195元。
另外原告邱品妍因本件事故受傷，需在家休養1月又28日而無法工作，又原告邱品妍每月工資為34,535元，又依聯新醫院診斷證明書分別於110年12月4日、111年12月6日、 110年12月17日、110年12月24日、111年1月10日持續建議休養1週至1個月，總計1個月又28日，其不能工作之損失應為66,768元。
另查系爭車輛，因被告之過失行為，受有交易上價值貶損33,000元及支出鑑定費3,000元，因此原告邱品妍向被告請求賠償之本件車輛交易價值減損及鑑定費共計36,000元。
原告邱品妍因本件車禍受有頭暈及頸部扭傷等傷害，影響其工作、生活之行動，於精神上造成無形痛苦，故請求被告連帶賠償60,000元精神慰撫金。
    """
    
    print("🧪 測試語義化法律文件處理系統")
    print("=" * 80)
    
    # 執行完整處理
    results = processor.process_case_semantically(test_case)
    
    # 顯示結果
    if "error" not in results:
        print("\\n📊 處理結果摘要:")
        summary = results.get("summary", {})
        print(f"   總金額: {summary.get('total_amount', 0):,}元")
        print(f"   求償項目數: {summary.get('claim_count', 0)}")
        print(f"   原告數量: {summary.get('plaintiff_count', 0)}")
        print(f"   被告數量: {summary.get('defendant_count', 0)}")
        
        print("\\n📝 生成的損害項目:")
        print(results.get("compensation", "未生成"))
        
        print("\\n🧠 生成的結論:")
        print(results.get("conclusion", "未生成"))
    else:
        print(f"❌ 處理失敗: {results['error']}")

if __name__ == "__main__":
    print("🚀 啟動語義化法律文件處理系統...")
    test_semantic_system()