#!/usr/bin/env python3
"""
KG_700_Semantic_Complete.py
完整的語義化法律文件處理系統 - 含互動界面
基於語義理解的通用法律文件處理，具備真正的泛化能力
"""

import os
import re
import json
import requests
import time
import sys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

# 導入必要模組
try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    from elasticsearch import Elasticsearch
    from neo4j import GraphDatabase
    from dotenv import load_dotenv
    FULL_MODE = True
    print("✅ 完整模式：所有檢索功能可用")
except ImportError as e:
    print(f"⚠️ 部分模組未安裝：{e}")
    print("⚠️ 使用簡化模式（僅LLM生成功能）")
    FULL_MODE = False

# 導入語義處理器
try:
    from KG_700_Semantic_Universal import SemanticLegalProcessor
    SEMANTIC_PROCESSOR_AVAILABLE = True
    print("✅ 語義處理器載入成功")
except ImportError:
    SEMANTIC_PROCESSOR_AVAILABLE = False
    print("⚠️ 語義處理器未找到")

# ===== 基本設定 =====
LLM_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:27b"

# ===== 檢索系統設定 =====
if FULL_MODE:
    # 載入環境變數
    env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
    load_dotenv(dotenv_path=env_path)
    
    # 嵌入模型設定
    BERT_MODEL = "shibing624/text2vec-base-chinese"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        TOKENIZER = AutoTokenizer.from_pretrained(BERT_MODEL)
        MODEL = AutoModel.from_pretrained(BERT_MODEL, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32).to(device)
        print("✅ 嵌入模型載入成功")
    except Exception as e:
        print(f"❌ 嵌入模型載入失敗: {e}")
        FULL_MODE = False
    
    # ES 和 Neo4j 連接
    try:
        ES_HOST = os.getenv("ELASTIC_HOST")
        ES_USER = os.getenv("ELASTIC_USER")
        ES_PASSWORD = os.getenv("ELASTIC_PASSWORD")
        ES_AUTH = (ES_USER, ES_PASSWORD)
        
        # 測試 ES 連接
        response = requests.get(f"{ES_HOST}/_cluster/health", auth=ES_AUTH, verify=False)
        if response.status_code != 200:
            raise Exception(f"ES連接失敗: {response.status_code}")
        
        NEO4J_DRIVER = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
        )
        CHUNK_INDEX = "legal_kg_chunks"
        print("✅ 資料庫連接成功")
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        FULL_MODE = False

