#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAG 案件分類器
基於規則和 LLM 的案件類型識別系統
"""

import re
import requests
from typing import Dict, List, Tuple
import time

# 案件類型對照表
CASE_TYPE_MAP = {
    # 特殊案型
    "§190動物案型": "單純原被告各一",
    "§188僱用人案型": "單純原被告各一", 
    "§187未成年案型": "單純原被告各一",
    
    # 複合案型的fallback
    "原被告皆數名+§188僱用人案型": "§188僱用人案型",
    "數名原告+§188僱用人案型": "§188僱用人案型",
    "數名被告+§188僱用人案型": "§188僱用人案型",
    "數名被告+§187未成年案型": "§187未成年案型", 
    "原被告皆數名+§187未成年案型": "§187未成年案型",
    "原被告皆數名+§190動物案型": "§190動物案型",
    
    # 基礎當事人數量類型
    "數名原告": "單純原被告各一",
    "數名被告": "單純原被告各一",
    "原被告皆數名": "單純原被告各一",
}

# 案件類型特徵關鍵詞
CASE_TYPE_KEYWORDS = {
    "§188僱用人案型": [
        "僱用人", "受僱人", "執行職務", "僱佣關係", "執行職務中",
        "司機", "駕駛人", "貨車", "計程車", "送貨", "配送",
        "公司車輛", "營業用", "工作期間"
    ],
    "§187未成年案型": [
        "未成年", "法定代理人", "監護人", "父母", "未滿", "歲",
        "學生", "高中", "國中", "小學", "幼兒園", "兒童"
    ],
    "§190動物案型": [
        "動物", "狗", "貓", "寵物", "飼主", "畜牧", "動物傷人",
        "咬傷", "抓傷", "動物攻擊", "飼養"
    ]
}

class CaseClassifier:
    """CAG 案件分類器"""
    
    def __init__(self, llm_url: str = "http://localhost:11434/api/generate", model_name: str = "gemma3:27b"):
        self.llm_url = llm_url
        self.model_name = model_name
        self.llm_available = self._check_llm_connection()
        
    def _check_llm_connection(self) -> bool:
        """檢查 LLM 連接"""
        try:
            response = requests.get(self.llm_url.replace('/api/generate', '/api/tags'), timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def extract_parties_info(self, text: str) -> Dict:
        """提取當事人信息"""
        print("🧠 分析當事人信息...")
        
        if self.llm_available:
            return self._extract_parties_with_llm(text)
        else:
            print("⚠️ LLM不可用，使用規則方法")
            return self._extract_parties_fallback(text)
    
    def _extract_parties_with_llm(self, text: str) -> Dict:
        """使用LLM提取當事人"""
        print("🤖 使用LLM智能提取當事人...")
        
        prompt = f"""請你幫我從以下車禍案件的法律文件中提取並列出所有原告和被告的真實姓名。

以下是案件內容：
{text}

提取要求：
1. 僅提取「原告○○○」和「被告○○○」中明確提到的真實姓名
2. 不要提取「訴外人」的姓名，訴外人不是當事人
3. 完整保留姓名，不可截斷（如：鄭凱祥不能寫成鄭祥）
4. 如果文中沒有明確的姓名，就直接寫「原告」、「被告」
5. 多個姓名用逗號分隔

輸出格式（只輸出這兩行）：
原告:姓名1,姓名2...
被告:姓名1,姓名2...

