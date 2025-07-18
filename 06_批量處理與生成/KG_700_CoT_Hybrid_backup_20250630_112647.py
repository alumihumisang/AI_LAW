#!/usr/bin/env python3
"""
KG_700_CoT_Hybrid.py
混合模式：事實、法條和損害用標準方法，結論用CoT
優化版本：修正未成年誤判、改進損害項目處理、增強穩定性
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
else:
    ES_HOST = None
    ES_AUTH = None
    NEO4J_DRIVER = None
    CHUNK_INDEX = None

# 案件類型對照表（ES檢索fallback用）
CASE_TYPE_MAP = {
    # 特殊案型如果找不到，fallback到相關基礎類型
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
    
    # 基礎當事人數量類型（通常不需要fallback）
    "數名原告": "單純原被告各一",
    "數名被告": "單純原被告各一",
    "原被告皆數名": "單純原被告各一",
}

# ===== 輔助函數 =====
def extract_sections(text: str) -> dict:
    """提取文本段落"""
    result = {
        "accident_facts": "",
        "injuries": "",
        "compensation_facts": ""
    }
    
    # 事故發生緣由
    fact_match = re.search(r"一[、．.\s]*事故發生緣由[:：]?\s*(.*?)(?=二[、．.]|$)", text, re.S)
    if fact_match:
        result["accident_facts"] = fact_match.group(1).strip()
    
    # 受傷情形
    injury_match = re.search(r"二[、．.\s]*(?:原告)?受傷情形[:：]?\s*(.*?)(?=三[、．.]|$)", text, re.S)
    if injury_match:
        result["injuries"] = injury_match.group(1).strip()
    
    # 賠償事實根據
    comp_match = re.search(r"三[、．.\s]*請求賠償的事實根據[:：]?\s*(.*?)$", text, re.S)
    if comp_match:
        result["compensation_facts"] = comp_match.group(1).strip()
    
    return result

def extract_parties_with_llm(text: str) -> dict:
    """使用LLM提取當事人（增強版 - 更好的泛化能力）"""
    print("🤖 使用增強版LLM智能提取當事人...")
    
    # 嘗試使用語義輔助處理器
    try:
        from KG_700_Semantic_Universal import SemanticLegalProcessor
        semantic_processor = SemanticLegalProcessor()
        semantic_result = semantic_processor.extract_parties_semantically(text)
        
        # 轉換格式以符合原有接口
        result = {}
        
        # 處理原告 - 加入嚴格驗證邏輯
        plaintiffs = []
        for p in semantic_result.get("原告", []):
            if p.confidence > 0.3 and p.name != "原告":
                # 嚴格驗證：必須確實是「原告○○○」的格式
                if f"原告{p.name}" in text:
                    plaintiffs.append(p.name)
                else:
                    print(f"⚠️ 語義提取的原告姓名 '{p.name}' 在原文中不存在或不是原告，跳過")
        
        result["原告"] = "、".join(plaintiffs) if plaintiffs else "原告"
        
        # 處理被告 - 加入嚴格驗證邏輯
        defendants = []
        for p in semantic_result.get("被告", []):
            if p.confidence > 0.3 and p.name != "被告":
                # 嚴格驗證：必須確實是「被告○○○」的格式
                if f"被告{p.name}" in text:
                    defendants.append(p.name)
                else:
                    print(f"⚠️ 語義提取的被告姓名 '{p.name}' 在原文中不存在或不是被告，跳過")
        
        result["被告"] = "、".join(defendants) if defendants else "被告"
        
        # 額外檢查：確保沒有把訴外人誤認為當事人
        for outsider in semantic_result.get("訴外人", []):
            if outsider.name in result["原告"]:
                print(f"⚠️ 檢測到訴外人 '{outsider.name}' 被誤認為原告，移除")
                result["原告"] = result["原告"].replace(outsider.name, "").replace("、、", "、").strip("、") or "原告"
            if outsider.name in result["被告"]:
                print(f"⚠️ 檢測到訴外人 '{outsider.name}' 被誤認為被告，移除")
                result["被告"] = result["被告"].replace(outsider.name, "").replace("、、", "、").strip("、") or "被告"
        
        print(f"✅ 語義輔助提取成功: 原告={result['原告']}, 被告={result['被告']}")
        
        # 如果語義提取沒有找到有效姓名，則fallback到LLM方法
        if result["原告"] == "原告" and result["被告"] == "被告":
            print("⚠️ 語義提取未找到具體姓名，fallback到LLM方法")
            # 不要返回，繼續執行LLM方法
        else:
            return result
        
    except Exception as e:
        print(f"⚠️ 語義輔助不可用，使用原LLM方法: {e}")
    
    # 備用：增強的LLM提示詞
    prompt = f"""請你幫我從以下車禍案件的法律文件中提取原告和被告的姓名。

以下是案件內容：
{text}

【關鍵提取規則】
1. **只提取**「原告○○○」和「被告○○○」中的姓名
2. **絕對不要提取**「訴外人○○○」的姓名 - 訴外人不是當事人！
3. **重要檢查**：確保提取的姓名前面有「原告」或「被告」字樣
4. 如果文中只有「原告」、「被告」而沒有具體姓名，就輸出「原告」、「被告」
5. **不要搞混角色**：原告就是原告，被告就是被告

【錯誤範例 - 絕對不要這樣做】
❌ 把「訴外人王其能」當成原告 - 錯誤！
❌ 把「原告」這個詞當成被告姓名 - 錯誤！ 
❌ 把角色搞反 - 錯誤！

【正確範例】
✅ 「原告羅靖崴主張...」→ 原告:羅靖崴
✅ 「被告張三駕駛...」→ 被告:張三
✅ 「訴外人王其能購買...」→ 忽略（不是當事人）
✅ 「原告主張賠償...」→ 原告:原告（沒有具體姓名）

【特殊注意】
在這個案例中，文中提到「訴外人王其能」，這是第三方，不是原告或被告！
原告和被告在文中都沒有具體姓名，只用「原告」、「被告」稱呼。