class SemanticLawsuitGenerator:
    """基於語義理解的起訴狀生成器"""
    
    def __init__(self):
        self.semantic_processor = SemanticLegalProcessor() if SEMANTIC_PROCESSOR_AVAILABLE else None
        self.llm_url = LLM_URL
        self.model_name = DEFAULT_MODEL
        
    def call_llm(self, prompt: str, timeout: int = 180) -> str:
        """調用LLM"""
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
    
    def extract_sections_semantic(self, text: str) -> Dict[str, str]:
        """基於語義的段落提取"""
        print("📝 使用語義理解提取段落...")
        
        prompt = f"""你是法律文件分析專家，請將以下車禍案件描述分為三個標準段落。

【輸入文本】
{text}

【分段要求】
請將內容分為以下三個部分：
1. accident_facts - 事故發生緣由和經過
2. injury_description - 原告受傷情形和就醫過程  
3. damage_claims - 請求賠償的事實根據和損害項目

【輸出格式】
請輸出JSON格式：
{{
    "accident_facts": "事故經過內容...",
    "injury_description": "受傷情形內容...", 
    "damage_claims": "損害賠償內容..."
}}

請分析並輸出JSON："""

        try:
            response = self.call_llm(prompt, timeout=120)
            
            # 解析JSON回應
            try:
                sections = json.loads(response)
            except:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    sections = json.loads(json_match.group(0))
                else:
                    print("❌ 段落JSON解析失敗，使用基本分段")
                    return self._fallback_section_extraction(text)
            
            print("✅ 語義段落提取完成")
            return sections
            
        except Exception as e:
            print(f"❌ 語義段落提取失敗: {e}")
            return self._fallback_section_extraction(text)
    
    def _fallback_section_extraction(self, text: str) -> Dict[str, str]:
        """備用段落提取"""
        # 簡單的關鍵詞分段
        sections = {
            "accident_facts": "",
            "injury_description": "",
            "damage_claims": ""
        }
        
        paragraphs = text.split('\n')
        current_section = "accident_facts"
        
        for para in paragraphs:
            if any(keyword in para for keyword in ['受傷', '診斷', '醫院', '治療']):
                current_section = "injury_description"
            elif any(keyword in para for keyword in ['費用', '損失', '賠償', '請求']):
                current_section = "damage_claims"
            
            if para.strip():
                sections[current_section] += para + "\n"
        
        return sections
    
    def determine_case_type_semantic(self, text: str) -> str:
        """基於語義的案件分類"""
        print("🔍 使用語義理解進行案件分類...")
        
        prompt = f"""你是交通事故法律專家，請分析以下案件並判斷案件類型。

【案件描述】
{text}

【案件類型】
請從以下類型中選擇最適合的：
- 一般車禍 - 普通的車輛碰撞事故
- 機車事故 - 涉及機車的事故
- 行人事故 - 車輛撞擊行人
- 停車糾紛 - 停車相關的損害
- 其他交通事故 - 不屬於上述類型的交通事故

【輸出要求】
只需要回答案件類型，例如：一般車禍

請分析並回答："""

        try:
            response = self.call_llm(prompt, timeout=60)
            case_type = response.strip()
            print(f"✅ 案件分類: {case_type}")
            return case_type
        except Exception as e:
            print(f"❌ 語義分類失敗: {e}")
            return "一般車禍"
    
    def generate_semantic_lawsuit(self, user_input: str) -> Dict[str, Any]:
        """完整的語義化起訴狀生成"""
        print("🚀 開始語義化起訴狀生成...")
        print("=" * 80)
        
        results = {}
        
        try:
            # 1. 段落提取
            sections = self.extract_sections_semantic(user_input)
            results["sections"] = sections
            
            # 2. 當事人提取（使用語義處理器）
            if self.semantic_processor:
                parties = self.semantic_processor.extract_parties_semantically(user_input)
                results["parties"] = parties
                
                # 提取當事人姓名
                plaintiff_names = [p.name for p in parties["原告"] if p.confidence > 0.3]
                defendant_names = [p.name for p in parties["被告"] if p.confidence > 0.3]
                
                plaintiff_str = "、".join(plaintiff_names) if plaintiff_names else "原告"
                defendant_str = "、".join(defendant_names) if defendant_names else "被告"
                
                print(f"✅ 當事人提取: 原告={plaintiff_str}, 被告={defendant_str}")
            else:
                # 備用當事人提取
                plaintiff_str = "原告"
                defendant_str = "被告"
                print("⚠️ 使用備用當事人提取")
            
            # 3. 案件分類
            accident_facts = sections.get("accident_facts", user_input)
            case_type = self.determine_case_type_semantic(accident_facts)
            results["case_type"] = case_type
            
            # 4. 損害項目生成（使用語義處理器）
            damage_claims = sections.get("damage_claims", "")
            if self.semantic_processor and damage_claims:
                print("💰 使用語義處理器分析損害項目...")
                
                # 分析案例結構
                structure = self.semantic_processor.analyze_case_structure_semantically(damage_claims, parties)
                
                # 提取和分類金額
                amounts = self.semantic_processor.extract_amounts_semantically(damage_claims, structure)
                
                # 生成損害項目
                compensation = self.semantic_processor.generate_compensation_semantically(
                    damage_claims, structure, parties, amounts
                )
                results["compensation"] = compensation
                
                # 統計信息
                claim_amounts = [amt for amt in amounts if amt.amount_type == "claim_amount"]
                total_amount = sum(amt.amount for amt in claim_amounts)
                results["total_amount"] = total_amount
                
                print(f"✅ 損害項目生成完成，總計: {total_amount:,}元")
            else:
                # 備用損害項目生成
                compensation = self._generate_fallback_compensation(damage_claims)
                results["compensation"] = compensation
                results["total_amount"] = 0
                print("⚠️ 使用備用損害項目生成")
            
            # 5. 生成完整起訴狀
            lawsuit = self._generate_complete_lawsuit(
                plaintiff_str, defendant_str, sections, compensation, case_type
            )
            results["lawsuit"] = lawsuit
            
            print("✅ 語義化起訴狀生成完成！")
            return results
            
        except Exception as e:
            print(f"❌ 語義化生成失敗: {e}")
            results["error"] = str(e)
            return results
    
    def _generate_fallback_compensation(self, damage_text: str) -> str:
        """備用損害項目生成"""
        # 簡單的金額提取和格式化
        amount_pattern = r'(\d+(?:,\d{3})*(?:\.\d{2})?)\\s*([萬千]?)元'
        matches = re.finditer(amount_pattern, damage_text)
        
        result_lines = []
        chinese_nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        
        for i, match in enumerate(matches):
            if i < len(chinese_nums):
                amount_str = match.group(1).replace(',', '')
                unit = match.group(2)
                
                amount = float(amount_str)
                if unit == '萬':
                    amount *= 10000
                elif unit == '千':
                    amount *= 1000
                
                if amount >= 100:  # 排除小額
                    num = chinese_nums[i]
                    result_lines.append(f"（{num}）損害項目：{int(amount):,}元")
                    result_lines.append(f"原告因本次事故受有損害，請求賠償{int(amount):,}元。")
                    result_lines.append("")
        
        return '\\n'.join(result_lines) if result_lines else "未能提取損害項目"
    
    def _generate_complete_lawsuit(self, plaintiff: str, defendant: str, sections: Dict, 
                                 compensation: str, case_type: str) -> str:
        """生成完整起訴狀"""
        print("📄 生成完整起訴狀...")
        
        prompt = f"""你是台灣資深律師，請基於以下資訊生成完整的民事起訴狀。

【當事人資訊】
原告：{plaintiff}
被告：{defendant}
案件類型：{case_type}

【案件事實】
{sections.get('accident_facts', '')}

【受傷情形】
{sections.get('injury_description', '')}

【損害賠償項目】
{compensation}

【起訴狀格式要求】
請按照台灣民事起訴狀的標準格式生成，包含：
1. 標題：民事起訴狀
2. 當事人資訊（原告、被告）
3. 案由
4. 事實及理由（分為一、事實，二、理由）
5. 證據方法
6. 附屬文件
7. 法院管轄
8. 具狀人及日期

【重要要求】
- 使用正式的法律文書語言
- 事實部分要客觀描述
- 理由部分要有法律依據
- 格式要完整專業

請生成完整的起訴狀："""

        try:
            lawsuit = self.call_llm(prompt, timeout=300)
            print("✅ 完整起訴狀生成完成")
            return lawsuit
        except Exception as e:
            print(f"❌ 起訴狀生成失敗: {e}")
            return f"起訴狀生成失敗: {e}"