範例說明：
- 「原告吳麗娟」→ 原告:吳麗娟
- 「被告鄭凱祥」→ 被告:鄭凱祥  
- 「訴外人陳河田」→ 不是當事人，忽略
- 如果只說「原告」沒有姓名 → 原告:原告
- 如果只說「被告」沒有姓名 → 被告:被告"""

        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                llm_result = response.json()["response"].strip()
                print(f"🤖 LLM提取結果: {llm_result}")
                return self._parse_llm_parties_result(llm_result)
            else:
                print(f"❌ LLM調用失敗: {response.status_code}")
                return self._extract_parties_fallback(text)
                
        except Exception as e:
            print(f"❌ LLM提取異常: {e}")
            return self._extract_parties_fallback(text)
    
    def _parse_llm_parties_result(self, llm_result: str) -> Dict:
        """解析LLM的當事人提取結果"""
        result = {"原告": "原告", "被告": "被告", "被告數量": 1, "原告數量": 1}
        
        # 檢查LLM是否返回了無效的回應
        invalid_responses = ["請提供", "無法提取", "沒有提供", "由於您沒有"]
        if any(invalid in llm_result for invalid in invalid_responses):
            print("⚠️ LLM返回無效回應，使用fallback")
            return result
        
        lines = llm_result.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('原告:') or line.startswith('原告：'):
                plaintiff_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                if plaintiff_text:
                    # 分割多個原告
                    plaintiffs = [p.strip() for p in plaintiff_text.split(',') if p.strip()]
                    result["原告"] = "、".join(plaintiffs)
                    result["原告數量"] = len(plaintiffs)
            
            elif line.startswith('被告:') or line.startswith('被告：'):
                defendant_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                if defendant_text:
                    # 分割多個被告
                    defendants = [d.strip() for d in defendant_text.split(',') if d.strip()]
                    result["被告"] = "、".join(defendants)
                    result["被告數量"] = len(defendants)
        
        return result
    
    def _extract_parties_fallback(self, text: str) -> Dict:
        """當LLM提取失敗時的fallback方法（簡化版正則）"""
        print("⚠️ 使用fallback方法提取當事人...")
        result = {"原告": "原告", "被告": "被告", "被告數量": 1, "原告數量": 1}
        
        # 簡化的正則表達式提取
        plaintiffs = set()
        defendants = set()
        
        # 基本模式
        plaintiff_patterns = [
            r'原告([\u4e00-\u9fff]{2,4})',
            r'原告([甲乙丙丁戊])'
        ]
        
        defendant_patterns = [
            r'被告([\u4e00-\u9fff]{2,4})',
            r'被告([甲乙丙丁戊])'
        ]
        
        for pattern in plaintiff_patterns:
            matches = re.findall(pattern, text)
            plaintiffs.update(matches)
        
        for pattern in defendant_patterns:
            matches = re.findall(pattern, text)
            defendants.update(matches)
        
        # 清理和組合結果
        if plaintiffs:
            result["原告"] = "、".join(sorted(plaintiffs))
            result["原告數量"] = len(plaintiffs)
        elif "原告" in text:
            result["原告"] = "原告"
        
        if defendants:
            result["被告"] = "、".join(sorted(defendants))
            result["被告數量"] = len(defendants)
        elif "被告" in text:
            result["被告"] = "被告"
        
        return result
    
    def classify_case_type(self, text: str, parties_info: Dict = None) -> str:
        """分類案件類型"""
        print("🔍 分析案件類型...")
        
        if parties_info is None:
            parties_info = self.extract_parties_info(text)
        
        # 1. 基於關鍵詞識別特殊案型
        special_type = self._identify_special_case_type(text)
        
        # 2. 基於當事人數量分類
        party_type = self._classify_by_parties(parties_info)
        
        # 3. 組合最終案件類型
        final_type = self._combine_case_types(special_type, party_type)
        
        print(f"📋 案件分類結果: {final_type}")
        print(f"   特殊案型: {special_type if special_type else '無'}")
        print(f"   當事人類型: {party_type}")
        print(f"   原告: {parties_info['原告']} ({parties_info['原告數量']}人)")
        print(f"   被告: {parties_info['被告']} ({parties_info['被告數量']}人)")
        
        return final_type
    
    def _identify_special_case_type(self, text: str) -> str:
        """識別特殊案型"""
        for case_type, keywords in CASE_TYPE_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches >= 2:  # 至少匹配2個關鍵詞
                print(f"🎯 識別到特殊案型: {case_type} (匹配{matches}個關鍵詞)")
                return case_type
        return None
    
    def _classify_by_parties(self, parties_info: Dict) -> str:
        """基於當事人數量分類"""
        plaintiff_count = parties_info.get("原告數量", 1)
        defendant_count = parties_info.get("被告數量", 1)
        
        if plaintiff_count > 1 and defendant_count > 1:
            return "原被告皆數名"
        elif plaintiff_count > 1:
            return "數名原告"
        elif defendant_count > 1:
            return "數名被告"
        else:
            return "單純原被告各一"
    
    def _combine_case_types(self, special_type: str, party_type: str) -> str:
        """組合案件類型"""
        if special_type:
            if party_type != "單純原被告各一":
                combined = f"{party_type}+{special_type}"
                return combined
            else:
                return special_type
        else:
            return party_type
    
    def get_case_type_with_fallback(self, case_type: str) -> str:
        """獲取案件類型（包含fallback）"""
        return CASE_TYPE_MAP.get(case_type, case_type)
    
    def analyze_case(self, text: str) -> Dict:
        """完整分析案件（當事人+案件類型）"""
        print("🔬 開始案件分析...")
        
        # 提取當事人信息
        parties_info = self.extract_parties_info(text)
        
        # 分類案件類型
        case_type = self.classify_case_type(text, parties_info)
        
        # 獲取fallback類型
        fallback_type = self.get_case_type_with_fallback(case_type)
        
        result = {
            "parties": parties_info,
            "case_type": case_type,
            "fallback_type": fallback_type,
            "special_characteristics": self._analyze_special_characteristics(text)
        }
        
        print(f"✅ 案件分析完成")
        print(f"   主要類型: {case_type}")
        print(f"   Fallback類型: {fallback_type}")
        
        return result
    
    def _analyze_special_characteristics(self, text: str) -> List[str]:
        """分析案件特殊特徵"""
        characteristics = []
        
        # 檢查傷勢嚴重程度
        if any(keyword in text for keyword in ["重傷", "死亡", "植物人", "失能"]):
            characteristics.append("重大傷害")
        
        # 檢查財產損失
        if any(keyword in text for keyword in ["車輛", "修理", "財產", "物品"]):
            characteristics.append("財產損失")
        
        # 檢查精神損害
        if any(keyword in text for keyword in ["慰撫金", "精神", "痛苦"]):
            characteristics.append("精神損害")
        
        # 檢查醫療費用
        if any(keyword in text for keyword in ["醫療", "治療", "醫院", "復健"]):
            characteristics.append("醫療費用")
        
        return characteristics

def test_case_classifier():
    """測試案件分類器"""
    classifier = CaseClassifier()
    
    test_case = """一、事故發生緣由:
被告於108年9月12日早上8時36分許，騎乘車牌號碼000-000號普通重型機車，沿新北市中和區華中橋行駛時，本應注意變換車道時，應讓直行車先行，並注意安全距離，竟疏未注意而貿然變換車道，致擦撞右側原告所騎乘之車牌000-0000號普通重型機車（下稱系爭車輛），造成原告人車倒地。

二、原告受傷情形：
原告乙○○、丙○○因被告之過失致受有傷害，為治療上開傷勢而支出醫療費用，原告乙○○因傷無法工作達6個月。

三、請求賠償的事實根據：
原告主張醫療復健費用662,640元、工作損失249,840元、精神慰撫金2,300,000元，總計3,212,480元。"""
    
    result = classifier.analyze_case(test_case)
    print(f"\n測試結果: {result}")

if __name__ == "__main__":
    test_case_classifier()