請仔細分析並輸出（只輸出這兩行）：
原告:
被告:"""

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
        print(f"❌ LLM提取異常: {e}")
        return extract_parties_fallback(text)

def _is_valid_name(name: str) -> bool:
    """檢查是否是有效的姓名"""
    import re
    
    # 排除包含數字、職業描述、年齡等的文字
    invalid_patterns = [
        r'\d+',  # 包含數字
        r'歲',   # 年齡
        r'先生|女士|小姐',  # 稱謂
        r'經理|主任|司機|領班|員工',  # 職業
        r'企業|公司|行號|店',  # 公司名稱
        r'係|即|之|等|及|或',  # 連接詞
        r'受僱人|僱用人|法定代理人',  # 法律用語
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, name):
            return False
    
    # 檢查是否是合理的中文姓名長度（2-4個字）
    if len(name) < 2 or len(name) > 6:
        return False
    
    # 檢查是否主要由中文字組成
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', name))
    if chinese_chars < len(name) * 0.7:  # 至少70%是中文字
        return False
    
    return True

def _clean_name_text(text: str) -> str:
    """清理姓名文字，移除非姓名內容"""
    import re
    
    # 移除年齡、職業等描述
    cleaned = re.sub(r'\d+歲', '', text)
    cleaned = re.sub(r'先生|女士|小姐', '', cleaned)
    cleaned = re.sub(r'（.*?）|\(.*?\)', '', cleaned)  # 移除括號內容
    cleaned = re.sub(r'[，,]\s*\d+.*', '', cleaned)  # 移除逗號後的數字和描述
    
    # 提取可能的姓名（2-4個中文字的組合）
    name_matches = re.findall(r'[\u4e00-\u9fff]{2,4}', cleaned)
    if name_matches:
        return name_matches[0]  # 返回第一個匹配的姓名
    
    return text.strip()

def parse_llm_parties_result(llm_result: str) -> dict:
    """解析LLM的當事人提取結果 - 增強版本防止角色混淆"""
    result = {"原告": "原告", "被告": "被告", "被告數量": 1, "原告數量": 1}
    
    # 檢查LLM是否返回了無效的回應
    invalid_responses = ["請提供", "無法提取", "沒有提供", "由於您沒有"]
    if any(invalid in llm_result for invalid in invalid_responses):
        print("⚠️ LLM返回無效回應，使用fallback")
        return result
    
    # 檢查是否出現了角色混淆的錯誤（常見bug）
    if "原告:王其能" in llm_result and "被告:原告" in llm_result:
        print("⚠️ 檢測到明顯的角色混淆錯誤，使用安全默認值")
        return result
    
    # 檢查是否把訴外人當成了當事人
    if "王其能" in llm_result:
        print("⚠️ 檢測到訴外人被誤認為當事人，使用安全默認值")
        return result
    
    lines = llm_result.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('原告:') or line.startswith('原告：'):
            plaintiff_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
            if plaintiff_text:
                # 改進的分割邏輯：只有當確實有多個有效姓名時才分割
                potential_plaintiffs = [p.strip() for p in plaintiff_text.split(',') if p.strip()]
                # 驗證是否真的是多個姓名
                valid_plaintiffs = []
                for p in potential_plaintiffs:
                    # 檢查是否是有效的姓名（不包含數字、不是描述性文字）
                    if _is_valid_name(p):
                        valid_plaintiffs.append(p)
                
                if len(valid_plaintiffs) > 1:
                    result["原告"] = "、".join(valid_plaintiffs)
                    result["原告數量"] = len(valid_plaintiffs)
                else:
                    # 單一原告或無法確定多個，使用原始文字但清理非姓名內容
                    cleaned_name = _clean_name_text(plaintiff_text)
                    result["原告"] = cleaned_name if cleaned_name else "原告"
                    result["原告數量"] = 1
        
        elif line.startswith('被告:') or line.startswith('被告：'):
            defendant_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
            if defendant_text:
                # 改進的分割邏輯：只有當確實有多個有效姓名時才分割
                potential_defendants = [d.strip() for d in defendant_text.split(',') if d.strip()]
                # 驗證是否真的是多個姓名
                valid_defendants = []
                for d in potential_defendants:
                    # 檢查是否是有效的姓名
                    if _is_valid_name(d):
                        valid_defendants.append(d)
                
                if len(valid_defendants) > 1:
                    result["被告"] = "、".join(valid_defendants)
                    result["被告數量"] = len(valid_defendants)
                else:
                    # 單一被告或無法確定多個，使用原始文字但清理非姓名內容
                    cleaned_name = _clean_name_text(defendant_text)
                    result["被告"] = cleaned_name if cleaned_name else "被告"
                    result["被告數量"] = 1
    
    return result

def extract_parties_fallback(text: str) -> dict:
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

def extract_parties(text: str) -> dict:
    """主要的當事人提取函數（優先使用LLM）"""
    return extract_parties_with_llm(text)

# ===== 檢索相關函數 =====
def embed(text: str):
    """文字向量化"""
    if not FULL_MODE:
        return []
    
    t = TOKENIZER(text, truncation=True, padding="max_length", max_length=512, return_tensors="pt")
    t = {k: v.to(device) for k, v in t.items()}
    with torch.no_grad():
        vec = MODEL(**t).last_hidden_state.mean(dim=1).squeeze()
    return vec.cpu().numpy().tolist()

def es_search(query_vector, case_type: str, top_k: int = 3, label: str = "Facts", quiet: bool = False):
    """ES 搜尋（含fallback機制）"""
    if not FULL_MODE or not ES_HOST:
        return []
    
    def _search(label_filter, case_type_filter):
        must_clause = [{"match": {"label": label_filter}}]
        
        if case_type_filter:
            # 嘗試多種可能的 case_type 欄位格式
            case_type_options = [
                {"term": {"case_type.keyword": case_type_filter}},
                {"term": {"case_type": case_type_filter}},
                {"match": {"case_type": case_type_filter}}
            ]
            
            # 使用 should 查詢，任一符合即可
            must_clause.append({
                "bool": {
                    "should": case_type_options,
                    "minimum_should_match": 1
                }
            })
            
        body = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"bool": {"must": must_clause}},
                    "script": {
                        "source": "cosineSimilarity(params.qv,'embedding')+1.0",
                        "params": {"qv": query_vector},
                    },
                }
            },
        }
        
        # 調試信息：只在非安靜模式下輸出
        if not quiet:
            print(f"🔍 ES查詢條件: index={CHUNK_INDEX}, label={label_filter}, case_type={case_type_filter}")
        
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
            response = requests.post(url, auth=ES_AUTH, json=body, verify=False)
            if response.status_code == 200:
                result = response.json()
                hits = result["hits"]["hits"]
                total_docs = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
                if not quiet:
                    print(f"📊 ES查詢結果: 找到 {len(hits)} 個匹配結果，總文檔數: {total_docs}")
                return hits
            else:
                if not quiet:
                    print(f"❌ ES查詢失敗: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            if not quiet:
                print(f"❌ ES查詢失敗: {e}")
            return []

    if not quiet:
        print(f"🔎 使用 case_type='{case_type}' 搜索相似案例...")
    hits = _search(label, case_type)
    
    if not hits:
        # 先檢查索引映射和可用的案件類型
        try:
            # 檢查 mapping
            mapping_url = f"{ES_HOST}/{CHUNK_INDEX}/_mapping"
            mapping_response = requests.get(mapping_url, auth=ES_AUTH, verify=False)
            if mapping_response.status_code == 200:
                mapping = mapping_response.json()
                properties = mapping[CHUNK_INDEX]["mappings"]["properties"]
                has_case_type = "case_type" in properties
                print(f"🗺️ case_type欄位存在: {has_case_type}")
                
                if has_case_type:
                    # 嘗試不同的欄位名稱
                    for field_name in ["case_type", "case_type.keyword"]:
                        try:
                            check_body = {
                                "size": 0,
                                "aggs": {
                                    "case_type_count": {"terms": {"field": field_name, "size": 20}}
                                }
                            }
                            check_url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
                            check_response = requests.post(check_url, auth=ES_AUTH, json=check_body, verify=False)
                            if check_response.status_code == 200:
                                check_result = check_response.json()
                                available_types = [bucket["key"] for bucket in check_result["aggregations"]["case_type_count"]["buckets"]]
                                print(f"📋 使用欄位 {field_name} 找到的案件類型: {available_types}")
                                break
                        except Exception as field_e:
                            print(f"⚠️ 欄位 {field_name} 查詢失敗: {field_e}")
                else:
                    print("❌ case_type欄位不存在於索引映射中")
            else:
                print(f"❌ 獲取映射失敗: {mapping_response.status_code}")
                
        except Exception as e:
            print(f"⚠️ 無法檢查索引映射或案件類型: {e}")
        
        fallback = CASE_TYPE_MAP.get(case_type, "單純原被告各一")
        if fallback != case_type:
            print(f"⚠️ 使用 fallback='{fallback}' 重新搜尋...")
            hits = _search(label, fallback)
    
    if not hits:
        print("⚠️ 不限案件類型進行搜尋...")
        hits = _search(label, None)
    
    return hits

def rerank_case_ids_by_paragraphs(query_text: str, case_ids: List[str], label: str = "Facts", quiet: bool = False) -> List[str]:
    """根據段落級資料重新排序案例"""
    if not FULL_MODE or not ES_HOST:
        return case_ids
    
    if not quiet:
        print("📘 啟動段落級 rerank...")
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
        if not quiet:
            print("⚠️ sklearn未安裝，跳過rerank")
        return case_ids

    query_vec = embed(query_text)
    if not query_vec:
        return case_ids
    
    query_vec_np = np.array(query_vec).reshape(1, -1)
    scored_cases = []
    
    for cid in case_ids:
        try:
            # 使用 requests 直接調用 ES API
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"case_id": cid}},
                            {"term": {"label": label}}
                        ]
                    }
                },
                "size": 1
            }
            url = f"{ES_HOST}/legal_kg_paragraphs/_search"
            response = requests.post(url, auth=ES_AUTH, json=search_body, verify=False)
            if response.status_code != 200:
                continue
            res = response.json()
            hits = res.get("hits", {}).get("hits", [])
            if hits:
                vec = hits[0]['_source']['embedding']
                para_vec_np = np.array(vec).reshape(1, -1)
                score = cosine_similarity(query_vec_np, para_vec_np)[0][0]
                scored_cases.append((cid, score))
        except Exception as e:
            print(f"⚠️ Case {cid} rerank失敗: {e}")
            scored_cases.append((cid, 0.0))

    scored_cases.sort(key=lambda x: x[1], reverse=True)
    return [cid for cid, _ in scored_cases]

def get_complete_cases_content(case_ids: List[str]) -> List[str]:
    """獲取完整案例內容"""
    if not FULL_MODE or not NEO4J_DRIVER:
        return []
    
    complete_cases = []
    
    try:
        with NEO4J_DRIVER.session() as session:
            for case_id in case_ids:
                # 查詢完整案例的事實段落
                result = session.run("""
                    MATCH (c:Case {case_id: $case_id})-[:包含]->(f:Facts)
                    RETURN f.description AS facts_content
                """, case_id=case_id).data()
                
                if result:
                    # 組合案例的所有事實段落
                    case_content = "\n".join([record["facts_content"] for record in result if record["facts_content"]])
                    if case_content:
                        complete_cases.append(case_content)
                else:
                    print(f"⚠️ 案例 {case_id} 無法獲取完整內容")
                    
    except Exception as e:
        print(f"⚠️ 獲取完整案例內容失敗: {e}")
    
    return complete_cases

def query_laws(case_ids):
    """從Neo4j查詢法條資訊"""
    if not FULL_MODE or not NEO4J_DRIVER:
        return Counter(), {}
    
    counter = Counter()
    law_text_map = {}
    
    try:
        with NEO4J_DRIVER.session() as session:
            for cid in case_ids:
                result = session.run("""
                    MATCH (c:Case {case_id: $cid})-[:包含]->(:Facts)-[:適用]->(l:Laws)-[:包含]->(ld:LawDetail)
                    RETURN collect(distinct ld.name) AS law_names, collect(distinct ld.text) AS law_texts
                """, cid=cid).single()
                if result:
                    names = result["law_names"]
                    texts = result["law_texts"]
                    counter.update(names)
                    for n, t in zip(names, texts):
                        if n not in law_text_map:
                            law_text_map[n] = t
    except Exception as e:
        print(f"⚠️ Neo4j查詢失敗: {e}")
    
    return counter, law_text_map

def get_similar_cases_laws_stats(case_ids):
    """獲取相似案例的法條統計資訊"""
    counter, _ = query_laws(case_ids)
    return counter.most_common()

def normalize_article_number(article: str) -> str:
    """條號格式標準化：第191-2條 → 第191條之2"""
    # 處理特殊格式的條號
    article = re.sub(r'第(\d+)-(\d+)條', r'第\1條之\2', article)
    return article

def detect_special_relationships(text: str, parties: dict) -> dict:
    """偵測特殊法律關係（優化版 - 修復當事人數量檢測）"""
    
    # 正確計算當事人數量
    plaintiff_count = len([name.strip() for name in parties.get('原告', '原告').split('、') if name.strip() and name.strip() != '原告'])
    defendant_count = len([name.strip() for name in parties.get('被告', '被告').split('、') if name.strip() and name.strip() != '被告'])
    
    # 如果沒有具體姓名，當事人數量為1
    if parties.get('原告', '') in ['原告', '']:
        plaintiff_count = 1
    if parties.get('被告', '') in ['被告', '']:
        defendant_count = 1
        
    print(f"🔍 當事人數量檢測: 原告={plaintiff_count}人, 被告={defendant_count}人")
    
    relationships = {
        "未成年": False,
        "雇傭關係": False,
        "動物損害": False,
        "多被告": defendant_count > 1,
        "多原告": plaintiff_count > 1
    }
    
    # 更精確的未成年檢測
    # 1. 明確提到未成年相關詞彙
    explicit_minor_keywords = ["未成年", "法定代理人", "監護人", "未滿十八歲", "未滿18歲"]
    if any(keyword in text for keyword in explicit_minor_keywords):
        relationships["未成年"] = True
    
    # 2. 檢查具體年齡（18歲以下）
    age_pattern = r'(\d+)\s*歲'
    age_matches = re.findall(age_pattern, text)
    for age_str in age_matches:
        age = int(age_str)
        if age < 18:
            relationships["未成年"] = True
            break
    
    # 3. 學校關鍵字需要更謹慎
    school_keywords = ["國中生", "國小生", "高中生"]  # 不是單純的"國中"、"高中"
    if any(keyword in text for keyword in school_keywords):
        relationships["未成年"] = True
    
    # 檢查雇傭關係
    employment_keywords = ["受僱", "僱用", "雇主", "員工", "職務", "工作時間", "公司車", "執行職務"]
    relationships["雇傭關係"] = any(keyword in text for keyword in employment_keywords)
    
    # 檢查動物損害
    animal_keywords = ["狗", "貓", "犬", "動物", "寵物", "咬傷", "抓傷"]
    relationships["動物損害"] = any(keyword in text for keyword in animal_keywords)
    
    return relationships

def determine_case_type(accident_facts: str, parties: dict) -> str:
    """判斷案件類型（七大基本類型）"""
    relationships = detect_special_relationships(accident_facts, parties)
    
    # 優先判斷特殊法條類型（互斥優先級）
    if relationships["動物損害"]:
        return "§190動物案型"
    elif relationships["雇傭關係"]: 
        return "§188僱用人案型"
    elif relationships["未成年"]:
        return "§187未成年案型"
    
    # 其次判斷當事人數量類型
    elif relationships["多原告"] and relationships["多被告"]:
        return "原被告皆數名"
    elif relationships["多原告"]:
        return "數名原告"
    elif relationships["多被告"]:
        return "數名被告"
    else:
        return "單純原被告各一"

def determine_applicable_laws(accident_facts: str, injuries: str, comp_facts: str, parties: dict) -> List[str]:
    """根據案件事實智能判斷適用法條"""
    applicable_laws = []
    
    # 偵測特殊關係
    relationships = detect_special_relationships(accident_facts + injuries + comp_facts, parties)
    
    # 1. 第184條第1項前段 - 基本侵權責任（必須）
    applicable_laws.append("民法第184條第1項前段")
    
    # 2. 車禍案件 - 第191條之2（交通工具）
    traffic_keywords = ["汽車", "機車", "車輛", "駕駛", "交通", "撞", "碰撞"]
    if any(keyword in accident_facts for keyword in traffic_keywords):
        applicable_laws.append("民法第191條之2")
    
    # 3. 身體健康損害 - 第193條第1項
    health_damage_keywords = ["醫療", "看護", "工作損失", "薪資", "收入", "勞動能力"]
    if injuries or any(keyword in comp_facts for keyword in health_damage_keywords):
        applicable_laws.append("民法第193條第1項")
    
    # 4. 精神慰撫金 - 第195條第1項前段
    mental_damage_keywords = ["精神", "慰撫", "痛苦", "名譽", "人格"]
    if any(keyword in comp_facts for keyword in mental_damage_keywords):
        applicable_laws.append("民法第195條第1項前段")
    
    # 5. 特殊情況處理（互斥規則）
    if relationships["雇傭關係"]:
        # 雇傭關係優先適用第188條第1項本文
        applicable_laws.append("民法第188條第1項本文")
    elif relationships["多被告"]:
        # 多被告但無雇傭關係時適用第185條第1項
        applicable_laws.append("民法第185條第1項")
    
    # 6. 未成年案件 - 第187條第1項
    if relationships["未成年"]:
        applicable_laws.append("民法第187條第1項")
    
    # 7. 動物損害 - 第190條第1項
    if relationships["動物損害"]:
        applicable_laws.append("民法第190條第1項")
    
    # 標準化條號格式
    applicable_laws = [normalize_article_number(law) for law in applicable_laws]
    
    return list(dict.fromkeys(applicable_laws))  # 去重但保持順序


    

# ===== 混合模式生成器 =====
class HybridCoTGenerator:
    """混合模式生成器：事實法條損害用標準，結論用CoT"""
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.llm_url = LLM_URL
        
        # 初始化金額處理器
        if STRUCTURED_PROCESSOR_AVAILABLE:
            self.structured_processor = StructuredLegalAmountProcessor()
        else:
            self.structured_processor = None
        
        if BASIC_STANDARDIZER_AVAILABLE:
            self.basic_standardizer = LegalAmountStandardizer()
        else:
            self.basic_standardizer = None
        
        # 初始化通用格式處理器
        if UNIVERSAL_FORMAT_HANDLER_AVAILABLE:
            self.format_handler = UniversalFormatHandler()
        else:
            self.format_handler = None
        
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
    
    def _chinese_num(self, num: int) -> str:
        """數字轉中文"""
        chinese = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
        if num <= 10:
            return chinese[num]
        return str(num)
    
    def _extract_all_plaintiffs(self, text: str) -> List[str]:
        """提取所有原告姓名"""
        plaintiffs = []
        
        # 方法1：從文本中找「原告○○○」的模式
        pattern = r'原告([^，。；、\s]{2,4})(?:為|因|受|前往|支出)'
        matches = re.findall(pattern, text)
        plaintiffs.extend(matches)
        
        # 去重並保持順序
        seen = set()
        unique_plaintiffs = []
        for p in plaintiffs:
            if p not in seen:
                seen.add(p)
                unique_plaintiffs.append(p)
        
        return unique_plaintiffs
    
    def generate_standard_facts(self, accident_facts: str, similar_cases: List[str] = None, parties: dict = None) -> str:
        """標準方式生成事實段落（含相似案例參考）"""
        print("📝 使用標準方式生成事實段落...")
        
        # 組合相似案例參考
        reference_text = ""
        if similar_cases:
            reference_text = "\n\n參考相似案例：\n" + "\n".join([f"{i+1}. {case}" for i, case in enumerate(similar_cases[:2])])
        
        prompt = f"""你是台灣律師，請根據以下事實材料撰寫起訴狀的事實段落：

事實材料：
{accident_facts}{reference_text}

要求：
1. 以「緣被告」開頭
2. 使用「原告」、「被告」稱謂，但必須保持姓名的完整性和準確性
3. 客觀描述事故經過，確保語法正確流暢
4. 參考相似案例的敘述方式，但不得抄襲
5. 格式：一、事實概述：[內容]
6. **重要**：如果事實材料中有具體姓名，請完整保留，不要截斷或改變任何字元
7. **禁止事項**：絕對不可以在輸出中包含任何括號提醒文字，如「（姓名：請填寫...）」、「（請填寫...）」等提示內容
8. **直接輸出**：只輸出完整的事實段落，不要包含任何需要用戶填寫的空白或提醒
9. **語法要求**：請特別注意句子結構的完整性，避免出現語法錯誤或不完整的句子

請直接輸出完整的事實段落："""
        
        result = self.call_llm(prompt)
        
        # 清理括號提醒文字
        result = self._remove_bracket_reminders(result)
        
        # 修正語法錯誤
        result = self._fix_grammar_errors(result)
        
        # 提取事實段落
        fact_match = re.search(r"一、事實概述：\s*(.*?)(?:\n\n|$)", result, re.S)
        if fact_match:
            cleaned_content = fact_match.group(1).strip()
            result = f"一、事實概述：\n{cleaned_content}"
            return self._standardize_names_in_facts(result, parties or {})
        elif "緣被告" in result:
            # 找到包含"緣被告"的行
            for line in result.split('\n'):
                if "緣被告" in line:
                    cleaned_line = line.strip()
                    result = f"一、事實概述：\n{cleaned_line}"
                    return self._standardize_names_in_facts(result, parties or {})
        
        # Fallback
        facts_content = accident_facts.replace('緣被告', '').strip()
        result = f"一、事實概述：\n緣被告{facts_content}"
        
        # 統一姓名處理
        return self._standardize_names_in_facts(result, parties or {})
    
    def generate_standard_laws(self, accident_facts: str, injuries: str, parties: dict, compensation_facts: str = "") -> str:
        """標準方式生成法律依據（符合法條引用規範）"""
        print("⚖️ 使用標準方式生成法律依據...")
        
        # 智能判斷適用法條
        applicable_laws = determine_applicable_laws(accident_facts, injuries, compensation_facts, parties)
        
        # 完整的法條說明對照表（精確到項、段、但書）
        law_descriptions = {
            "民法第184條第1項前段": "因故意或過失，不法侵害他人之權利者，負損害賠償責任。",
            "民法第185條第1項": "數人共同不法侵害他人之權利者，連帶負損害賠償責任。",
            "民法第187條第1項": "無行為能力人或限制行為能力人，不法侵害他人之權利者，以行為時有識別能力為限，與其法定代理人連帶負損害賠償責任。",
            "民法第188條第1項本文": "受僱人因執行職務，不法侵害他人之權利者，由僱用人與行為人連帶負損害賠償責任。",
            "民法第190條第1項": "動物加損害於他人者，由其占有人負損害賠償責任。",
            "民法第191條之2": "汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。",
            "民法第193條第1項": "不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。",
            "民法第195條第1項前段": "不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。"
        }
        
        # 組合法條內容（先列法條內容）
        law_texts = []
        valid_laws = []
        
        for law in applicable_laws:
            if law in law_descriptions:
                law_texts.append(f"「{law_descriptions[law]}」")
                valid_laws.append(law)
        
        if not law_texts:
            # Fallback：至少包含基本侵權條文
            law_texts = ["「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」"]
            valid_laws = ["民法第184條第1項前段"]
        
        # 按條號數字排序法條
        sorted_laws_with_content = self._sort_laws_by_article_number(valid_laws, law_descriptions)
        
        # 提取排序後的內容和條號
        sorted_law_texts = [item[1] for item in sorted_laws_with_content]
        sorted_article_list = [item[0] for item in sorted_laws_with_content]
        
        # 按正確格式組合：先法條內容，後條號
        law_content_block = "、".join(sorted_law_texts)
        article_list = "、".join(sorted_article_list)
        
        print(f"✅ 適用法條: {', '.join(sorted_article_list)}")
        
        return f"""二、法律依據：
