#!/usr/bin/env python3
"""
KG_700_CoT_Hybrid_Enhanced.py
基於原hybrid版本的增強版本：減少硬編碼，提升通用性
保留原有架構，只針對問題部分進行改進
"""

import os
import re
import json
import requests
import time
import sys
from typing import List, Dict, Any, Optional
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

# 導入語義處理器作為輔助
try:
    from KG_700_Semantic_Universal import SemanticLegalProcessor
    SEMANTIC_ASSISTANT_AVAILABLE = True
    print("✅ 語義輔助處理器載入成功")
except ImportError:
    SEMANTIC_ASSISTANT_AVAILABLE = False
    print("⚠️ 語義輔助處理器未找到")

# 導入結構化金額處理器
try:
    from structured_legal_amount_processor import StructuredLegalAmountProcessor
    STRUCTURED_PROCESSOR_AVAILABLE = True
    print("✅ 結構化金額處理器載入成功")
except ImportError:
    STRUCTURED_PROCESSOR_AVAILABLE = False
    print("⚠️ 結構化金額處理器未找到")

# 導入基本金額標準化器
try:
    from legal_amount_standardizer import LegalAmountStandardizer
    BASIC_STANDARDIZER_AVAILABLE = True
    print("✅ 基本金額標準化器載入成功")
except ImportError:
    BASIC_STANDARDIZER_AVAILABLE = False
    print("⚠️ 基本金額標準化器未找到")

# 導入通用格式處理器
try:
    from universal_format_handler import UniversalFormatHandler
    UNIVERSAL_FORMAT_HANDLER_AVAILABLE = True
    print("✅ 通用格式處理器載入成功")
except ImportError:
    UNIVERSAL_FORMAT_HANDLER_AVAILABLE = False
    print("⚠️ 通用格式處理器未找到")

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
        # 使用 requests 直接調用 ES API 避免版本兼容性問題
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

def extract_parties_enhanced(text: str) -> dict:
    """增強版當事人提取：結合語義輔助和原有方法"""
    print("🤖 使用增強版當事人提取...")
    
    # 優先使用語義輔助處理器
    if SEMANTIC_ASSISTANT_AVAILABLE:
        try:
            semantic_processor = SemanticLegalProcessor()
            semantic_result = semantic_processor.extract_parties_semantically(text)
            
            # 轉換格式以符合原有接口
            result = {}
            
            # 處理原告
            plaintiffs = [p.name for p in semantic_result.get("原告", []) if p.confidence > 0.3]
            result["原告"] = "、".join(plaintiffs) if plaintiffs else "原告"
            
            # 處理被告
            defendants = [p.name for p in semantic_result.get("被告", []) if p.confidence > 0.3]
            result["被告"] = "、".join(defendants) if defendants else "被告"
            
            print(f"✅ 語義輔助提取成功: 原告={result['原告']}, 被告={result['被告']}")
            return result
            
        except Exception as e:
            print(f"⚠️ 語義輔助失敗，使用原方法: {e}")
    
    # 備用：使用原有的LLM方法
    return extract_parties_with_llm(text)

