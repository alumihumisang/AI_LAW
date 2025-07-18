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

# 案件類型對照表
CASE_TYPE_MAP = {
    "數名原告": "單純原被告各一",
    "數名被告": "單純原被告各一", 
    "原被告皆數名": "單純原被告各一",
    "原被告皆數名+§188僱用人案型": "單純原被告各一",
    "數名原告+§188僱用人案型": "單純原被告各一",
    "數名被告+§188僱用人案型": "單純原被告各一",
    "數名被告+§187未成年案型": "單純原被告各一",
    "原被告皆數名+§187未成年案型": "單純原被告各一",
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
    """使用LLM提取當事人（更準確的方法）"""
    print("🤖 使用LLM智能提取當事人...")
    
    # 創建提示模板
    prompt = f"""請你幫我從以下車禍案件的事故詳情中提取並列出所有原告和被告的姓名，並只能用以下格式輸出:
原告:原告1,原告2...
被告:被告1,被告2...

以下是本起車禍的事故詳情：
{text}

重要要求:
1. 請完整提取姓名，不要截斷或省略任何字元（例如：羅靖崴不能寫成羅崴）
2. 如果未提及原告或被告的姓名或代稱需寫為"未提及"
3. 你只需要列出原告和被告的姓名，請不要輸出其他多餘的內容
4. 姓名之間用逗號分隔
5. 如果有甲、乙、丙等代稱也算作姓名
6. 請仔細檢查每個姓名是否完整，特別注意三個字的姓名

範例：
- 正確：羅靖崴,邱品妍
- 錯誤：羅崴,邱品妍"""

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

def parse_llm_parties_result(llm_result: str) -> dict:
    """解析LLM的當事人提取結果"""
    result = {"原告": "未提及", "被告": "未提及", "被告數量": 1, "原告數量": 1}
    
    lines = llm_result.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('原告:') or line.startswith('原告：'):
            plaintiff_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
            if plaintiff_text and plaintiff_text != "未提及":
                # 分割多個原告
                plaintiffs = [p.strip() for p in plaintiff_text.split(',') if p.strip()]
                result["原告"] = "、".join(plaintiffs)
                result["原告數量"] = len(plaintiffs)
        
        elif line.startswith('被告:') or line.startswith('被告：'):
            defendant_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
            if defendant_text and defendant_text != "未提及":
                # 分割多個被告
                defendants = [d.strip() for d in defendant_text.split(',') if d.strip()]
                result["被告"] = "、".join(defendants)
                result["被告數量"] = len(defendants)
    
    return result

def extract_parties_fallback(text: str) -> dict:
    """當LLM提取失敗時的fallback方法（簡化版正則）"""
    print("⚠️ 使用fallback方法提取當事人...")
    result = {"原告": "未提及", "被告": "未提及", "被告數量": 1, "原告數量": 1}
    
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

def es_search(query_vector, case_type: str, top_k: int = 3, label: str = "Facts"):
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
        
        # 調試信息：輸出查詢條件
        print(f"🔍 ES查詢條件: index={CHUNK_INDEX}, label={label_filter}, case_type={case_type_filter}")
        
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
            response = requests.post(url, auth=ES_AUTH, json=body, verify=False)
            if response.status_code == 200:
                result = response.json()
                hits = result["hits"]["hits"]
                total_docs = result["hits"]["total"]["value"] if isinstance(result["hits"]["total"], dict) else result["hits"]["total"]
                print(f"📊 ES查詢結果: 找到 {len(hits)} 個匹配結果，總文檔數: {total_docs}")
                return hits
            else:
                print(f"❌ ES查詢失敗: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"❌ ES查詢失敗: {e}")
            return []

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

def rerank_case_ids_by_paragraphs(query_text: str, case_ids: List[str], label: str = "Facts") -> List[str]:
    """根據段落級資料重新排序案例"""
    if not FULL_MODE or not ES_HOST:
        return case_ids
    
    print("📘 啟動段落級 rerank...")
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
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
                
                # 如果找不到，嘗試使用id屬性
                if not result:
                    result = session.run("""
                        MATCH (c:Case {id: $case_id})-[:包含]->(f:Facts)
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
        print(f"❌ Neo4j查詢失敗: {e}")
        
    return complete_cases

def query_laws(case_ids):
    """查詢相關法條"""
    if not FULL_MODE or not NEO4J_DRIVER:
        return []
    
    try:
        with NEO4J_DRIVER.session() as session:
            # 查詢與案例相關的法條
            result = session.run("""
                MATCH (c:Case)-[:適用]->(l:Laws)
                WHERE c.case_id IN $case_ids OR c.id IN $case_ids
                RETURN DISTINCT l.article AS article, l.description AS description
                ORDER BY l.article
            """, case_ids=case_ids).data()
            
            return result
    except Exception as e:
        print(f"❌ 法條查詢失敗: {e}")
        return []

def normalize_article_number(article: str) -> str:
    """標準化法條編號"""
    return re.sub(r'[^0-9]', '', str(article))

def detect_special_relationships(text: str, parties: dict) -> dict:
    """檢測特殊關係（僱傭、監護等）"""
    relationships = {}
    
    # 僱傭關係檢測
    employment_patterns = [
        r"僱用人.*責任", r"受僱人", r"僱主", r"員工", r"執行職務",
        r"民法.*第.*一百八十八.*條", r"§\s*188", r"第188條"
    ]
    
    for pattern in employment_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            relationships["僱傭關係"] = True
            break
    else:
        relationships["僱傭關係"] = False
    
    # 監護關係檢測（未成年）
    guardianship_patterns = [
        r"未成年", r"監護人", r"法定代理人", r"未滿.*歲",
        r"民法.*第.*一百八十七.*條", r"§\s*187", r"第187條"
    ]
    
    for pattern in guardianship_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            relationships["監護關係"] = True
            break
    else:
        relationships["監護關係"] = False
    
    # 動物管理人責任檢測
    animal_patterns = [
        r"動物.*責任", r"飼主", r"管理人.*動物", r"動物.*管理",
        r"民法.*第.*一百九十.*條", r"§\s*190", r"第190條"
    ]
    
    for pattern in animal_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            relationships["動物管理"] = True
            break
    else:
        relationships["動物管理"] = False
    
    return relationships

def determine_case_type(accident_facts: str, parties: dict) -> str:
    """根據事實和當事人判斷案件類型"""
    # 獲取當事人數量
    plaintiff_count = parties.get("原告數量", 1)
    defendant_count = parties.get("被告數量", 1)
    
    # 檢測特殊關係
    relationships = detect_special_relationships(accident_facts, parties)
    
    # 判斷基本案型
    base_type = ""
    if plaintiff_count == 1 and defendant_count == 1:
        base_type = "單純原被告各一"
    elif plaintiff_count > 1 and defendant_count == 1:
        base_type = "數名原告"
    elif plaintiff_count == 1 and defendant_count > 1:
        base_type = "數名被告"
    elif plaintiff_count > 1 and defendant_count > 1:
        base_type = "原被告皆數名"
    else:
        base_type = "單純原被告各一"  # 預設值
    
    # 檢查特殊法條適用
    if relationships.get("監護關係", False):
        return "§187未成年案型"
    elif relationships.get("僱傭關係", False):
        return "§188僱用人案型"
    elif relationships.get("動物管理", False):
        return "§190動物案型"
    else:
        return base_type

def determine_applicable_laws(accident_facts: str, injuries: str, comp_facts: str, parties: dict) -> List[str]:
    """根據案件事實判斷適用法條"""
    laws = []
    combined_text = f"{accident_facts} {injuries} {comp_facts}"
    
    # 檢測特殊關係
    relationships = detect_special_relationships(combined_text, parties)
    
    # 基本侵權行為 - 第184條
    laws.append("184")
    
    # 特殊責任條款
    if relationships.get("監護關係", False):
        laws.append("187")  # 未成年人責任
    
    if relationships.get("僱傭關係", False):
        laws.append("188")  # 僱用人責任
    
    if relationships.get("動物管理", False):
        laws.append("190")  # 動物管理人責任
    
    # 汽車交通相關
    vehicle_patterns = [
        r"汽車", r"機車", r"摩托車", r"車輛", r"駕駛", r"交通事故", r"車禍"
    ]
    if any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in vehicle_patterns):
        laws.append("191-2")  # 汽車交通事故責任
    
    # 共同侵權
    if parties.get("被告數量", 1) > 1:
        laws.append("185")  # 共同侵權行為
    
    # 損害賠償範圍相關條文
    damage_patterns = [
        r"醫療費", r"看護費", r"精神慰撫金", r"工作能力", r"收入", r"營業損失"
    ]
    if any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in damage_patterns):
        laws.extend(["193", "194", "195", "196"])  # 損害賠償相關條文
    
    return list(set(laws))  # 去重

def call_llm(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """調用LLM生成回應"""
    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            return f"❌ LLM調用失敗: {response.status_code}"
            
    except Exception as e:
        return f"❌ LLM調用異常: {e}"

def generate_lawsuit_content(facts: str, laws: str, compensation: str) -> str:
    """生成完整的起訴狀內容"""
    prompt = f"""你是一位專業的法律文書撰寫助理。請你根據以下提供的資料，撰寫一份完整的民事起訴狀。

## 提供資料：

### 事實部分：
{facts}

### 適用法條：
{laws}

### 損害賠償：
{compensation}

## 撰寫要求：
1. 格式要完整正式，包含標題、當事人、請求事項、事實及理由、證據資料等
2. 事實陳述要清楚有條理，按時間順序組織
3. 法律適用要準確，引用條文要完整
4. 損害賠償計算要詳細列出各項目及金額
5. 用字要正式、專業、符合法律文書規範
6. 請求事項要明確具體

請開始撰寫："""
    
    return call_llm(prompt)

def interactive_generate_lawsuit():
    """互動式生成起訴狀"""
    print("\n" + "="*60)
    print("🏛️  法律文書生成系統 - 混合模式")
    print("="*60)
    
    # 輸入事故描述
    print("\n📝 請輸入車禍事故的詳細描述：")
    print("（包含事故發生緣由、受傷情形、賠償事實根據）")
    user_input = input("> ")
    
    if not user_input.strip():
        print("❌ 請輸入有效的事故描述")
        return
    
    print("\n🔍 開始分析案件...")
    
    # 1. 提取段落
    sections = extract_sections(user_input)
    print(f"✅ 段落提取完成")
    
    # 2. 提取當事人
    parties = extract_parties(user_input)
    print(f"✅ 當事人提取完成: 原告{parties['原告數量']}名, 被告{parties['被告數量']}名")
    
    # 3. 判斷案件類型
    case_type = determine_case_type(sections["accident_facts"], parties)
    print(f"✅ 案件分類: {case_type}")
    
    # 4. 生成各部分內容
    if FULL_MODE:
        print("\n🔍 搜尋相似案例...")
        
        # 事實部分
        print("📋 生成事實陳述...")
        facts_query = sections["accident_facts"][:200]
        facts_vector = embed(facts_query)
        facts_hits = es_search(facts_vector, case_type, top_k=3, label="Facts")
        
        if facts_hits:
            case_ids = [hit["_source"]["case_id"] for hit in facts_hits]
            reranked_case_ids = rerank_case_ids_by_paragraphs(facts_query, case_ids, "Facts")
            similar_cases = get_complete_cases_content(reranked_case_ids[:2])
            
            facts_context = "\n\n".join(similar_cases[:2]) if similar_cases else ""
            facts_prompt = f"""請根據以下事故描述生成正式的起訴狀事實陳述部分：

## 事故描述：
{sections["accident_facts"]}

## 參考案例：
{facts_context}

## 要求：
1. 使用正式的法律文書用語
2. 按時間順序組織事實
3. 重點突出過失行為和因果關係
4. 格式要整齊有條理"""
            facts_result = call_llm(facts_prompt)
        else:
            facts_result = f"事故發生緣由：{sections['accident_facts']}"
        
        # 法條部分
        print("⚖️ 生成法條適用...")
        applicable_laws = determine_applicable_laws(
            sections["accident_facts"], 
            sections["injuries"], 
            sections["compensation_facts"], 
            parties
        )
        
        if applicable_laws:
            laws_vector = embed(f"民法第{applicable_laws[0]}條")
            laws_hits = es_search(laws_vector, case_type, top_k=2, label="Laws")
            
            if laws_hits:
                laws_content = "\n".join([hit["_source"]["content"] for hit in laws_hits])
                laws_prompt = f"""請根據以下法條內容生成起訴狀的法條適用部分：

## 適用法條：
{laws_content}

## 案件事實：
{sections["accident_facts"]}

## 要求：
1. 明確引用法條條文
2. 說明法條與本案事實的對應關係
3. 論證被告責任成立的法律依據"""
                laws_result = call_llm(laws_prompt)
            else:
                laws_result = f"適用法條：民法第{"、第".join(applicable_laws)}條"
        else:
            laws_result = "適用法條：民法第184條第1項前段"
        
        # 損害賠償部分
        print("💰 生成損害賠償...")
        comp_query = sections["compensation_facts"][:200]
        comp_vector = embed(comp_query)
        comp_hits = es_search(comp_vector, case_type, top_k=3, label="Compensation")
        
        if comp_hits:
            comp_case_ids = [hit["_source"]["case_id"] for hit in comp_hits]
            comp_reranked = rerank_case_ids_by_paragraphs(comp_query, comp_case_ids, "Compensation")
            comp_cases = get_complete_cases_content(comp_reranked[:2])
            
            comp_context = "\n\n".join(comp_cases[:2]) if comp_cases else ""
            comp_prompt = f"""請根據以下損害事實生成詳細的損害賠償計算：

## 損害事實：
{sections["compensation_facts"]}

## 參考案例：
{comp_context}

## 要求：
1. 詳細列出各項損害項目
2. 計算方式要清楚具體
3. 包含醫療費、工作損失、精神慰撫金等
4. 提供總計金額"""
            comp_result = call_llm(comp_prompt)
        else:
            comp_result = f"損害賠償：{sections['compensation_facts']}"
    
    else:
        # 簡化模式：直接使用輸入內容
        facts_result = sections["accident_facts"]
        laws_result = "適用法條：民法第184條第1項前段"
        comp_result = sections["compensation_facts"]
    
    # 生成最終起訴狀
    print("\n📋 生成完整起訴狀...")
    final_lawsuit = generate_lawsuit_content(facts_result, laws_result, comp_result)
    
    # 輸出結果
    print("\n" + "="*60)
    print("🏛️ 生成的起訴狀內容")
    print("="*60)
    print(final_lawsuit)
    
    # 儲存結果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"lawsuit_{timestamp}.txt"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(final_lawsuit)
        print(f"\n✅ 起訴狀已儲存為：{filename}")
    except Exception as e:
        print(f"\n⚠️ 檔案儲存失敗：{e}")

def main():
    """主程式"""
    print("\n🏛️ 法律文書生成系統 (舊混合版本)")
    print(f"📊 模式: {'完整模式' if FULL_MODE else '簡化模式'}")
    
    while True:
        print("\n" + "="*40)
        print("請選擇功能：")
        print("1. 生成起訴狀")
        print("2. 檢查系統狀態")
        print("3. 退出")
        
        choice = input("\n請輸入選項 (1-3): ").strip()
        
        if choice == "1":
            interactive_generate_lawsuit()
        elif choice == "2":
            print(f"\n📊 系統狀態：")
            print(f"模式: {'完整模式' if FULL_MODE else '簡化模式'}")
            print(f"ES連接: {'✅' if FULL_MODE and ES_HOST else '❌'}")
            print(f"Neo4j連接: {'✅' if FULL_MODE and NEO4J_DRIVER else '❌'}")
        elif choice == "3":
            print("\n👋 再見！")
            break
        else:
            print("\n❌ 無效選項，請重新選擇")

if __name__ == "__main__":
    main()