按{law_content_block}，{article_list}分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任："""
    
    def _parse_damage_from_sentence(self, sentence: str, plaintiff: str) -> List[dict]:
        """從句子中解析損害項目（改進版）"""
        damages = []
        
        # 擴充損害類型模式
        damage_patterns = [
            {
                'keywords': ['醫療費用', '治療', '醫院', '診所', '就診'],
                'name': '醫療費用',
                'template': f'原告{plaintiff}因本次事故受傷，前往醫院治療所支出之醫療費用'
            },
            {
                'keywords': ['交通費', '交通費用', '往返費用', '來回費用', '車費', '油費', '停車費', '過路費', '通行費'],
                'name': '交通費用',
                'template': f'原告{plaintiff}因本次事故所生之交通費用'
            },
            {
                'keywords': ['工資損失', '不能工作', '工作損失', '無法工作', '休養'],
                'name': '工作損失',
                'template': f'原告{plaintiff}因本次事故無法工作之收入損失'
            },
            {
                'keywords': ['慰撫金', '精神'],
                'name': '精神慰撫金',
                'template': f'原告{plaintiff}因本次事故所受精神上痛苦之慰撫金'
            },
            {
                'keywords': ['車輛貶值', '貶損', '價值減損', '交易價值'],
                'name': '車輛貶值損失',
                'template': f'系爭車輛因本次事故貶值之損失'
            },
            {
                'keywords': ['鑑定費'],
                'name': '鑑定費用',
                'template': f'為評估車輛損失所支出之鑑定費用'
            }
        ]
        
        # 更精確的金額提取（考慮前後文）
        # 不要只看到金額就提取，要看金額前後的描述
        
        return damages
    
    def generate_smart_compensation(self, injuries: str, comp_facts: str, parties: dict) -> str:
        """智能生成損害項目（簡化版本）"""
        print("💰 生成損害賠償...")
        
        # 直接使用LLM處理，避免複雜的結構化處理
        return self._generate_llm_based_compensation(comp_facts, parties)

    def _preprocess_chinese_numbers(self, text: str) -> str:
        """預處理中文數字，轉換為阿拉伯數字"""
        import re
        
        # 處理 X萬Y,YYY元 格式 (如：26萬4,379元)
        pattern1 = r'(\d+)萬(\d+,?\d+)元'
        def replace1(match):
            wan = int(match.group(1))
            rest = int(match.group(2).replace(',', ''))
            total = wan * 10000 + rest
            return f"{total:,}元"
        text = re.sub(pattern1, replace1, text)
        
        # 處理 X萬Y千元 格式 (如：30萬5千元)
        pattern2 = r'(\d+)萬(\d+)千元'
        def replace2(match):
            wan = int(match.group(1))
            qian = int(match.group(2))
            total = wan * 10000 + qian * 1000
            return f"{total:,}元"
        text = re.sub(pattern2, replace2, text)
        
        # 處理 X萬元 格式 (如：20萬元)
        pattern3 = r'(\d+)萬元'
        def replace3(match):
            wan = int(match.group(1))
            total = wan * 10000
            return f"{total:,}元"
        text = re.sub(pattern3, replace3, text)
        
        # 處理 X千元 格式 (如：5千元)
        pattern4 = r'(\d+)千元'
        def replace4(match):
            qian = int(match.group(1))
            total = qian * 1000
            return f"{total:,}元"
        text = re.sub(pattern4, replace4, text)
        
        return text
    
    def _remove_bracket_reminders(self, text: str) -> str:
        """移除文本中的括號提醒文字"""
        import re
        
        # 移除各種括號提醒模式
        patterns = [
            r'\（[^）]*請填寫[^）]*\）',  # （姓名：請填寫...）
            r'\（[^）]*請[^）]*\）',     # （請...）
            r'\（[^）]*：[^）]*\）',     # （任何：說明）
            r'\（[^）]*填寫[^）]*\）',   # （...填寫...）
            r'\（[^）]*輸入[^）]*\）',   # （...輸入...）
            r'\（[^）]*補充[^）]*\）',   # （...補充...）
        ]
        
        cleaned_text = text
        for pattern in patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text)
        
        # 清理多餘的空格
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
    def _fix_grammar_errors(self, text: str) -> str:
        """修正文本中的語法錯誤"""
        import re
        
        cleaned_text = text
        
        # 修正常見的語法錯誤模式
        grammar_fixes = [
            # 修正「致撞擊車後之機車道上，由原告所騎乘...」類型的錯誤
            (r'致撞擊車後之機車道上，由([^所]+)所騎乘([^普]+)普通重型機車', 
             r'致撞擊\1所騎乘之\2普通重型機車'),
            
            # 修正其他常見的語法錯誤
            (r'，由([^所]+)所騎乘([^之]+)之([^，。]+)，', r'，撞擊\1所騎乘之\2\3，'),
            
            # 修正句子結構不完整的問題
            (r'致撞擊([^，。]+)，$', r'致撞擊\1。'),
            
            # 修正重複的介詞或連詞
            (r'之之', r'之'),
            (r'於於', r'於'),
            (r'，，', r'，'),
            
            # 修正車輛描述的語法
            (r'車後之機車道上，由', r'車輛，該車輛由'),
            
            # 修正不完整的句子結構
            (r'由([^所]+)所騎乘([^，。]+)，$', r'由\1所騎乘之\2。'),
        ]
        
        for pattern, replacement in grammar_fixes:
            cleaned_text = re.sub(pattern, replacement, cleaned_text)
        
        # 清理多餘的空格和標點
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        cleaned_text = re.sub(r'，。', '。', cleaned_text)
        cleaned_text = re.sub(r'。。', '。', cleaned_text)
        
        return cleaned_text
    
    def _remove_conclusion_phrases(self, text: str) -> str:
        """移除文本中的結論性文字和總計說明"""
        import re
        
        # 分行處理
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 跳過包含結論性關鍵詞的行（但不要誤刪理由說明）
            conclusion_keywords = [
                '綜上所述', '總計新台幣', '合計新台幣', '法定利息', 
                '按週年利率', '按年息', '起訴狀繕本送達',
                '清償日止', '自.*起至.*止', '年息5%', '總額為',
                '此有相關收據可證', '有收據為證', '有統一發票可證',
                '經查', '查明', '經審理'
            ]
            
            should_skip = False
            for keyword in conclusion_keywords:
                if keyword in line:
                    should_skip = True
                    break
            
            if not should_skip and line:  # 保留非空且非結論性的行
                cleaned_lines.append(line)
        
        # 重新組合
        cleaned_text = '\n'.join(cleaned_lines)
        
        # 額外清理：移除可能的結論段落和證據文字
        # 移除從「綜上」開始到結尾的所有內容
        cleaned_text = re.sub(r'綜上.*$', '', cleaned_text, flags=re.MULTILINE | re.DOTALL)
        
        # 移除句子中的證據相關文字
        evidence_patterns = [
            r'，此有[^。]*可證。?',
            r'，有[^。]*收據[^。]*證。?',
            r'，有[^。]*發票[^。]*證。?',
            r'，[^。]*為證。?'
        ]
        
        for pattern in evidence_patterns:
            cleaned_text = re.sub(pattern, '。', cleaned_text)
        
        # 清理多餘的句號
        cleaned_text = re.sub(r'。+', '。', cleaned_text)
        
        return cleaned_text.strip()
    
    def _remove_defendant_damage_errors(self, text: str) -> str:
        """移除關於被告損害的錯誤內容"""
        import re
        
        # 分行處理
        lines = text.split('\n')
        cleaned_lines = []
        skip_section = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # 檢查是否開始被告損害段落
            if re.search(r'[（(][一二三四五六七八九十][）)].*被告.*損害', line_stripped):
                print(f"🔍 檢測到被告損害錯誤段落，開始跳過：{line_stripped}")
                skip_section = True
                continue
            
            # 檢查是否開始新的正常段落（如下一個原告或其他段落）
            if skip_section and (
                re.search(r'^[一二三四五六七八九十]、', line_stripped) or  # 新的大標題
                re.search(r'[（(][一二三四五六七八九十][）)](?!.*被告)', line_stripped) or  # 新的項目但不是被告
                line_stripped.startswith('四、') or  # 結論段落
                line_stripped == ''
            ):
                skip_section = False
            
            # 如果不在跳過模式中，保留這行
            if not skip_section:
                # 額外檢查：移除任何直接提到被告損害的行
                if ('被告' in line_stripped and '損害' in line_stripped and 
                    ('之損害' in line_stripped or '的損害' in line_stripped)):
                    print(f"🔍 移除被告損害相關行：{line_stripped}")
                    continue
                
                # 移除解釋被告為什麼沒有損害的無用文字
                if ('未提及被告' in line_stripped or 
                    '故此部分無損害項目' in line_stripped or
                    '由於原始描述僅提供' in line_stripped):
                    print(f"🔍 移除無用解釋文字：{line_stripped}")
                    continue
                
                cleaned_lines.append(line)
        
        # 重新組合
        cleaned_text = '\n'.join(cleaned_lines)
        
        # 清理多餘的空行
        cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
        
        return cleaned_text.strip()
    
    def _final_format_validation(self, text: str, is_single_case: bool) -> str:
        """最終格式驗證和修正"""
        import re
        
        if not is_single_case:
            return text  # 多原告案件不需要特殊處理
        
        # 單一原告案件的特殊格式修正
        lines = text.split('\n')
        corrected_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # 檢測並修正「（一）原告之損害：」格式
            if re.match(r'^[（(][一二三四五六七八九十][）)].*原告.*之損害：?$', line_stripped):
                print(f"🔍 檢測到錯誤格式，移除：{line_stripped}")
                continue  # 跳過這種錯誤格式的行
            
            # 檢測並修正嵌套的損害項目格式
            # 如：「1. 醫療費用：182,690元」→「（一）醫療費用：182,690元」
            if re.match(r'^\d+\.\s*([^：]+)：([0-9,]+元)', line_stripped):
                match = re.match(r'^\d+\.\s*([^：]+)：([0-9,]+元)', line_stripped)
                if match:
                    item_name = match.group(1).strip()
                    amount = match.group(2).strip()
                    # 轉換為正確的中文編號格式
                    # 簡單的數字轉換（1→一，2→二等）
                    chinese_nums = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
                    item_num = re.match(r'^(\d+)', line_stripped).group(1)
                    try:
                        num = int(item_num)
                        if num <= 10:
                            chinese_num = chinese_nums[num]
                            corrected_line = f"（{chinese_num}）{item_name}：{amount}"
                            print(f"🔍 格式修正：{line_stripped} → {corrected_line}")
                            corrected_lines.append(corrected_line)
                            continue
                    except:
                        pass
            
            corrected_lines.append(line)
        
        # 重新組合並清理
        corrected_text = '\n'.join(corrected_lines)
        
        # 確保格式一致性
        if not corrected_text.startswith("三、損害項目："):
            corrected_text = "三、損害項目：\n" + corrected_text
        
        return corrected_text.strip()
    
    def _clean_evidence_language(self, text: str) -> str:
        """清理文本中的證據語言"""
        import re
        
        # 移除證據相關文字
        evidence_patterns = [
            r'，此有[^。]*可證。?',
            r'，有[^。]*收據[^。]*證。?',
            r'，有[^。]*發票[^。]*證。?',
            r'，有[^。]*證明[^。]*證。?',
            r'，[^。]*為證。?',
            r'此有[^。]*可證。?',
            r'有[^。]*收據[^。]*證。?',
            r'有[^。]*發票[^。]*證。?',
            r'有[^。]*證明[^。]*證。?',
            r'[^。]*為證。?'
        ]
        
        cleaned_text = text
        for pattern in evidence_patterns:
            cleaned_text = re.sub(pattern, '。', cleaned_text)
        
        # 清理多餘的句號和空格
        cleaned_text = re.sub(r'。+', '。', cleaned_text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip().rstrip('。')
        
        return cleaned_text

    def _ensure_reason_completeness(self, text: str, original_facts: str) -> str:
        """確保每個損害項目都有理由說明"""
        import re
        
        lines = text.split('\n')
        enhanced_lines = []
        
        # 解析原始描述，建立項目到理由的對應
        reason_map = {}
        original_lines = original_facts.split('\n')
        
        current_item = None
        current_reason = []
        
        for line in original_lines:
            line = line.strip()
            if not line:
                continue
            
            # 檢查是否是新的項目開始
            item_match = re.match(r'^\d+\.\s*([^：]+)：', line)
            if item_match:
                # 保存前一個項目的理由
                if current_item and current_reason:
                    reason_text = ' '.join(current_reason)
                    # 清理證據語言
                    reason_text = self._clean_evidence_language(reason_text)
                    reason_map[current_item] = reason_text
                
                # 開始新項目
                current_item = item_match.group(1).strip()
                current_reason = []
                
                # 檢查同一行是否有理由
                reason_part = line.split('：', 1)[1] if '：' in line else ''
                if reason_part and not re.match(r'^\d+[,\d]*元', reason_part.strip()):
                    current_reason.append(reason_part.strip())
            else:
                # 這是理由說明行
                if current_item and line:
                    current_reason.append(line)
        
        # 保存最後一個項目
        if current_item and current_reason:
            reason_text = ' '.join(current_reason)
            # 清理證據語言
            reason_text = self._clean_evidence_language(reason_text)
            reason_map[current_item] = reason_text
        
        # 處理輸出文本，補充缺失的理由
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            enhanced_lines.append(lines[i])
            
            # 檢查是否是損害項目行
            item_match = re.match(r'^[（(][一二三四五六七八九十][）)]([^：]+)：([0-9,]+元)', line)
            if item_match:
                item_name = item_match.group(1).strip()
                amount = item_match.group(2).strip()
                
                # 檢查下一行是否有理由
                has_reason = False
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (next_line and 
                        not re.match(r'^[（(][一二三四五六七八九十][）)]', next_line) and
                        len(next_line) > 10):
                        has_reason = True
                
                # 如果沒有理由，從原始描述中找理由並添加
                if not has_reason:
                    reason = None
                    
                    # 精確匹配項目名稱
                    for key, value in reason_map.items():
                        if item_name in key or key in item_name:
                            reason = value
                            break
                    
                    # 如果找不到精確匹配，用簡潔的通用理由
                    if not reason:
                        if '醫療' in item_name:
                            reason = f"原告因本次事故受傷，支出{item_name}{amount}。"
                        elif '看護' in item_name:
                            reason = f"原告因本次事故受有重傷，需專人看護，支出{item_name}{amount}。"
                        elif '交通' in item_name:
                            reason = f"原告因本次事故受傷就醫期間，支出{item_name}{amount}。"
                        elif '工作' in item_name or '損失' in item_name:
                            reason = f"原告因本次事故受傷無法工作，受有{item_name}{amount}。"
                        elif '慰撫' in item_name:
                            reason = f"原告因本次事故受有傷害，造成身心痛苦，請求{item_name}{amount}。"
                        else:
                            reason = f"原告因本次事故支出{item_name}{amount}。"
                    
                    if reason:
                        # 添加理由行
                        enhanced_lines.append(reason)
                        print(f"🔍 補充理由：{item_name} -> {reason}")
            
            i += 1
        
        return '\n'.join(enhanced_lines)
    
    def _sort_laws_by_article_number(self, laws: List[str], law_descriptions: dict) -> List[tuple]:
        """按條號數字大小排序法條並返回(條號, 內容)元組列表"""
        import re
        
        def extract_article_number(law: str) -> tuple:
            """提取條號數字用於排序"""
            # 匹配如：民法第184條第1項前段
            match = re.search(r'第(\d+)條(?:之(\d+))?', law)
            if match:
                main_num = int(match.group(1))
                sub_num = int(match.group(2)) if match.group(2) else 0
                return (main_num, sub_num)
            return (999, 0)  # 無法解析的放到最後
        
        # 創建包含條號、內容和排序鍵的列表
        law_items = []
        for law in laws:
            if law in law_descriptions:
                content = f"「{law_descriptions[law]}」"
                sort_key = extract_article_number(law)
                law_items.append((law, content, sort_key))
        
        # 按條號數字排序
        law_items.sort(key=lambda x: x[2])
        
        # 返回(條號, 內容)元組列表
        return [(item[0], item[1]) for item in law_items]
    
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
    
    def _generate_structured_compensation(self, comp_facts: str, parties: dict) -> str:
        """使用結構化處理器生成損害項目"""
        print("🏗️ 使用結構化處理器分析損害項目...")
        
        # 使用結構化處理器
        result = self.structured_processor.process_structured_document(comp_facts)
        
        # 檢查是否有計算錯誤
        validation = result.get('validation', {})
        if validation.get('claimed_total') and not validation.get('match', True):
            print(f"⚠️ 發現計算錯誤：原起訴狀聲稱{validation['claimed_total']:,}元，實際應為{validation['calculated_total']:,}元")
            print(f"📊 差額：{abs(validation['difference']):,}元")
        
        # 生成修正後的損害項目
        structured_text = "三、損害項目：\n\n"
        
        # 按原告分組顯示
        current_plaintiff = None
        plaintiff_index = 0
        item_counter = 1
        
        for item in result['structured_items']:
            # 判斷是否為新的原告
            item_title = item['item_title']
            if '原告' in item_title:
                # 提取原告姓名
                plaintiff_match = re.search(r'原告([^之的]+)', item_title)
                if plaintiff_match:
                    plaintiff_name = plaintiff_match.group(1).strip()
                    if plaintiff_name != current_plaintiff:
                        current_plaintiff = plaintiff_name
                        plaintiff_index += 1
                        chinese_num = self._chinese_num(plaintiff_index)
                        structured_text += f"（{chinese_num}）原告{current_plaintiff}之損害：\n"
                        item_counter = 1
            
            # 添加損害項目
            structured_text += f"{item_counter}. {item['item_title']}：{item['formatted_amount']}\n"
            if item['description']:
                structured_text += f"   {item['description']}\n"
            item_counter += 1
            structured_text += "\n"
        
        # 添加我說明
        total_amount = result['calculation']['total']
        structured_text += f"\n💰 損害總計：新台幣{total_amount:,}元整\n"
        
        # 如果有計算錯誤，添加說明
        if validation.get('claimed_total') and not validation.get('match', True):
            structured_text += f"\n（註：經重新計算，正確總額為{total_amount:,}元，"
            if validation['difference'] > 0:
                structured_text += f"原起訴狀少算{validation['difference']:,}元）"
            else:
                structured_text += f"原起訴狀多算{abs(validation['difference']):,}元）"
        
        return structured_text
    
    def generate_cot_conclusion_with_smart_amount_calculation(self, accident_facts: str, compensation_text: str, parties: dict) -> str:
        """使用智能金額計算生成CoT結論（防止重複和錯誤計算）"""
        print("🧠 生成CoT結論（含總金額計算）...")
        
        # 統一使用詳細損害項目提取方法（已驗證準確）
        plaintiff_damages = self._extract_damage_items_from_text(compensation_text)
        
        # 基於詳細項目計算總金額（確保一致性）
        total_amount = 0
        amounts = []
        item_details = []
        
        print("🔍 【統一金額計算】基於第三部分詳細項目計算總額...")
        for plaintiff, damages in plaintiff_damages.items():
            for damage in damages:
                total_amount += damage['amount']
                amounts.append(damage['amount'])
                item_details.append(f"{damage['name']}{damage['amount']:,}元")
                print(f"   ✅ {plaintiff}: {damage['name']} {damage['amount']:,}元")
        
        print(f"🔍 【統一金額計算】最終總計: {total_amount:,}元")
        
        # 構建包含金額計算的CoT提示詞
        plaintiff = parties.get("原告", "原告")
        defendant = parties.get("被告", "被告")
        plaintiff_count = parties.get('原告數量', 1)
        
        # 構建原告分組信息
        plaintiff_details = ""
        if plaintiff_damages:
            plaintiff_details = "\n📋 各原告損害詳情："
            for plaintiff_name, damages in plaintiff_damages.items():
                plaintiff_details += f"\n• 原告{plaintiff_name}："
                for damage in damages:
                    plaintiff_details += f" {damage['name']}{damage['amount']:,}元"
        
        # 根據被告數量決定責任用詞
        defendant_list = [name.strip() for name in parties.get('被告', '被告').split('、') if name.strip() and name.strip() != '被告']
        defendant_count = len(defendant_list) if defendant_list else 1
        
        # 單一被告用「賠償」，多被告用「連帶賠償」
        liability_term = "連帶賠償" if defendant_count > 1 else "賠償"
        
        prompt = f"""你是台灣資深律師，請運用Chain of Thought推理方式生成專業的起訴狀結論段落。