def interactive_generate_lawsuit():
    """互動式語義化起訴狀生成"""
    print("=" * 80)
    print("🏛️  車禍起訴狀生成器 - 語義化版本")
    print("=" * 80)
    print("👋 歡迎使用語義化起訴狀生成器！特色功能：")
    print("   🧠 語義理解：基於LLM的深度文本理解")
    print("   📊 智能分析：自動識別當事人、金額分類")
    print("   🎯 真正泛化：適應各種文本格式")
    print("   📄 完整生成：專業的法律文書")
    print()
    
    print("📝 使用方法：")
    print("   1. 請一次性輸入完整的案件資料")
    print("   2. 可以多行輸入，換行繼續")
    print("   3. 輸入完成後輸入 'END' 確認")
    print("   4. 輸入 'quit' 可退出程式")
    print()
    
    # 初始化語義生成器
    generator = SemanticLawsuitGenerator()
    
    print("📝 請輸入完整的車禍案件資料：")
    print("📋 建議包含以下內容：")
    print("   • 事故發生經過和責任歸屬")
    print("   • 原告受傷情形和就醫過程")
    print("   • 具體的損害項目和金額")
    print("   • 當事人姓名（原告、被告）")
    print()
    print("💡 提示：語義系統能理解自然語言，無需特定格式")
    print("=" * 60)
    print("🎯 請開始輸入（完成後輸入 'END' 確認）：")
    
    # 多行輸入模式
    user_input_lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() in ['END', 'QUIT', 'EXIT', '退出']:
                if line.strip().upper() in ['QUIT', 'EXIT'] or line.strip() == '退出':
                    print("👋 感謝使用語義化起訴狀生成器，再見！")
                    return
                break
            user_input_lines.append(line)
        except KeyboardInterrupt:
            print("\\n👋 用戶中斷，程序退出")
            return
        except EOFError:
            break
    
    user_query = '\\n'.join(user_input_lines).strip()
    
    if not user_query:
        print("⚠️ 請輸入有效的內容")
        return
    
    print("\\n🔄 語義化處理中...")
    
    try:
        # 使用語義生成器處理
        results = generator.generate_semantic_lawsuit(user_query)
        
        if "error" not in results:
            print("\\n" + "=" * 80)
            print("📄 生成的起訴狀")
            print("=" * 80)
            print(results.get("lawsuit", "未生成"))
            
            print("\\n" + "=" * 80)
            print("📊 分析摘要")
            print("=" * 80)
            print(f"案件類型：{results.get('case_type', '未分類')}")
            
            if "parties" in results:
                parties = results["parties"]
                plaintiffs = [p.name for p in parties["原告"] if p.confidence > 0.3]
                defendants = [p.name for p in parties["被告"] if p.confidence > 0.3]
                print(f"原告：{plaintiffs}")
                print(f"被告：{defendants}")
            
            total_amount = results.get("total_amount", 0)
            if total_amount > 0:
                print(f"請求總額：{total_amount:,}元")
            
            print("\\n✅ 語義化起訴狀生成完成！")
        else:
            print(f"❌ 處理失敗：{results['error']}")
            
    except Exception as e:
        print(f"❌ 程序執行錯誤：{str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """主程序"""
    try:
        print("🚀 啟動語義化法律文件處理系統...")
        print("=" * 80)
        print("📊 系統狀態檢查：")
        print(f"🌐 LLM服務：{'可用' if LLM_URL else '不可用'}")
        print(f"🔍 檢索功能：{'完整模式' if FULL_MODE else '簡化模式'}")
        print(f"🧠 語義處理器：{'可用' if SEMANTIC_PROCESSOR_AVAILABLE else '不可用'}")
        print()
        
        # 啟動互動界面
        interactive_generate_lawsuit()
        
    except KeyboardInterrupt:
        print("\\n\\n👋 用戶中斷，程序退出")
    except Exception as e:
        print(f"\\n❌ 程序執行錯誤：{str(e)}")

if __name__ == "__main__":
    main()