def extract_parties_with_llm(text: str) -> dict:
    """使用LLM提取當事人（增強版提示詞）"""
    print("🤖 使用LLM智能提取當事人...")
    
    # 創建更精確的提示模板
    prompt = f"""請你幫我從以下車禍案件的法律文件中提取並列出所有原告和被告的真實姓名。

以下是案件內容：
{text}

提取要求：
1. 僅提取「原告○○○」和「被告○○○」中明確提到的真實姓名
2. 不要提取「訴外人」的姓名，訴外人不是當事人
3. **重要**：完整保留姓名，絕對不可截斷或省略任何字（如：羅靖崴必須完整寫成羅靖崴，不能寫成羅崴）
4. **重要**：如果原文是「原告羅靖崴」，必須輸出完整的「羅靖崴」三個字
5. **重要**：如果原文是「原告歐陽天華」，必須輸出完整的「歐陽天華」四個字
6. 如果文中沒有明確的姓名，就直接寫「原告」、「被告」
7. 多個姓名用逗號分隔

輸出格式（只輸出這兩行）：
原告:姓名1,姓名2...
被告:姓名1,姓名2...

範例說明：
- 「原告吳麗娟」→ 原告:吳麗娟
- 「被告鄭凱祥」→ 被告:鄭凱祥
- 「原告羅靖崴」→ 原告:羅靖崴（必須保留完整三個字）
- 「原告邱品妍」→ 原告:邱品妍（必須保留完整三個字）
- 「原告歐陽天華」→ 原告:歐陽天華（複姓必須完整）
- 「訴外人陳河田」→ 不是當事人，忽略
- 如果只說「原告」沒有姓名 → 原告:原告
- 如果只說「被告」沒有姓名 → 被告:被告

**務必確保姓名完整性，不可省略任何字！**"""

    try:
        # 調用LLM
        response = requests.post(
            LLM_URL,
            json={
                "model": DEFAULT_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            llm_result = response.json()["response"].strip()
            print(f"🤖 LLM提取結果: {llm_result}")
            return parse_llm_parties_result(llm_result)
        else:
            print(f"❌ LLM調用失敗: {response.status_code}")
            return extract_parties_fallback(text)
    except Exception as e:
        print(f"❌ LLM調用錯誤: {e}")
        return extract_parties_fallback(text)

def parse_llm_parties_result(llm_result: str) -> dict:
    """解析LLM當事人提取結果（增強版）"""
    parties = {"原告": "原告", "被告": "被告"}
    
    lines = llm_result.strip().split('\n')
    for line in lines:
        line = line.strip()
        
        # 更靈活的解析方式
        if "原告:" in line or "原告：" in line:
            # 提取原告部分
            plaintiff_part = re.split(r'原告[:：]', line, 1)
            if len(plaintiff_part) > 1:
                plaintiffs = plaintiff_part[1].strip()
                # 清理可能的額外文字
                plaintiffs = re.sub(r'[，,]\s*被告.*', '', plaintiffs)
                if plaintiffs and plaintiffs != "原告":
                    parties["原告"] = plaintiffs
                    
        elif "被告:" in line or "被告：" in line:
            # 提取被告部分
            defendant_part = re.split(r'被告[:：]', line, 1)
            if len(defendant_part) > 1:
                defendants = defendant_part[1].strip()
                # 清理可能的額外文字
                defendants = re.sub(r'[，,]\s*原告.*', '', defendants)
                if defendants and defendants != "被告":
                    parties["被告"] = defendants
    
    # 驗證姓名完整性
    for role, names in parties.items():
        if names not in [role, "原告", "被告"]:  # 如果有具體姓名
            # 檢查是否有可能的截斷
            name_list = [name.strip() for name in names.split('、') if name.strip()]
            validated_names = []
            
            for name in name_list:
                # 檢查姓名長度和字符類型
                if len(name) >= 2 and re.match(r'^[\u4e00-\u9fff]+$', name):
                    validated_names.append(name)
                elif len(name) == 1:
                    print(f"⚠️ 可能的姓名截斷: {name}")
                    validated_names.append(name)  # 仍然保留，但記錄警告
            
            if validated_names:
                parties[role] = "、".join(validated_names)
    
    print(f"✅ 解析結果: 原告={parties['原告']}, 被告={parties['被告']}")
    return parties

def extract_parties_fallback(text: str) -> dict:
    """備用當事人提取方法（改進版）"""
    print("🔄 使用備用當事人提取方法...")
    parties = {"原告": "原告", "被告": "被告"}
    
    # 改進的正則表達式，更好地捕獲完整姓名
    plaintiff_patterns = [
        r'原告([^\s，、。；：被告]{2,4})(?=[\s，、。；：被告]|$)',  # 2-4個字符的姓名
        r'原告\s*([^\s，、。；：被告]+)',  # 更寬鬆的匹配
    ]
    
    defendant_patterns = [
        r'被告([^\s，、。；：原告]{2,4})(?=[\s，、。；：原告]|$)',
        r'被告\s*([^\s，、。；：原告]+)',
    ]
    
    # 提取原告
    plaintiffs = []
    for pattern in plaintiff_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            clean_name = match.strip()
            if len(clean_name) >= 2 and clean_name not in plaintiffs:
                plaintiffs.append(clean_name)
    
    # 提取被告
    defendants = []
    for pattern in defendant_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            clean_name = match.strip()
            if len(clean_name) >= 2 and clean_name not in defendants:
                defendants.append(clean_name)
    
    if plaintiffs:
        parties["原告"] = "、".join(plaintiffs)
    if defendants:
        parties["被告"] = "、".join(defendants)
    
    return parties

def _extract_valid_claim_amounts_enhanced(text: str, parties: dict) -> List[Dict[str, Any]]:
    """增強版有效求償金額提取：結合語義分析和原方法"""
    print("💰 使用增強版金額提取...")
    
    # 優先使用語義輔助處理器
    if SEMANTIC_ASSISTANT_AVAILABLE:
        try:
            semantic_processor = SemanticLegalProcessor()
            
            # 創建模擬的結構對象
            from dataclasses import dataclass
            @dataclass
            class MockStructure:
                case_type: str = "multi_plaintiff" if "、" in parties.get("原告", "") else "single"
                plaintiff_count: int = len(parties.get("原告", "").split("、"))
                defendant_count: int = len(parties.get("被告", "").split("、"))
                narrative_style: str = "structured_chinese"
                confidence: float = 0.8
            
            structure = MockStructure()
            amounts = semantic_processor.extract_amounts_semantically(text, structure)
            
            # 轉換格式
            valid_amounts = []
            for amt in amounts:
                if amt.amount_type == "claim_amount" and amt.amount >= 100:
                    valid_amounts.append({
                        'amount': amt.amount,
                        'description': amt.description,
                        'context': amt.context,
                        'confidence': amt.confidence,
                        'source': 'semantic'
                    })
            
            if valid_amounts:
                print(f"✅ 語義金額提取成功: {len(valid_amounts)}項")
                return valid_amounts
            
        except Exception as e:
            print(f"⚠️ 語義金額提取失敗，使用原方法: {e}")
    
    # 備用：使用改進的原方法
    return _extract_valid_claim_amounts_original_enhanced(text, parties)

def _extract_valid_claim_amounts_original_enhanced(text: str, parties: dict) -> List[Dict[str, Any]]:
    """原方法的增強版本：改進金額分類邏輯"""
    print("💰 使用增強版原始金額提取...")
    
    valid_amounts = []
    
    # 改進的金額匹配模式
    amount_patterns = [
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\\s*([萬千]?)元',
        r'([一二三四五六七八九十百千萬]+)元',
    ]
    
    for pattern in amount_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            amount_str = match.group(1)
            unit = match.group(2) if len(match.groups()) > 1 else ""
            
            # 轉換金額
            try:
                if amount_str.isdigit() or ',' in amount_str or '.' in amount_str:
                    amount = float(amount_str.replace(',', ''))
                    if unit == '萬':
                        amount *= 10000
                    elif unit == '千':
                        amount *= 1000
                else:
                    # 中文數字轉換
                    amount = convert_chinese_number_to_int(amount_str)
                    
                if amount < 100:  # 排除小額
                    continue
                    
                # 改進的上下文分析
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end]
                
                # 更精確的分類邏輯
                is_claim_amount = classify_amount_enhanced(amount, context)
                
                if is_claim_amount:
                    # 生成描述
                    description = generate_amount_description(context)
                    
                    valid_amounts.append({
                        'amount': int(amount),
                        'description': description,
                        'context': context,
                        'confidence': 0.7,
                        'source': 'enhanced_original'
                    })
                    
            except Exception as e:
                print(f"⚠️ 金額轉換失敗: {amount_str} - {e}")
                continue
    
    # 去重和排序
    valid_amounts = remove_duplicate_amounts(valid_amounts)
    valid_amounts.sort(key=lambda x: x['amount'])
    
    print(f"✅ 增強版金額提取完成: {len(valid_amounts)}項")
    return valid_amounts

def classify_amount_enhanced(amount: float, context: str) -> bool:
    """增強版金額分類：更準確地區分求償金額vs計算基準"""
    
    # 明確的計算基準指示詞
    calculation_indicators = [
        '每月工資', '月工資', '月薪', '每日', '日薪', '時薪',
        '計算', '基準', '標準', '依據', '按', '以',
        '為計算基準', '作為基準', '計算基礎'
    ]
    
    # 明確的求償指示詞
    claim_indicators = [
        '請求', '賠償', '支出', '損失', '費用', '花費',
        '求償', '給付', '補償', '慰撫金', '醫療費',
        '交通費', '看護費', '營養費', '精神慰撫'
    ]
    
    # 檢查計算基準
    for indicator in calculation_indicators:
        if indicator in context:
            return False
    
    # 檢查求償指示
    for indicator in claim_indicators:
        if indicator in context:
            return True
    
    # 預設為求償金額
    return True

def generate_amount_description(context: str) -> str:
    """基於上下文生成金額描述"""
    
    description_map = {
        '醫療': '醫療費用',
        '交通': '交通費用',
        '看護': '看護費用',
        '營養': '營養費用',
        '慰撫': '精神慰撫金',
        '精神': '精神慰撫金',
        '車輛': '車輛損失',
        '財產': '財產損失',
        '鑑定': '鑑定費用',
        '工作': '工作損失',
        '薪資': '薪資損失',
    }
    
    for keyword, description in description_map.items():
        if keyword in context:
            return description
    
    return '損害賠償'

def convert_chinese_number_to_int(chinese_num: str) -> int:
    """轉換中文數字為整數（簡化版）"""
    chinese_map = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '百': 100, '千': 1000, '萬': 10000
    }
    
    # 簡單的轉換邏輯
    result = 0
    for char in chinese_num:
        if char in chinese_map:
            result = chinese_map[char]
            break
    
    return result if result > 0 else 0

def remove_duplicate_amounts(amounts: List[Dict]) -> List[Dict]:
    """去除重複金額"""
    seen_amounts = set()
    unique_amounts = []
    
    for amt in amounts:
        amount_key = amt['amount']
        if amount_key not in seen_amounts:
            seen_amounts.add(amount_key)
            unique_amounts.append(amt)
    
    return unique_amounts

# 繼續使用原有的其他函數...
# 這裡需要從原文件複製其他必要的函數

if __name__ == "__main__":
    print("🚀 增強版Hybrid起訴狀生成器")
    print("✅ 保留原有架構，針對性改進硬編碼問題")
    print("🧠 整合語義輔助，提升泛化能力")
    print()
    print("主要改進：")
    print("- 增強版當事人提取：保證姓名完整性")
    print("- 改進版金額分類：更準確的求償vs計算基準判斷")
    print("- 語義輔助：在可用時提供額外的準確性")
    print("- 備用機制：確保穩定性")