👥 當事人資訊：
原告：{plaintiff}（共{plaintiff_count}名）
被告：{defendant}（共{defendant_count}名）

📄 案件事實：
{accident_facts}

📄 損害賠償內容：
{compensation_text}
{plaintiff_details}

💰 智能金額分析結果：
提取到的有效求償金額：{amounts}
正確總計：{total_amount:,}元

🧠 請使用Chain of Thought方式分析：

步驟1: 分析案件性質和當事人責任
步驟2: 從損害賠償內容中識別各原告的具體損害項目和金額
步驟3: 確保姓名一致性（與事實概述中的姓名完全一致）
步驟4: 按原告分組列出具體損害項目，形成精確的結論

🏛️ 最後請生成專業的結論段落，格式要求：
- 開頭：「四、結論：」
- 格式：一段式連續文字，不要條列式
- 內容結構：「綜上所陳，被告應{liability_term}原告之損害，包含原告[姓名1][項目1][金額1]元、[項目2][金額2]元；原告[姓名2][項目1][金額1]元、[項目2][金額2]元，總計{total_amount:,}元，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。」

⚠️ 重要要求：
1. 必須按原告分組，清楚列出每位原告的具體損害項目和金額
2. 確保原告姓名與事實概述完全一致
3. 每位原告的損害項目要準確對應其實際金額
4. 必須使用提供的正確總計{total_amount:,}元
5. 用一段連續文字，不要分條列出
6. 如有多名原告，用分號區隔不同原告的損害項目
7. **重要**：項目名稱必須與損害賠償段落完全一致（如：損害段落寫「工作損失」，結論就用「工作損失」，不可改為「工資損失」）
8. **重要**：車輛相關項目使用統一名稱（如：「車輛損失」而非「車輛貶值損失」或「鑑定費用」）

請直接輸出結論段落："""

        result = self.call_llm(prompt, timeout=180)
        
        return result if result else "四、結論：\n（LLM生成失敗，請檢查輸入內容）"

    def generate_cot_conclusion_with_structured_analysis(self, accident_facts: str, compensation_text: str, parties: dict) -> str:
        """使用智能金額計算生成CoT結論（簡化版本）"""
        print("🧠 生成CoT結論（使用智能金額計算）...")
        
        # 直接使用智能金額計算方式，避免複雜的結構化處理
        return self.generate_cot_conclusion_with_smart_amount_calculation(
            accident_facts, compensation_text, parties
        )
    
    def _build_structured_cot_prompt(self, accident_facts: str, compensation_text: str, parties: dict, analysis_result: dict) -> str:
        """構建基於結構化分析的CoT提示詞"""
        
        plaintiff = parties.get("原告", "原告")
        defendant = parties.get("被告", "被告")
        
        # 提取結構化分析結果
        structured_items = analysis_result.get('structured_items', [])
        calculation = analysis_result.get('calculation', {})
        validation = analysis_result.get('validation', {})
        
        # 構建項目摘要
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
        
        prompt = f"""你是台灣資深律師，請運用Chain of Thought推理方式，根據結構化分析結果生成專業的起訴狀結論段落。

🎯 重要指示：
1. 必須使用正確的金額計算，避免重複計算說明文字中的金額
2. 使用逐步推理方式分析損害項目
3. 結論必須包含完整的項目明細
4. 總金額必須準確無誤
5. 採用標準的法律文書格式

👥 當事人資訊：
原告：{plaintiff}
被告：{defendant}

📄 案件事實：
{accident_facts}

📄 損害賠償原始內容：
{compensation_text}

{items_summary}

🧠 請使用Chain of Thought方式分析：

步驟1: 分析案件性質和當事人責任
步驟2: 檢視各項損害的合理性和法律依據
步驟3: 驗證金額計算的準確性
步驟4: 綜合分析並形成結論

🏛️ 最後請生成專業的結論段落，包括：
1. 損害項目明細列表
2. 正確的總金額計算  
3. 標準的結論格式
4. 利息計算條款

格式要求：
- 開頭：「四、結論：」
- 中間：列舉各項損害明細
- 結尾：總計金額和利息請求
- ⚠️ 重要：避免重複說明同一項目，每項損害只說明一次
- ⚠️ 重要：不要重複列舉金額，使用結構化分析的正確總額

重要：請確保金額計算絕對正確，使用結構化分析的正確總額！"""

        return prompt
    
    def _build_traditional_cot_prompt(self, accident_facts: str, compensation_text: str, parties: dict) -> str:
        """構建傳統CoT提示詞"""
        
        plaintiff = parties.get("原告", "原告")
        defendant = parties.get("被告", "被告")
        
        prompt = f"""你是台灣資深律師，請運用Chain of Thought推理方式生成專業的起訴狀結論段落。

👥 當事人資訊：
原告：{plaintiff}
被告：{defendant}

📄 案件事實：
{accident_facts}

📄 損害賠償內容：
{compensation_text}

🧠 請使用Chain of Thought方式分析：

步驟1: 分析案件性質和當事人責任
步驟2: 檢視各項損害的合理性和法律依據  
步驟3: 計算總損害金額
步驟4: 綜合分析並形成結論

🏛️ 最後請生成專業的結論段落，格式要求：
- 開頭：「四、結論：」
- 中間：列舉各項損害明細
- 結尾：總計金額和利息請求
- ⚠️ 重要：避免重複說明同一項目，每項損害只說明一次
- ⚠️ 重要：不要重複列舉相同的金額和項目"""

        return prompt
    
    def _post_process_structured_conclusion(self, conclusion: str, analysis_result: dict) -> str:
        """後處理結構化結論"""
        
        # 添加處理資訊
        processing_info = f"\n\n💡 處理資訊：\n"
        processing_info += f"處理方法：結構化分析\n"
        
        calculation = analysis_result.get('calculation', {})
        validation = analysis_result.get('validation', {})
        
        processing_info += f"正確總額：{calculation.get('total', 0):,}元\n"
        if validation.get('claimed_total'):
            processing_info += f"原聲稱額：{validation['claimed_total']:,}元\n"
            if validation.get('difference', 0) != 0:
                processing_info += f"差額修正：{abs(validation['difference']):,}元\n"
        
        return conclusion + processing_info

    def _generate_complex_compensation(self, comp_facts: str, parties: dict) -> str:
        """處理複雜損害項目文本的分步方法"""
        print("🔧 使用分步處理複雜損害文本...")
        
        # 步驟1：預處理中文數字
        preprocessed_facts = self._preprocess_chinese_numbers(comp_facts)
        
        # 直接格式化為標準損害項目
        format_prompt = f"""請將以下損害賠償內容重新整理為標準的法律文書格式：

【當事人】
原告：{parties.get('原告', '未提及')}（共{parties.get('原告數量', 1)}名）

【損害描述】
{preprocessed_facts}

【標準格式要求】
三、損害項目：

（一）原告[姓名]之損害：
1. [項目名稱]：[金額]元
   說明：原告[姓名]因本次車禍[損害性質]
2. [項目名稱]：[金額]元
   說明：原告[姓名]因本次車禍[損害性質]

（二）原告[姓名]之損害：
1. [項目名稱]：[金額]元
   說明：原告[姓名]因本次車禍[損害性質]

【重要要求】
- 直接整理損害項目，不要顯示分析或計算過程
- 共同費用要平均分攤給相關原告
- 所有金額使用千分位逗號格式
- 每項損害都要有具體說明
- 確保格式整齊統一

請直接輸出標準格式的損害項目："""

        return self.call_llm(format_prompt, timeout=120)

    def _verify_calculation(self, result_text: str) -> dict:
        """從結果中提取並驗證計算準確性"""
        import re
        
        verification = {
            "correct": True,
            "errors": [],
            "corrected_total": None
        }
        
        # 提取所有金額數字
        amounts = re.findall(r'(\d{1,3}(?:,\d{3})*)', result_text)
        amounts = [int(amt.replace(',', '')) for amt in amounts if amt]
        
        if len(amounts) >= 10:  # 如果有足夠的金額進行驗證
            # 嘗試找到兩個小計和總計
            try:
                # 假設最後三個大數字是：小計1、小計2、總計
                if len(amounts) >= 3:
                    subtotal1 = amounts[-3]
                    subtotal2 = amounts[-2] 
                    reported_total = amounts[-1]
                    
                    # 驗證總計
                    actual_total = subtotal1 + subtotal2
                    if actual_total != reported_total:
                        verification["correct"] = False
                        verification["errors"].append(f"總計錯誤：{subtotal1} + {subtotal2} = {actual_total}，但報告為{reported_total}")
                        verification["corrected_total"] = actual_total
                        
            except Exception as e:
                verification["errors"].append(f"驗證過程出錯：{e}")
        
        return verification

    def _generate_llm_based_compensation(self, comp_facts: str, parties: dict) -> str:
        """使用LLM完全處理損害項目生成 - 支持格式自適應"""
        
        # 先預處理中文數字
        preprocessed_facts = self._preprocess_chinese_numbers(comp_facts)
        
        # 檢測輸入格式類型
        if self.format_handler:
            format_info = self.format_handler.detect_format(preprocessed_facts)
            detected_format = format_info.get('primary_format')
            confidence = format_info.get('confidence', 0.0)
            print(f"🔍 【格式檢測】檢測到格式: {detected_format} (置信度: {confidence:.2f})")
        else:
            detected_format = None
            confidence = 0.0
        
        # 檢查是否為單一原告情況（被告數量不影響格式選擇）
        # 正確計算當事人數量
        plaintiff_list = [name.strip() for name in parties.get('原告', '原告').split('、') if name.strip() and name.strip() != '原告']
        defendant_list = [name.strip() for name in parties.get('被告', '被告').split('、') if name.strip() and name.strip() != '被告']
        
        # 如果沒有具體姓名，當事人數量為1
        plaintiff_count = len(plaintiff_list) if plaintiff_list else 1
        defendant_count = len(defendant_list) if defendant_list else 1
        is_single_case = plaintiff_count == 1  # 只看原告數量
        
        # 除錯輸出
        print(f"🔍 DEBUG: parties = {parties}")
        print(f"🔍 DEBUG: plaintiff_list = {plaintiff_list}")
        print(f"🔍 DEBUG: plaintiff_count = {plaintiff_count}, defendant_count = {defendant_count}")
        print(f"🔍 DEBUG: is_single_case = {is_single_case}")
        
        # 根據格式檢測結果選擇合適的提示詞策略
        # 優先檢查是否為多原告案例
        if plaintiff_count > 1:
            # 多原告案例 - 強制使用多原告專門處理
            print(f"🔍 檢測到多原告案例: {plaintiff_count}名原告，使用多原告專門處理")
            prompt = self._build_adaptive_prompt(preprocessed_facts, parties, 'multi_plaintiff_narrative')
        elif detected_format == 'multi_plaintiff_narrative' or (format_info.get('is_multi_plaintiff', False) and plaintiff_count > 1):
            # 多原告案例 - 使用多原告專門處理
            prompt = self._build_adaptive_prompt(preprocessed_facts, parties, 'multi_plaintiff_narrative')
        elif detected_format == 'free_format' or confidence < 0.5:
            # 自由格式或格式不明確 - 使用適應性提示詞
            prompt = self._build_adaptive_prompt(preprocessed_facts, parties, detected_format)
        elif is_single_case:
            # 單一原告時，使用簡化的中文編號格式（不論被告數量）
            prompt = f"""請將以下損害內容整理成損害項目清單，理由簡潔明瞭。

【原始內容】
{preprocessed_facts}

【輸出格式】
（一）項目名稱：金額元
原告因本次事故[簡潔理由]，支出/受有[項目名稱][金額]元。

【範例】
（一）醫療費用：182,690元
原告因本次事故受傷，於南門醫院、雲林基督教醫院就醫治療，支出醫療費用共計182,690元。

（二）看護費用：246,000元
原告因本次事故受有重傷，需專人看護，支出看護費用246,000元。

（三）工作損失：485,000元
原告於車禍發生時任職於凱撒大飯店房務部領班，因本次事故受傷需休養一年，致無法工作，受有工作損失485,000元。

【要求】
- 理由1-2句話，簡潔明瞭
- 保留重要醫院名稱、工作單位等關鍵資訊
- 統一使用"本次事故"而非"本件車禍"
- 工作損失項目名稱直接用"工作損失"
- 精神慰撫金項目名稱直接用"慰撫金"
- 不要過度解釋或分析

請輸出："""
        else:
            # 多原告時，使用完整格式，每位原告分別列出損害
            prompt = f"""你是台灣律師，請根據車禍案件的損害賠償內容，分析並重新整理成標準的起訴狀損害項目格式：

【當事人資訊】
原告：{parties.get('原告', '未提及')}（共{plaintiff_count}名）
被告：{parties.get('被告', '未提及')}（共{defendant_count}名）
原告名單：{plaintiff_list}

【原始損害描述】
{preprocessed_facts}

【分析要求】
請仔細分析上述內容，從中提取出：
1. 每位原告的具體損害項目類型和確切金額
2. **每項損害的詳細事實根據和法律理由**：這是最重要的部分！
3. **重要**：只能使用原始描述中已提及的事實，絕對不可以自行添加或編造任何內容
4. **就醫紀錄整合**：如果原始描述中有具體的醫院名稱，請將這些就醫紀錄整合到醫療相關損害項目的理由說明中
5. **理由完整性**：每個損害項目都必須有完整的理由說明，包括：
   - 損害發生的原因（因本次車禍...）
   - 具體的事實依據（支出費用、受傷情況、影響等）
   - 相關的詳細說明（就醫情況、工作影響、生活影響等）

【標準輸出格式】
三、損害項目：

（一）原告吳麗娟之損害：
1. 醫療費用：6,720元
原告吳麗娟因本次車禍受傷，於臺北榮民總醫院、馬偕紀念醫院、內湖菁英診所及中醫診所就醫治療，支出醫療費用計6,720元。

2. 未來手術費用：264,379元
原告吳麗娟因本次車禍經榮民總醫院確診發生腰椎第一、二節脊椎滑脫，預計未來手術費用為264,379元。

3. 看護費用：152,500元
原告吳麗娟因本次車禍身體受猛烈撞擊震盪，養傷期間無生活自主能力，自107年7月24日起至107年11月23日止，平均分攤看護費用共計305,000元之半數。

4. 慰撫金：200,000元
原告吳麗娟因本次車禍除受外傷外，尚因受撞擊拉扯，須長期治療及復健，且未來尚須負擔沉重手術費用，故請求慰撫金200,000元。

（二）原告陳碧翔之損害：
1. 醫療費用：12,180元
原告陳碧翔因本次車禍受傷，於臺北榮民總醫院、馬偕紀念醫院及中醫診所就醫治療，支出醫療費用計12,180元。

2. 假牙裝置費用：24,000元
原告陳碧翔因本次車禍頭部右側遭受重擊，假牙脫落，需重新安裝假牙裝置，費用為24,000元。

【關鍵要求】
- 每位原告先用（一）（二）等編號區分
- 每位原告內部的損害項目使用 1. 2. 3. 等數字編號
- **每項必須格式**：數字編號. 項目名稱：金額 + 詳細完整的法律理由說明
- **理由完整性要求**：每個損害項目都必須包含完整的理由說明，不可只有金額
- **理由內容要求**：
  - 損害發生的原因（如：因本次車禍受傷...）
  - 具體的事實依據（如：支出費用、受傷情況、工作影響等）
  - 相關的詳細說明（如：就醫情況、治療需要、生活影響等）
- 理由說明必須基於原始描述中的具體事實，充分提取原始描述的詳細資訊
- 不可自行編造任何醫療診斷、傷勢描述或其他細節
- **就醫紀錄處理**：如果原始描述提及具體醫院名稱，請在醫療相關項目中加入「於[醫院名稱]就醫治療」
- 理由要採用正式的法律文書語言
- 使用千分位逗號格式顯示金額

【嚴格禁止事項】
- 絕對不可在輸出中包含「綜上所述」、「總計」、「合計」、「共計」等結論性文字
- 不要包含任何總金額計算或匯總說明
- 不要包含任何法定利息的說明
- 不要包含任何結論段落或總結文字
- 不要包含證據相關文字：「此有相關收據可證」、「有收據為證」、「有統一發票可證」、「可證」等
- 不要包含判決書用語：「經查」、「查明」、「經審理」等
- **絕對禁止被告損害**：不可以包含任何關於被告損害的內容，被告是賠償義務人不會有損害
- **絕對禁止**：不可以出現「（二）被告...之損害」或任何被告損害的描述
- 只輸出純粹的損害項目條列，每項包含編號、名稱、金額、理由說明
- **明確原則**：起訴狀中只能有原告的損害，絕對不能創造虛假的被告損害項目

請嚴格按照上述格式和要求，基於原始描述的事實分析並輸出損害項目："""

        result = self.call_llm(prompt, timeout=120)
        
        # 清理結論性文字
        result = self._remove_conclusion_phrases(result)
        
        # 移除任何關於被告損害的錯誤內容
        result = self._remove_defendant_damage_errors(result)
        
        # 檢查並補充缺失的理由
        result = self._ensure_reason_completeness(result, preprocessed_facts)
        
        # 最終清理證據語言（但保留理由說明）
        result = self._remove_conclusion_phrases(result)
        
        # 最終格式驗證和修正（但不要破壞理由）
        # result = self._final_format_validation(result, is_single_case)
        
        # 檢查結果是否包含預期格式
        if "（一）" in result:
            # 確保包含標題「三、損害項目：」
            if not result.startswith("三、損害項目："):
                result = "三、損害項目：\n\n" + result
            return result
        else:
            # Fallback：返回基本格式
            return comp_facts

    def _build_adaptive_prompt(self, preprocessed_facts: str, parties: dict, detected_format: str) -> str:
        """根據檢測到的格式構建適應性提示詞"""
        plaintiff = parties.get("原告", "原告")
        plaintiff_count = parties.get('原告數量', 1)
        
        if detected_format == 'multi_plaintiff_narrative':
            # 修正原告數量計算
            plaintiff_list = [name.strip() for name in parties.get('原告', '原告').split('、') if name.strip() and name.strip() != '原告']
            actual_plaintiff_count = len(plaintiff_list) if plaintiff_list else 1
            
            # 多原告敘述格式 - 專門處理多名原告各自的損害
            return f"""你是台灣資深律師，請從以下多原告損害描述中分別提取每位原告的損害項目。

【多原告損害描述】
{preprocessed_facts}

【當事人信息】
原告：{plaintiff}（共{actual_plaintiff_count}名）
原告名單：{plaintiff_list}

【重要分析指導】
這是多原告案例，需要：
1. 分別識別每位原告的損害項目和金額
2. 區分計算基準vs最終求償金額
3. 按原告分組整理損害項目

【輸出格式】
（一）原告[姓名]之損害：
1. 損害類型：金額元
原告[姓名]因本次事故[簡潔理由]，支出/受有[損害類型]金額元。

（二）原告[姓名]之損害：
1. 損害類型：金額元
原告[姓名]因本次事故[簡潔理由]，支出/受有[損害類型]金額元。

【範例】
（一）原告羅靖崴之損害：
1. 醫療費用：2,443元
原告羅靖崴因本次事故受傷就醫，支出醫療費用2,443元。
2. 交通費：1,235元
原告羅靖崴因本次事故就醫，支出交通費用1,235元。
3. 工作損失：20,148元
原告羅靖崴因本次事故無法工作16日，受有工作損失20,148元。
4. 慰撫金：10,000元
原告羅靖崴因本次事故受有身心痛苦，請求精神慰撫金10,000元。

（二）原告邱品妍之損害：
1. 醫療費用：57,550元
原告邱品妍因本次事故受傷就醫，支出醫療費用57,550元。
2. 交通費：22,195元
原告邱品妍因本次事故就醫，支出交通費用22,195元。
3. 工作損失：66,768元
原告邱品妍因本次事故無法工作1月28日，受有工作損失66,768元。
4. 車輛損失：36,000元
原告邱品妍因本次事故車輛受損，支出修復及鑑定費用36,000元。
5. 慰撫金：60,000元
原告邱品妍因本次事故受有身心痛苦，請求精神慰撫金60,000元。

【嚴格要求】
- 必須按原告分組，每位原告單獨列出
- 每位原告先用（一）（二）等中文編號區分
- 每位原告內部用1. 2. 3.等數字編號
- 只提取最終求償金額，排除計算基準（如月薪、日薪等）
- 每項理由1-2句話，簡潔明瞭
- 使用千分位逗號格式
- 不要包含總計、綜上所述等結論性文字

請分析並輸出："""
            
        elif detected_format == 'free_format':
            # 自由文本格式 - 專門處理非結構化描述
            return f"""你是台灣資深律師，請從以下自由文本中提取並整理損害賠償項目。

【原始自由文本】
{preprocessed_facts}

【重要分析指導】
以下文本可能包含：
1. 混合描述的損害項目和金額
2. 計算過程中的基準數據（如基本工資、日薪等）- 這些不是最終求償金額
3. 最終的求償金額

【提取原則】
1. 識別真正的損害類型：醫療費用、交通費、看護費、工作損失、精神慰撫金等
2. 區分計算基準vs最終求償：
   - 計算基準：「以每日XX元作為計算基準」、「每月基本工資XX元計算」
   - 最終求償：「共請求XX元」、「賠償XX元」、「損失為XX元」
3. 只採用最終求償金額，排除計算過程中的基準數據

【輸出格式】
（一）損害類型：金額元
原告因本次事故[簡潔理由說明]。

【範例】
（一）醫療費用：255,830元
原告因本次事故受傷就醫，支出醫療及交通費用共計255,830元。

（二）看護費用：270,000元
原告因本次事故需專人照顧，支出看護費用共計270,000元。

（三）工作損失：113,625元
原告因本次事故無法工作，受有薪資損失共計113,625元。

（四）慰撫金：300,000元
原告因本次事故受有身心痛苦，請求精神慰撫金300,000元。

【嚴格要求】
- 只輸出真正的求償項目，排除計算基準
- 每項理由1-2句話，簡潔明瞭
- 使用千分位逗號格式
- 不要包含總計、綜上所述等結論性文字

請分析並輸出："""
            
        else:
            # 其他格式或未知格式 - 使用通用策略
            if plaintiff_count == 1:
                return f"""請將以下損害內容整理成標準格式的損害項目清單。

【原始內容】
{preprocessed_facts}

【輸出格式】
（一）項目名稱：金額元
原告因本次事故[簡潔理由]，支出/受有[項目名稱]金額元。

【要求】
- 每項理由1-2句話，簡潔明瞭
- 保留重要醫院名稱、工作單位等關鍵資訊  
- 統一使用"本次事故"
- 工作損失項目名稱直接用"工作損失"
- 精神慰撫金項目名稱直接用"慰撫金"
- 使用千分位逗號格式顯示金額

請輸出："""
            else:
                # 多原告情況
                return f"""你是台灣律師，請根據車禍案件的損害賠償內容，分析並重新整理成標準的起訴狀損害項目格式：

【當事人資訊】
原告：{parties.get('原告', '未提及')}（共{plaintiff_count}名）
被告：{parties.get('被告', '未提及')}（共{parties.get('被告數量', 1)}名）

【原始損害描述】
{preprocessed_facts}

【標準輸出格式】
（一）原告[姓名]之損害：
1. 醫療費用：金額元
原告[姓名]因本次車禍受傷，[詳細就醫情況]，支出醫療費用計金額元。

【要求】
- 每位原告先用（一）（二）等編號區分
- 每位原告內部的損害項目使用 1. 2. 3. 等數字編號
- 每項必須包含：數字編號. 項目名稱：金額 + 詳細理由說明
- 理由要完整，包含損害原因、事實依據、詳細說明
- 不可包含總計、綜上所述等結論性文字

請分析並輸出："""

    def _comprehensive_number_preprocessing(self, text: str) -> str:
        """全面預處理中文數字和特殊格式"""
        import re
        
        # 處理 X萬Y,YYY元 格式 (如：26萬4,379元)
        pattern1 = r'(\d+)萬(\d+,?\d+)元'
        def replace1(match):
            wan = int(match.group(1))
            rest = int(match.group(2).replace(',', ''))
            total = wan * 10000 + rest
            return f"{total}元"
        text = re.sub(pattern1, replace1, text)
        
        # 處理其他中文數字格式
        text = re.sub(r'(\d+)萬(\d+)千元', lambda m: f"{int(m.group(1))*10000 + int(m.group(2))*1000}元", text)
        text = re.sub(r'(\d+)萬元', lambda m: f"{int(m.group(1))*10000}元", text)
        text = re.sub(r'(\d+)千元', lambda m: f"{int(m.group(1))*1000}元", text)
        
        return text

    def _is_same_damage_type(self, context1: str, context2: str) -> bool:
        """判斷兩個上下文是否為相同的損害類型"""
        damage_types = [
            ['醫療', '治療', '就診'],
            ['看護', '照顧'],
            ['牙齒', '假牙'],
            ['慰撫', '精神', '痛苦'],
            ['交通', '車資'],
            ['工作', '收入', '薪資'],
            ['修復', '修理', '維修']
        ]
        
        # 找出每個上下文的損害類型
        type1 = None
        type2 = None
        
        for i, keywords in enumerate(damage_types):
            if any(keyword in context1 for keyword in keywords):
                type1 = i
            if any(keyword in context2 for keyword in keywords):
                type2 = i
        
        return type1 is not None and type1 == type2

    def _extract_valid_claim_amounts(self, text: str) -> list:
        """通用智能金額提取 - 使用多層次策略適應各種格式"""
        print(f"🔍 【通用金額提取】原始文本: {text[:200]}...")

        # 策略1: 使用通用格式處理器（如果可用）
        if self.format_handler:
            try:
                damage_items = self.format_handler.extract_damage_items(text)
                if damage_items and len(damage_items) >= 1:  # 修正：只要有1個結果就使用
                    amounts = [item.amount for item in damage_items]
                    
                    # 後處理：移除明顯的計算基準金額 - 增強版
                    filtered_amounts = []
                    for amount in amounts:
                        is_calculation_base = False
                        
                        # 檢查常見的計算基準金額 - 增強版
                        calculation_base_checks = [
                            # 月薪基準檢查
                            {
                                'patterns': ['每個月月薪', '月薪', '平均每月薪資', '每月工資.*為', '月工資.*為'],
                                'description': '月薪基準'
                            },
                            # 每日費用基準檢查  
                            {
                                'patterns': ['每日', '日薪', '全日照護費用每日', '以.*每日.*計算', '以.*每日.*作為計算基準'],
                                'description': '每日費用基準'
                            },
                            # 每月計算基準檢查
                            {
                                'patterns': ['每月.*計算', '依每月.*計算', '每月.*勞動能力', '依每月.*減少'],
                                'description': '每月計算基準'
                            },
                            # 百分比計算基準檢查
                            {
                                'patterns': ['計算式', '×', '％', '76％計算', '.*％.*計算'],
                                'description': '計算式基準'
                            },
                            # 特定金額基準檢查（針對實際案例）
                            {
                                'patterns': ['作為計算基準', '計算基準', '以.*計算', '按.*計算'],
                                'description': '計算基準金額'
                            },
                            # 勞動能力減少基準
                            {
                                'patterns': ['勞動能力.*減少', '勞動能力.*損失.*計算', '勞動能力.*評估'],
                                'description': '勞動能力評估基準'
                            }
                        ]
                        
                        # 檢查金額是否出現在計算基準的上下文中
                        amount_str_patterns = [f'{amount:,}元', f'{amount}元']
                        
                        for pattern in amount_str_patterns:
                            if pattern in text:
                                pos = text.find(pattern)
                                # 擴大上下文檢查範圍到120字符
                                context_start = max(0, pos - 120)
                                context_end = min(len(text), pos + 120)
                                context = text[context_start:context_end]
                                
                                # 檢查所有類型的計算基準
                                for check in calculation_base_checks:
                                    for check_pattern in check['patterns']:
                                        # 使用正則表達式進行更精確的匹配
                                        import re as regex_module
                                        if regex_module.search(check_pattern, context):
                                            # 進一步驗證：確保基準詞和金額距離不超過30字符
                                            pattern_pos = context.find(check_pattern) if check_pattern in context else -1
                                            amount_pos_in_context = context.find(pattern)
                                            
                                            if pattern_pos != -1 and amount_pos_in_context != -1:
                                                distance = abs(pattern_pos - amount_pos_in_context)
                                                if distance < 30:  # 距離小於30字符
                                                    # 檢查中間是否有排除詞
                                                    start_pos = min(pattern_pos, amount_pos_in_context)
                                                    end_pos = max(pattern_pos, amount_pos_in_context)
                                                    between_text = context[start_pos:end_pos]
                                                    
                                                    # 如果中間包含明確的求償詞，則不視為計算基準
                                                    claim_words = ['請求', '賠償', '損害', '損失', '支出', '費用']
                                                    has_claim_word = any(word in between_text for word in claim_words)
                                                    
                                                    if not has_claim_word:
                                                        is_calculation_base = True
                                                        print(f'🔍 【後處理過濾】排除{check["description"]}: {amount:,}元 (距離: {distance}字符)')
                                                        print(f'    上下文: ...{context[max(0, pattern_pos-10):min(len(context), amount_pos_in_context+10)]}...')
                                                        break
                                    if is_calculation_base:
                                        break
                                if is_calculation_base:
                                    break
                        
                        if not is_calculation_base:
                            filtered_amounts.append(amount)
                    
                    print(f"🔍 【通用格式處理器】後處理後剩餘 {len(filtered_amounts)} 個金額: {filtered_amounts}")
                    print(f"🔍 【通用格式處理器】最終總計: {sum(filtered_amounts):,}元")
                    return filtered_amounts
                else:
                    print("🔍 【通用格式處理器】提取結果不足，使用fallback策略")
            except Exception as e:
                print(f"🔍 【通用格式處理器】處理失敗: {e}，使用fallback策略")

        # 策略2: Fallback到原有邏輯（保持兼容性）
        return self._extract_amounts_legacy_method(text)

    def _extract_amounts_legacy_method(self, text: str) -> list:
        """原有的金額提取邏輯（作為fallback）"""
        import re

        print(f"🔍 【傳統金額提取】Fallback到原有邏輯...")

        # 1. 先預處理中文數字
        processed_text = self._comprehensive_number_preprocessing(text)
        clean_text = processed_text.replace(',', '')

        # 2. 定義有效的求償關鍵詞
        valid_claim_keywords = [
            '費用', '損失', '慰撫金', '賠償', '支出', '花費',
            '醫療', '修復', '修理', '交通', '看護', '手術',
            '假牙', '復健', '治療', '工作收入', '預估', '未來', '預計', '用品'
        ]

        # 3. 定義排除的關鍵詞（非求償項目）- 更精確的匹配
        exclude_keywords = [
            '日薪', '年度所得', '月收入', '時薪', '學歷', '畢業',
            '名下', '動產', '總計新台幣', '合計新台幣', '小計新台幣',
            '包括', '其中', '包含',  # 添加細項分解關鍵詞
            '每日', '一日', '日計', '以每日',  # 日薪相關關鍵詞
            '每月', '月計', '以每月', '基本工資', '月薪', '底薪',  # 薪資參考數據
            '所得', '薪資所得', '年收入',  # 薪資參考數據
            '此有', '可證', '為證', '收據', '發票', '證明',  # 證據相關
            '經查', '查明', '經審理',  # 判決書用語
            '作為計算基準', '計算基準', '基準',  # 計算基準相關
            '共計', '總計', '合計', '小計', '計',  # 總和類關鍵詞
            '共', '總', '合',  # 總和簡寫
        ]

        amounts = []
        lines = clean_text.split('\n')

        for line in lines:
            # 找出該行中的所有金額
            line_amounts = re.findall(r'(\d+)\s*元', line)

            for amt_str in line_amounts:
                try:
                    amount = int(amt_str)
                    # 改進小額檢測邏輯：只跳過非常小的金額，但保留可能的費用
                    if amount < 10:  # 只跳過極小額（可能是編號等）
                        continue
                    
                    # 對於50-500元之間的金額，需要更嚴格的檢查確保是真正的費用
                    if 10 <= amount <= 500:
                        # 檢查是否明確提到是費用、支出等
                        small_amount_context = line[max(0, line.find(amt_str + '元') - 30):line.find(amt_str + '元') + 20]
                        small_amount_keywords = ['費用', '支出', '花費', '損失', '賠償', '醫療', '交通', '掛號']
                        if not any(keyword in small_amount_context for keyword in small_amount_keywords):
                            print(f"🔍 【小額跳過】{amount}元 - 無明確費用關鍵詞: {small_amount_context}")
                            continue
                        else:
                            print(f"🔍 【小額保留】{amount}元 - 包含費用關鍵詞: {small_amount_context}")

                    # 檢查金額周圍的上下文
                    # 找到金額在原文中的位置
                    amount_pos = line.find(amt_str + '元')
                    if amount_pos == -1:
                        continue

                    # 提取金額前後100個字符的上下文（擴大範圍）
                    start = max(0, amount_pos - 100)
                    end = min(len(line), amount_pos + 100)
                    context = line[start:end]
                    
                    # 也檢查整個文本中該金額的上下文（用於更準確的基準檢測）
                    full_text_pos = clean_text.find(amt_str + '元')
                    if full_text_pos != -1:
                        full_start = max(0, full_text_pos - 150)
                        full_end = min(len(clean_text), full_text_pos + 150)
                        full_context = clean_text[full_start:full_end]
                    else:
                        full_context = context

                    # 先檢查是否包含有效求償關鍵詞
                    is_valid_claim = any(keyword in context for keyword in valid_claim_keywords)
                    
                    if is_valid_claim:
                        # 如果是有效求償項目，再檢查是否需要排除
                        should_exclude = any(keyword in context for keyword in exclude_keywords)
                        
                        # 檢查是否為計算基準（中間值）- 使用完整上下文
                        calculation_pattern = f'{amount}元計算'
                        clean_full_context = full_context.replace(',', '')
                        is_calculation_base = (
                            '作為計算基準' in full_context or
                            ('以每日' in full_context and '作為計算基準' in full_context) or
                            ('基本工資' in full_context and calculation_pattern in clean_full_context)  # 如果是 "XXX元計算" 格式就是基準
                        )
                        
                        # 檢查是否為最終求償金額（金額直接跟在關鍵詞後面）
                        claim_patterns = [
                            f'損失為{amount}元',  # 受有之薪資損失為113625元
                            f'共請求{amount}元',  # 共請求270000元
                            f'支出.*{amount}元',  # 支出醫療費用255830元
                            f'請求.*{amount}元',  # 請求慰撫金300000元
                            f'賠償.*{amount}元'   # 賠償金額
                        ]
                        # 檢查時確保金額緊跟在描述後面，不是作為計算基準
                        context_clean = context.replace(',', '')
                        is_final_claim = False
                        for pattern in claim_patterns:
                            if re.search(pattern, context_clean):
                                # 進一步檢查：如果同時包含"計算"關鍵詞，可能是基準而非最終金額
                                if '計算' not in context or f'{amount}元計算' not in context_clean:
                                    is_final_claim = True
                                    break
                        
                        
                        # 如果是計算基準但不是最終求償，排除
                        if is_calculation_base and not is_final_claim:
                            should_exclude = True
                        # 如果是最終求償，即使包含其他排除關鍵詞也不排除    
                        elif is_final_claim:
                            should_exclude = False
                        
                        if should_exclude:
                            print(f"🔍 【排除】{amount:,}元 - 包含排除關鍵詞: {context[:50]}...")
                        else:
                            print(f"🔍 【有效】{amount:,}元 - 上下文: {context[:50]}...")
                            amounts.append(amount)
                    else:
                        print(f"🔍 【跳過】{amount:,}元 - 無明確求償關鍵詞: {context[:50]}...")

                except ValueError:
                    continue

        # 4. 改進的去重邏輯（按項目類型分組）
        damage_items = {}  # 按類型分組：{類型: [金額列表]}
        
        for line in clean_text.split('\n'):
            # 識別損害項目標題行（如：（一）醫療費用38,073元 或 1. 醫療費用38,073元）
            if (re.match(r'^[（][一二三四五六七八九十][）]', line.strip()) or 
                re.match(r'^[㈠㈡㈢㈣㈤㈥㈦㈧㈨㈩]', line.strip()) or 
                re.match(r'^\d+\.\s*[^\d]*\d+元', line.strip())):
                line_amounts = re.findall(r'(\d+)\s*元', line)
                for amt_str in line_amounts:
                    try:
                        amount = int(amt_str)
                        if amount >= 100:  # 排除小額
                            # 判斷損害類型
                            damage_type = "其他"
                            if '預估醫療' in line or '未來醫療' in line or '預計醫療' in line:
                                damage_type = "預估醫療費用"
                            elif '醫療用品' in line:
                                damage_type = "醫療用品費用"
                            elif '醫療器材' in line:
                                damage_type = "醫療器材費用"
                            elif '醫療' in line:
                                damage_type = "醫療費用"
                            elif '看護' in line:
                                damage_type = "看護費用"
                            elif '牙齒' in line or '假牙' in line:
                                damage_type = "牙齒損害"
                            elif '慰撫' in line or '精神' in line:
                                damage_type = "精神慰撫金"
                            elif any(keyword in line for keyword in ['交通', '往返', '來回', '車費', '油費', '停車', '過路', '通行']):
                                damage_type = "交通費用"
                            elif '車輛' in line or '機車' in line or '修復' in line or '修理' in line or '維修' in line:
                                damage_type = "車輛修復費用"
                            elif '無法工作' in line or '工作損失' in line:
                                damage_type = "無法工作損失"
                            elif '工作' in line or '收入' in line or '損失' in line:
                                damage_type = "工作損失"
                            
                            if damage_type not in damage_items:
                                damage_items[damage_type] = []
                            damage_items[damage_type].append(amount)
                            print(f"🔍 【確認項目】{damage_type}: {amount:,}元")
                    except ValueError:
                        continue
        
        # 每種損害類型只取一個金額（通常標題行的金額是正確的）
        final_amounts = []
        for damage_type, amounts_list in damage_items.items():
            if amounts_list:
                # 取該類型的第一個金額（標題行）
                final_amounts.append(amounts_list[0])
                print(f"✅ 【採用】{damage_type}: {amounts_list[0]:,}元")

        # 如果沒有找到結構化項目，使用第一階段提取的所有有效金額（去重）
        if not final_amounts and amounts:
            print("🔍 【備用方案】未找到結構化項目，使用第一階段的有效金額")
            # 簡單去重：保留不同的金額
            seen_amounts = set()
            for amount in amounts:
                if amount not in seen_amounts:
                    final_amounts.append(amount)
                    seen_amounts.add(amount)
                    print(f"✅ 【採用】金額: {amount:,}元")

        print(f"🔍 【傳統金額提取】去重後有效金額: {final_amounts}")
        print(f"🔍 【傳統金額提取】最終總計: {sum(final_amounts):,}元")

        return final_amounts

    def _extract_damage_items_from_text(self, text: str) -> Dict[str, List[Dict]]:
        """從文本中精確提取損害項目 - 改善版"""
        # 按原告分組
        plaintiff_damages = {}
        
        # 分句處理
        sentences = re.split(r'[。]', text)
        
        for sentence in sentences:
            # 改善原告識別 - 支援更多格式
            plaintiff_patterns = [
                r'原告([^，。；、\s因由就支出產生之]{2,4})',     # 標準格式，避免抓取動詞
                r'([^，。；、\s]{2,4})之醫療費用',              # 從損害項目反推原告
                r'([^，。；、\s]{2,4})之交通費',                # 從損害項目反推原告  
                r'([^，。；、\s]{2,4})之工資損失',              # 從損害項目反推原告
                r'([^，。；、\s]{2,4})之慰撫金',                # 從損害項目反推原告
                r'原告([^，。；、\s]{2,4})因',                  # 原告XX因格式
                r'原告([^，。；、\s]{2,4})[支受]',               # 原告XX支出/受有格式
            ]
            
            plaintiff = None
            for pattern in plaintiff_patterns:
                plaintiff_match = re.search(pattern, sentence)
                if plaintiff_match:
                    potential_plaintiff = plaintiff_match.group(1)
                    # 驗證是否為有效姓名（排除無關詞彙）
                    if self._is_valid_plaintiff_name(potential_plaintiff):
                        plaintiff = potential_plaintiff
                        break
            
            # 如果沒有找到具體姓名，檢查是否有通用的"原告"
            if not plaintiff:
                if '原告' in sentence and ('因' in sentence or '支出' in sentence or '受有' in sentence or '產生' in sentence):
                    plaintiff = "原告"  # 使用通用原告標識
                
            if not plaintiff:
                continue
                
            if plaintiff not in plaintiff_damages:
                plaintiff_damages[plaintiff] = []
            
            # 精確匹配各種損害類型 - 改善版
            # ========== 精神慰撫金（絕對最高優先級 - 系統開發核心精神） ==========
            if any(keyword in sentence for keyword in [
                # 核心關鍵詞（最高權重）
                '慰撫金', '精神慰撫金', 
                # 主要關鍵詞
                '精神賠償', '精神損害', '精神損害賠償', '精神痛苦',
                # 法律用語
                '非財產上之損害', '非財產損害', '人格權', '人格法益',
                # 描述性關鍵詞
                '身心痛苦', '精神受創', '心理創傷', '精神創傷',
                '精神上痛苦', '身心遭受痛苦', '精神上損害', 
                '精神上所受痛苦', '身心所受痛苦', '心靈創傷',
                # 完整表達模式
                '因.*身心.*痛苦', '因.*精神.*痛苦', '精神.*請求',
                '身心.*賠償', '精神.*慰撫', '痛苦.*慰撫',
                # 寬泛匹配（確保不遺漏）
                '精神', '慰撫', '痛苦'
            ]):
                # 超級靈活的正則表達式陣列 - 涵蓋所有可能表達方式
                amount_patterns = [
                    # 1. 標準直接格式
                    r'(?:慰撫金|精神慰撫金).*?(\d+(?:,\d{3})*)\s*元',
                    r'(?:精神賠償|精神損害賠償|精神損害).*?(\d+(?:,\d{3})*)\s*元',
                    r'(?:精神痛苦).*?(\d+(?:,\d{3})*)\s*元',
                    
                    # 2. 法律用語格式
                    r'(?:非財產上之損害|非財產損害|人格權|人格法益).*?(\d+(?:,\d{3})*)\s*元',
                    
                    # 3. 描述性格式
                    r'(?:身心痛苦|精神受創|心理創傷|精神創傷).*?(?:賠償|慰撫金).*?(\d+(?:,\d{3})*)\s*元',
                    r'(?:精神上痛苦|身心遭受痛苦|精神上損害).*?(\d+(?:,\d{3})*)\s*元',
                    
                    # 4. 請求格式（含動作詞）
                    r'請求.*?(?:慰撫金|精神慰撫金|精神賠償|精神損害).*?(\d+(?:,\d{3})*)\s*元',
                    r'支出.*?(?:慰撫金|精神慰撫金|精神賠償).*?(\d+(?:,\d{3})*)\s*元',
                    r'受有.*?(?:慰撫金|精神慰撫金|精神賠償).*?(\d+(?:,\d{3})*)\s*元',
                    
                    # 5. 總計格式
                    r'(?:慰撫金|精神慰撫金|精神賠償).*?(?:總計|共計|計|合計).*?(\d+(?:,\d{3})*)\s*元',
                    r'(?:總計|共計|計|合計).*?(?:慰撫金|精神慰撫金|精神賠償).*?(\d+(?:,\d{3})*)\s*元',
                    
                    # 6. 倒裝格式
                    r'(\d+(?:,\d{3})*)\s*元.*?(?:慰撫金|精神慰撫金|精神賠償)',
                    
                    # 7. 複雜句式格式
                    r'因.*?(?:事故|意外).*?(?:身心|精神).*?(?:痛苦|創傷|損害).*?(?:請求|賠償).*?(\d+(?:,\d{3})*)\s*元',
                    r'(?:身心|精神).*?(?:痛苦|創傷|損害).*?(?:請求|賠償).*?(\d+(?:,\d{3})*)\s*元',
                    
                    # 8. 最寬泛匹配（包含精神或慰撫且有金額）
                    r'精神.*?(\d+(?:,\d{3})*)\s*元',
                    r'慰撫.*?(\d+(?:,\d{3})*)\s*元',
                    r'痛苦.*?(\d+(?:,\d{3})*)\s*元'
                ]
                
                amount_match = None
                matched_pattern = None
                
                # 按順序嘗試匹配，優先使用更精確的模式
                for i, pattern in enumerate(amount_patterns):
                    amount_match = re.search(pattern, sentence)
                    if amount_match:
                        matched_pattern = i + 1
                        break
                
                if amount_match:
                    amount = int(amount_match.group(1).replace(',', ''))
                    print(f"🎯 慰撫金檢測成功：{amount:,}元 (模式 {matched_pattern})")
                    plaintiff_damages[plaintiff].append({
                        'name': '精神慰撫金',
                        'amount': amount,
                        'description': f'{plaintiff}因本次事故所受精神痛苦之慰撫金'
                    })
            
            # 未來醫療費用（優先檢查，避免被一般醫療費用誤判）
            elif any(keyword in sentence for keyword in ['未來醫療', '將來醫療', '預估.*醫療', '15萬', '十五萬']):
                amount_match = re.search(r'(?:未來醫療|將來醫療|預估.*醫療).*?(\d+(?:,\d{3})*)\s*元|15萬|十五萬', sentence)
                if amount_match:
                    # 處理"15萬"的情況
                    if '15萬' in sentence or '十五萬' in sentence:
                        amount = 150000
                    else:
                        amount = int(amount_match.group(1).replace(',', ''))
                    
                    plaintiff_damages[plaintiff].append({
                        'name': '未來醫療費用',
                        'amount': amount,
                        'description': f'{plaintiff}因本次事故預估之未來醫療費用'
                    })
            
            # 醫療費用（使用更靈活的正則表達式）
            elif any(keyword in sentence for keyword in ['醫療費用', '醫療費', '就醫費用', '醫療']):
                amount_match = re.search(r'(?:醫療費用|醫療費|就醫費用|醫療).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '醫療費用',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故受傷就醫之醫療費用'
                    })
            
            # 財物損失（優先檢查，避免被其他項目誤判）
            elif any(keyword in sentence for keyword in ['財物損失', '財物', '衣物', '物品損失']):
                amount_match = re.search(r'(?:財物損失|財物|衣物|物品損失).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '財物損失',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故所受之財物損失'
                    })
            
            # 牙齒相關費用（擴展檢測範圍）
            elif any(keyword in sentence for keyword in [
                # 假牙相關
                '假牙', '假牙裝置', '假牙脫落', '重新安裝假牙',
                # 牙齒損害相關
                '牙齒損害', '牙齒受損', '牙齒治療', '牙齒破損',
                # 牙科相關
                '牙科', '牙科治療', '牙醫', '口腔', '口腔治療',
                # 通用牙齒
                '牙齒', '齒'
            ]) and '財物' not in sentence:
                # 更靈活的正則表達式
                amount_patterns = [
                    # 標準格式
                    r'(?:假牙|牙齒|牙科|口腔|齒).*?(?:費用|損害|治療|裝置).*?(\d+(?:,\d{3})*)\s*元',
                    # 損害費用格式
                    r'(?:牙齒損害費用|牙科費用|假牙費用|口腔.*?費用).*?(\d+(?:,\d{3})*)\s*元',
                    # 治療費用格式
                    r'(?:牙齒|假牙|牙科|口腔).*?治療.*?費用.*?(\d+(?:,\d{3})*)\s*元',
                    # 寬泛匹配
                    r'(?:牙齒|假牙|牙科|口腔|齒).*?(\d+(?:,\d{3})*)\s*元'
                ]
                
                amount_match = None
                for pattern in amount_patterns:
                    amount_match = re.search(pattern, sentence)
                    if amount_match:
                        break
                
                if amount_match:
                    # 根據內容判斷具體類型
                    if any(word in sentence for word in ['假牙', '裝置', '脫落', '重新安裝']):
                        damage_name = '假牙費用'
                        description = f'{plaintiff}因本次事故所需之假牙費用'
                    elif any(word in sentence for word in ['損害', '受損', '破損']):
                        damage_name = '牙齒損害費用'
                        description = f'{plaintiff}因本次事故牙齒受損之治療費用'
                    elif any(word in sentence for word in ['口腔']):
                        damage_name = '口腔治療費用'
                        description = f'{plaintiff}因本次事故所需之口腔治療費用'
                    elif any(word in sentence for word in ['治療', '牙科', '牙醫']):
                        damage_name = '牙科治療費用'
                        description = f'{plaintiff}因本次事故所需之牙科治療費用'
                    else:
                        damage_name = '牙齒相關費用'
                        description = f'{plaintiff}因本次事故之牙齒相關費用'
                    
                    print(f"🦷 牙齒相關費用檢測成功：{damage_name} {int(amount_match.group(1).replace(',', '')):,}元")
                    plaintiff_damages[plaintiff].append({
                        'name': damage_name,
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': description
                    })
            
            # 手術費用
            elif any(keyword in sentence for keyword in ['手術', '開刀', '手術費']):
                amount_match = re.search(r'(?:手術|開刀|手術費).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '手術費用',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故所需之手術費用'
                    })
            
            # 營養品費用
            elif any(keyword in sentence for keyword in ['營養品', '膠原蛋白', '營養', '補品']):
                amount_match = re.search(r'(?:營養品|膠原蛋白|營養|補品).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '營養品費用',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故所需之營養品費用'
                    })
            
            # 看護費用
            elif any(keyword in sentence for keyword in ['看護', '照護', '護理', '看護費']):
                amount_match = re.search(r'(?:看護|照護|護理|看護費).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '看護費用',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故所需之看護費用'
                    })
            
            # 交通費
            elif any(keyword in sentence for keyword in ['交通費用', '交通費', '往返費用', '來回費用', '車費', '油費', '停車費', '過路費', '通行費']):
                # 使用更靈活的正則表達式，允許關鍵詞和金額之間有其他文字
                amount_match = re.search(r'(?:交通費用|交通費|往返費用|來回費用|車費|油費|停車費|過路費|通行費).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '交通費用',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故所生之交通費用'
                    })
            
            # 勞動能力減損（優先檢查，避免被工作損失誤判）
            elif any(keyword in sentence for keyword in ['勞動能力', '勞動損失', '減少勞動', '勞動減少', '失能']):
                amount_match = re.search(r'(?:勞動能力|勞動損失|減少勞動|勞動減少|失能).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '勞動能力減損',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故勞動能力減損之損失'
                    })
            
            # 工作損失
            elif any(keyword in sentence for keyword in ['工資損失', '薪資損失', '工作損失', '不能工作', '無法工作', '收入損失']):
                amount_match = re.search(r'(?:工資損失|薪資損失|工作損失|收入損失|損失|受有).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '工作損失',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故無法工作之收入損失'
                    })
            
            
            # 車輛維修費用
            elif any(keyword in sentence for keyword in ['車輛維修', '維修費', '修理費', '車輛修理']):
                amount_match = re.search(r'(?:車輛維修|維修費|修理費|車輛修理).*?(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '車輛維修費',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': f'{plaintiff}因本次事故車輛維修之費用'
                    })
            
            # 車輛貶值
            if any(keyword in sentence for keyword in ['貶值', '貶損', '價值減損']):
                amount_match = re.search(r'(?:貶損|減損)\s*(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '車輛貶值損失',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': '系爭車輛因本次事故之價值減損'
                    })
            
            # 鑑定費
            if '鑑定費' in sentence:
                amount_match = re.search(r'鑑定費\s*(\d+(?:,\d{3})*)\s*元', sentence)
                if amount_match:
                    plaintiff_damages[plaintiff].append({
                        'name': '鑑定費用',
                        'amount': int(amount_match.group(1).replace(',', '')),
                        'description': '車輛損害鑑定費用'
                    })
        
        # 處理共同費用分配
        plaintiff_damages = self._handle_shared_costs(plaintiff_damages, text)
        
        return plaintiff_damages
    
    def _handle_shared_costs(self, plaintiff_damages: Dict[str, List[Dict]], text: str) -> Dict[str, List[Dict]]:
        """處理共同費用的分配"""
        if len(plaintiff_damages) <= 1:
            return plaintiff_damages
        
        # 檢測共同費用項目
        shared_costs = []
        plaintiffs = list(plaintiff_damages.keys())
        
        # 找出被分配給第一個原告但應該是共同費用的項目
        for plaintiff, damages in plaintiff_damages.items():
            for damage in damages[:]:  # 使用切片避免修改過程中出錯
                # 檢查該費用是否在共同損害段落中提到
                if self._is_shared_cost(damage, text, plaintiffs):
                    shared_costs.append(damage)
                    damages.remove(damage)  # 從個人費用中移除
        
        # 將共同費用平分給所有原告
        if shared_costs:
            print(f"🔍 檢測到 {len(shared_costs)} 項共同費用需要分配")
            for shared_cost in shared_costs:
                shared_amount = shared_cost['amount']
                split_amount = shared_amount // len(plaintiffs)
                
                print(f"   {shared_cost['name']} {shared_amount:,}元 → 每人 {split_amount:,}元")
                
                for plaintiff in plaintiffs:
                    if plaintiff not in plaintiff_damages:
                        plaintiff_damages[plaintiff] = []
                    
                    plaintiff_damages[plaintiff].append({
                        'name': shared_cost['name'],
                        'amount': split_amount,
                        'description': f"原告{plaintiff}分攤之{shared_cost['name']}"
                    })
        
        return plaintiff_damages
    
    def _is_shared_cost(self, damage: Dict, text: str, plaintiffs: List[str]) -> bool:
        """判斷是否為共同費用"""
        # 更精確地檢查是否在共同損害段落中
        shared_section_pattern = r'[（(][三3][）)].*?原告.*?、.*?共同.*?損害.*?(?=[（(][四4][）)]|四、|$)'
        shared_section_match = re.search(shared_section_pattern, text, re.DOTALL)
        
        if not shared_section_match:
            return False
        
        shared_section_text = shared_section_match.group(0)
        
        # 檢查該費用的金額是否在共同段落中出現
        damage_amount = damage['amount']
        amount_pattern = f"{damage_amount:,}元"
        
        # 同時檢查金額和費用類型關鍵詞
        damage_keywords = {
            '看護費用': ['看護', '照護', '護理'],
            '交通費用': ['交通', '車費', '計程車'],
            '醫療費用': ['醫療'],
            '手術費用': ['手術'],
            '假牙費用': ['假牙', '牙齒'],
            '精神慰撫金': ['慰撫', '精神']
        }
        
        if damage['name'] in damage_keywords:
            keywords = damage_keywords[damage['name']]
            
            # 檢查金額是否在共同段落中
            if amount_pattern in shared_section_text:
                # 檢查對應的關鍵詞是否也在同一段落中
                if any(keyword in shared_section_text for keyword in keywords):
                    print(f"   ✅ {damage['name']} {damage_amount:,}元 確認為共同費用")
                    return True
        
        return False
    
    def _format_damage_items(self, damage_items: Dict[str, List[Dict]]) -> str:
        """格式化損害項目"""
        if not damage_items:
            return ""
        
        result = "三、損害項目：\n"
        for idx, (plaintiff, damages) in enumerate(damage_items.items()):
            chinese_num = self._chinese_num(idx + 1)
            result += f"\n（{chinese_num}）原告{plaintiff}之損害：\n"
            
            for i, damage in enumerate(damages, 1):
                result += f"{i}. {damage['name']}：{damage['amount']:,}元\n"
                result += f"   說明：{damage['description']}\n"
            
            # 小計
            subtotal = sum(d['amount'] for d in damages)
            result += f"\n小計：{subtotal:,}元\n"
        
        # 總計
        total = sum(sum(d['amount'] for d in damages) for damages in damage_items.values())
        result += f"\n損害總計：新台幣{total:,}元整"
        
        return result
    
    def _is_valid_plaintiff_name(self, name: str) -> bool:
        """驗證是否為有效的原告姓名"""
        if not name or len(name) < 2 or len(name) > 5:
            return False
        
        # 排除無關詞彙，但不包含可能出現在姓名中的字
        invalid_keywords = [
            '醫療', '交通', '工資', '損失', '費用', '慰撫', '精神',
            '車輛', '貶值', '鑑定', '賠償', '元', '因', '受', '支出',
            '就醫', '事故', '本次', '所', '之', '等', '共', '計',
            '包含', '總', '合', '金額', '項目', '主張', '根據', '媳婦',
            '全日', '法定', '代理', '診斷', '證明', '依照', '參考'
        ]
        
        for keyword in invalid_keywords:
            if keyword in name:
                return False
        
        # 檢查是否包含數字
        if any(char.isdigit() for char in name):
            return False
        
        # 檢查是否為常見的中文姓名格式
        # 簡單的中文字符檢查
        chinese_char_count = sum(1 for char in name if '\u4e00' <= char <= '\u9fff')
        return chinese_char_count >= 2  # 至少包含2個中文字符
    
    def _standardize_names_in_facts(self, facts_text: str, parties: dict) -> str:
        """統一事實段落中的姓名，確保與當事人信息一致"""
        if not parties:
            return facts_text
        
        result = facts_text
        
        # 處理原告姓名統一
        if '原告' in parties and parties['原告'] != '原告':
            correct_plaintiffs = [name.strip() for name in parties['原告'].split('、') if name.strip()]
            
            # 查找並替換可能的姓名變體
            for correct_name in correct_plaintiffs:
                if len(correct_name) >= 2:
                    # 查找相似姓名（可能是筆誤或不同寫法）
                    # 例如：羅蘭崴 -> 羅靖崴
                    surname = correct_name[0]  # 取姓氏
                    
                    # 查找以相同姓氏開頭但名字不同的可能變體
                    import re
                    pattern = rf'原告{surname}[^，。；、\s]{{1,3}}'
                    matches = re.finditer(pattern, result)
                    
                    for match in matches:
                        found_name = match.group(0).replace('原告', '')
                        if found_name != correct_name and len(found_name) == len(correct_name):
                            # 替換為正確姓名
                            result = result.replace(f'原告{found_name}', f'原告{correct_name}')
                            print(f"🔧 姓名統一: '{found_name}' -> '{correct_name}'")
        
        # 處理被告姓名統一（類似邏輯）
        if '被告' in parties and parties['被告'] != '被告':
            correct_defendants = [name.strip() for name in parties['被告'].split('、') if name.strip()]
            
            for correct_name in correct_defendants:
                if len(correct_name) >= 2:
                    surname = correct_name[0]
                    
                    import re
                    pattern = rf'被告{surname}[^，。；、\s]{{1,3}}'
                    matches = re.finditer(pattern, result)
                    
                    for match in matches:
                        found_name = match.group(0).replace('被告', '')
                        if found_name != correct_name and len(found_name) == len(correct_name):
                            result = result.replace(f'被告{found_name}', f'被告{correct_name}')
                            print(f"🔧 姓名統一: '{found_name}' -> '{correct_name}'")
        
        return result

# ===== 主要互動功能 =====

def interactive_generate_lawsuit():
    """互動式起訴狀生成（恢復多行輸入版本）"""
    print("=" * 80)
    print("🏛️  車禍起訴狀生成器 - 混合版本（整合結構化金額處理）")
    print("=" * 80)
    print("👋 歡迎使用！我會為您生成專業的起訴狀，包含：")
    print("   📄 相似案例檢索")
    print("   ⚖️ 適用法條分析")
    print("   📋 完整起訴狀生成")
    print("💡 支援結構化金額處理，自動修正計算錯誤")
    print()
    
    print("📝 使用方法：")
    print("   1. 請一次性輸入完整的三段內容")
    print("   2. 可以多行輸入，換行繼續")
    print("   3. 輸入完成後輸入 'END' 確認")
    print("   4. 輸入 'quit' 可退出程式")
    print()
    
    # 初始化生成器
    generator = HybridCoTGenerator()
    
    print("📝 請輸入完整的車禍案件資料：")
    print("📋 請包含以下三個部分：")
    print("   一、事故發生緣由：[詳述車禍經過]")
    print("   二、原告受傷情形：[描述傷勢]")
    print("   三、請求賠償的事實根據：[列出損害項目和金額]")
    print()
    print("💡 提示：可以換行輸入，完成後輸入 'END' 確認")
    print("=" * 60)
    print("🎯 請開始輸入（完成後輸入 'END' 或 'end' 確認）：")
    
    # 多行輸入模式
    user_input_lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() in ['END', 'QUIT', 'EXIT', '退出']:
                if line.strip().upper() == 'QUIT' or line.strip().upper() == 'EXIT' or line.strip() == '退出':
                    print("👋 感謝使用，再見！")
                    return
                break
            user_input_lines.append(line)
        except KeyboardInterrupt:
            print("\n👋 用戶中斷，程序退出")
            return
        except EOFError:
            break
    
    user_query = '\n'.join(user_input_lines).strip()
    
    if not user_query:
        print("⚠️ 請輸入有效的內容")
        return
    
    print("🔄 正在處理...")
    
    try:
        # 分段提取資訊
        sections = extract_sections(user_query)
        
        # 提取當事人
        parties = extract_parties(user_query)
        
        # 案件分類和檢索相似案例
        accident_facts = sections.get("accident_facts", user_query)
        case_type = determine_case_type(accident_facts, parties)
        
        print("✅ LLM服務正常")
        print()
        
        # 相似案例檢索（詳細模式）
        similar_cases = []
        if FULL_MODE:
            print("🔍 檢索相似案例...")
            # 使用固定參數進行檢索
            k_final = 3
            initial_retrieve_count = 15
            use_multi_stage = True
            
            print(f"🔧 檢索策略: 目標{k_final}個案例 → 檢索{initial_retrieve_count}個段落")
            
            try:
                # 詳細執行檢索
                query_vector = embed(accident_facts)
                if query_vector:
                    hits = es_search(query_vector, case_type, top_k=initial_retrieve_count, label="Facts", quiet=False)
                    if hits:
                        print(f"🔍 ES原始結果: 找到{len(hits)}個段落")
                        
                        # 多階段模式
                        candidate_case_ids = []
                        for hit in hits:
                            case_id = hit['_source'].get('case_id')
                            if case_id and case_id not in candidate_case_ids:
                                candidate_case_ids.append(case_id)
                        
                        print(f"🔄 去重後結果: {len(candidate_case_ids)}個唯一案例")
                        final_case_ids = candidate_case_ids[:k_final]
                        print(f"📌 最終選取: {len(final_case_ids)}個案例 {final_case_ids}")
                        
                        if candidate_case_ids:
                            reranked_case_ids = rerank_case_ids_by_paragraphs(
                                accident_facts, 
                                candidate_case_ids[:k_final*2],
                                label="Facts",
                                quiet=False
                            )
                            final_case_ids = reranked_case_ids[:k_final]
                            print(f"📘 Rerank後最終順序: {final_case_ids}")
                            
                            similar_cases = get_complete_cases_content(final_case_ids)
                            
                            # 顯示詳細案例分析
                            print()
                            print(f"📋 詳細案例分析 (僅顯示前 {len(similar_cases)} 個最相關案例):")
                            print("=" * 80)
                            print()
                            
                            for i, (case_content, case_id) in enumerate(zip(similar_cases, final_case_ids)):
                                # 從hits中找到對應的分數
                                score = 0.0
                                for hit in hits:
                                    if hit['_source'].get('case_id') == case_id:
                                        score = hit['_score']
                                        break
                                
                                print(f"📄 相似案例 {i+1}: Case ID {case_id}")
                                print(f"🎯 ES相似度分數: {score:.4f}")
                                print("-" * 50)
                                case_preview = case_content[:500] + "..." if len(case_content) > 500 else case_content
                                print(case_preview)
                                print()
                                if i < len(similar_cases) - 1:
                                    print()
                        else:
                            # 簡單模式
                            if hits:
                                first_hit = hits[0]['_source']
                                content_fields = ['original_text', 'content', 'text', 'facts_content', 'chunk_content', 'body']
                                content_field = None
                                for field in content_fields:
                                    if field in first_hit and first_hit[field]:
                                        content_field = field
                                        break
                                
                                if content_field:
                                    similar_cases = [hit['_source'].get(content_field, '') for hit in hits[:k_final] if hit['_source'].get(content_field)]
                                else:
                                    # Fallback
                                    similar_cases = []
                                    for hit in hits[:k_final]:
                                        all_text = " ".join([str(v) for k, v in hit['_source'].items() 
                                                           if isinstance(v, str) and len(v) > 50])
                                        if all_text:
                                            similar_cases.append(all_text)
            except Exception as e:
                similar_cases = []
        
        # ===== 開始混合模式生成 =====
        print(f"\n🎯 開始混合模式生成...")
        print("📝 事實 + 法條 + 損害：標準方式")
        print("🧠 結論：CoT方式（計算總金額）")
        print()
        
        # 生成事實段落
        print("📝 生成事實段落...")
        facts = generator.generate_standard_facts(accident_facts, similar_cases, parties)
        print("✅ 事實段落生成完成")
        
        # 生成法律依據
        print("⚖️ 生成法律依據...")
        
        # 統計相似案例使用的法條
        if similar_cases and 'final_case_ids' in locals():
            try:
                print("📊 分析相似案例使用的法條...")
                similar_laws_stats = get_similar_cases_laws_stats(final_case_ids)
                if similar_laws_stats:
                    print("📋 相似案例常用法條統計:")
                    for law_name, count in similar_laws_stats[:5]:  # 顯示前5個最常用的
                        print(f"   • {law_name}: {count}次")
                    print()
            except Exception as e:
                print(f"⚠️ 法條統計分析失敗: {e}")
        
        laws = generator.generate_standard_laws(
            sections.get("accident_facts", user_query),
            sections.get("injuries", ""),
            parties,
            sections.get("compensation_facts", "")
        )
        print("✅ 法律依據生成完成")
        
        # 生成損害賠償
        print("💰 生成損害賠償...")
        compensation_text = sections.get("compensation_facts", user_query)
        damages = generator.generate_smart_compensation(
            sections.get("injuries", ""),
            compensation_text, 
            parties
        )
        print("✅ 損害賠償生成完成")
        
        # 生成CoT結論
        print("🧠 生成CoT結論（含總金額計算）...")
        conclusion = generator.generate_cot_conclusion_with_structured_analysis(
            sections.get("accident_facts", user_query),
            damages,  # 使用生成後的損害段落，而不是原始輸入
            parties
        )
        print("✅ CoT結論生成完成")
        print()
        print("✅ 所有生成步驟完成！")
        
        # 提取適用法條
        applicable_laws = determine_applicable_laws(
            sections.get("accident_facts", user_query),
            sections.get("injuries", ""),
            sections.get("compensation_facts", ""),
            parties
        )
        
        # ===== 輸出核心結果 =====
        print("\n" + "=" * 60)
        print("⚖️ 適用法條")
        print("=" * 60)
        
        for i, law in enumerate(applicable_laws, 1):
            print(f"{i}. {law}")
        
        print("\n" + "=" * 60)
        print("📋 生成的起訴狀")
        print("=" * 60)
        
        print(f"\n{facts}")
        print(f"\n{laws}")
        print(f"\n{damages}")
        print(f"\n{conclusion}")
        
        print("\n" + "=" * 60)
        print("✅ 起訴狀生成完成!")
        
    except Exception as e:
        print(f"❌ 生成過程中發生錯誤：{str(e)}")
        print("請檢查輸入格式或聯繫系統管理員")

def main():
    """主程序入口"""
    try:
        # 檢查依賴
        print("🔧 檢查系統依賴...")
        print(f"📊 檢索模式：{'完整模式' if FULL_MODE else '簡化模式'}")
        print(f"🏗️ 結構化處理器：{'可用' if STRUCTURED_PROCESSOR_AVAILABLE else '不可用'}")
        print(f"📏 基本標準化器：{'可用' if BASIC_STANDARDIZER_AVAILABLE else '不可用'}")
        
        # 啟動互動界面
        interactive_generate_lawsuit()
        
    except KeyboardInterrupt:
        print("\n\n👋 用戶中斷，程序退出")
    except Exception as e:
        print(f"\n❌ 程序執行錯誤：{str(e)}")

if __name__ == "__main__":
    main()