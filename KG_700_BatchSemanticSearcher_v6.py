# KG_700.py
import os
import re
import sys
import json
import torch
import requests
import jieba
import time  
from collections import Counter
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from transformers import AutoTokenizer, AutoModel
from ts_define_case_type import get_case_type  
from ts_input_filter import get_people  
from ts_prompt import (
    get_facts_prompt,
    get_compensation_prompt_part1_single_plaintiff,
    get_compensation_prompt_part1_multiple_plaintiffs,
    get_compensation_prompt_part3,
    get_compensation_prompt_from_raw_input
)
from KG_110_input_enhancer import register_to_jieba
register_to_jieba()


# 自動載入環境變數
load_dotenv()

# 模型與裝置設定
BERT_MODEL = "shibing624/text2vec-base-chinese"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TOKENIZER = AutoTokenizer.from_pretrained(BERT_MODEL)
MODEL = AutoModel.from_pretrained(BERT_MODEL, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32).to(device)

# ES 與 Neo4j 初始化
ES = Elasticsearch(
    os.getenv("ELASTIC_HOST"),
    basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
    verify_certs=False,
)
CHUNK_INDEX = "legal_kg_chunks"

NEO4J_DRIVER = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
)

# 類型 fallback 對照表
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

# 從 ts_input_filter 抽取姓名結果中解析原告與被告姓名
def extract_parties_from(party_info: str) -> dict:
    result = {"原告": "未提及", "被告": "未提及"}
    match = re.search(r"原告[:：]?(.*?)\n被告[:：]?(.*?)\n", party_info + "\n", re.S)
    if match:
        result["原告"] = match.group(1).strip()
        result["被告"] = match.group(2).strip()
    return result

# 文字向量化
def embed(text: str):
    t = TOKENIZER(text, truncation=True, padding="max_length", max_length=512, return_tensors="pt")
    t = {k: v.to(device) for k, v in t.items()}
    with torch.no_grad():
        vec = MODEL(**t).last_hidden_state.mean(dim=1).squeeze()
    return vec.cpu().numpy().tolist()

# ES 搜尋（強化 fallback 機制 + 印出 payload）
def es_search(query_vector, case_type: str, top_k: int = 5, label: str = "Facts"):
    def _search(label_filter, case_type_filter):
        must_clause = [{"match": {"label": label_filter}}]
        if case_type_filter:
            must_clause.append({"term": {"case_type.keyword": case_type_filter}})
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
        print("\n📤 查詢 相似段落 (向量略去)...")
        return ES.search(index=CHUNK_INDEX, body=body)["hits"]["hits"]

    print(f"🔎 使用 case_type='{case_type}' 搜索...")
    hits = _search(label, case_type)
    if not hits:
        fallback = CASE_TYPE_MAP.get(case_type, "單純原被告各一")
        if fallback != case_type:
            print(f"⚠️ 使用 case_type='{case_type}' 無結果，改為 fallback='{fallback}' 重新搜尋...")
            hits = _search(label, fallback)
    if not hits:
        print("⚠️ 再次無結果，將不限案件類型進行最寬鬆搜尋...")
        hits = _search(label, None)
    return hits

def rerank_case_ids_by_paragraphs(query_text: str, case_ids: List[str], label: str = "Facts") -> List[str]:
    """
    根據段落級資料（legal_kg_paragraphs），以 cosine 相似度重新排序案例
    """
    print("\n📘 啟動段落級 rerank...")
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    # 嵌入用戶輸入全文
    query_vec = embed(query_text)
    query_vec_np = np.array(query_vec).reshape(1, -1)

    scored_cases = []
    for cid in case_ids:
        res = ES.search(
            index="legal_kg_paragraphs",
            query={
                "bool": {
                    "must": [
                        {"term": {"case_id": cid}},
                        {"term": {"label": label}}
                    ]
                }
            },
            size=1
        )
        hits = res.get("hits", {}).get("hits", [])
        if hits:
            vec = hits[0]['_source']['embedding']
            para_vec_np = np.array(vec).reshape(1, -1)
            score = cosine_similarity(query_vec_np, para_vec_np)[0][0]
            scored_cases.append((cid, score))

    # 根據相似度排序
    scored_cases.sort(key=lambda x: x[1], reverse=True)
    print("\n🎯 Rerank 後相似度排序:")
    for i, (cid, score) in enumerate(scored_cases, 1):
        print(f"{i}. Case {cid} ➜ 相似度: {score:.4f}")

    return [cid for cid, _ in scored_cases]

# Neo4j 抓取補強資訊
def query_laws(case_ids):
    counter = Counter()
    law_text_map = {}
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
    return counter, law_text_map

def keyword_law_filter(fact_text: str, injury_text: str, compensation_text: str) -> List[str]:
    """從三段事實中比對出命中的法條條號"""
    legal_mapping = {
        "民法第184條第1項前段": ["未注意", "過失", "損害賠償", "侵害他人", "侵害權利"],
        "民法第185條": ["共同侵害", "共同行為", "數人侵害", "造意人", "共同加害"],
        "民法第187條": ["無行為能力", "限制行為能力", "法定代理人", "識別能力", "未成年", "精神障礙"],
        "民法第188條": ["受僱人", "僱用人", "雇傭", "連帶賠償", "職務上", "雇主責任", "受雇"],
        "民法第191-2條": ["汽車", "機車", "交通事故", "高速公路", "動力車輛", "駕駛"],
        "民法第193條第1項": ["損失", "醫療費用", "工作損失", "薪資", "就醫", "勞動能力", "收入損失"],
        "民法第195條第1項前段": ["精神", "慰撫金", "痛苦", "名譽", "健康", "隱私", "貞操", "人格"],
        "民法第213條": ["回復原狀", "回復", "給付金錢", "損害發生"],
        "民法第216條": ["填補損害", "所失利益", "預期利益", "損失補償"],
        "民法第217條": ["被害人與有過失", "過失相抵", "重大損害原因", "損害擴大"],
        "民法第190條": ["動物", "寵物", "狗", "貓", "動物攻擊", "動物咬傷"],

    }

    combined_text = "。".join([fact_text, injury_text, compensation_text])
    matched = set()
    for law, keywords in legal_mapping.items():
        if any(k in combined_text for k in keywords):
            matched.add(law)

    print("📌 關鍵字命中的法條:", matched)
    return sorted(matched)


def fetch_full_lawsuit_from_neo4j(driver, case_id):
    """從 Neo4j 撈出完整四段起訴狀內容（Facts, Laws, Compensation, Conclusion）"""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Case {case_id: $cid})-[:包含]->(f:Facts)-[:適用]->(l:Laws)-[:計算]->(comp:Compensation)-[:推導]->(con:Conclusion)
            RETURN f.description AS fact, l.description AS law, comp.description AS comp, con.description AS con
        """, cid=case_id).single()

        if result:
            return [
                result.get("fact", "").strip(),
                result.get("law", "").strip(),
                result.get("comp", "").strip(),
                result.get("con", "").strip(),
            ]
        else:
            return []

def parse_amount_string(raw):
    # 嘗試從文字中找出「xxx元」或「xxx萬元」
    match_million = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?=\s*萬[\s\u5143元])", raw)
    if match_million:
        return float(match_million.group(1).replace(",", "")) * 10000
    match_plain = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?=\s*[\u5143元])", raw)
    if match_plain:
        return float(match_plain.group(1).replace(",", ""))
    return None

def extract_calculate_tags(text: str) -> Dict[str, float]:
    pattern = r'<calculate>(.*?)</calculate>'
    matches = re.findall(pattern, text)
    print(f"找到 {len(matches)} 個 <calculate> 標籤內容")
    sums = {}
    default_count = 0

    for match in matches:
        plaintiff_id = "default"
        name_match = re.search(r'原告(\w+)', match)
        if name_match:
            plaintiff_id = name_match.group(1)
        else:
            if "default" in sums:
                default_count += 1
                plaintiff_id = f"原告{default_count}"

        numbers = re.findall(r'\d+', match)
        if numbers:
            total = sum(float(num) for num in numbers)
            if plaintiff_id in sums:
                default_count += 1
                plaintiff_id = f"原告{default_count}"
            sums[plaintiff_id] = total
            print(f"計算 {plaintiff_id}: {total}")

    return sums


def query_conclusion_amounts(case_ids):
    value_dict = {}
    with NEO4J_DRIVER.session() as session:
        for cid in case_ids:
            result = session.run("""
                MATCH (c:Case {case_id: $cid})-[:包含]->(:Facts)-[:適用]->(:Laws)
                      -[:計算]->(:Compensation)-[:推導]->(:Conclusion)-[:包含]->(cd:ConclusionDetail)
                WHERE cd.name CONTAINS "總計"
                RETURN cd.name AS name, cd.value AS value
            """, cid=cid)

            rows = list(result)
            if not rows:
                continue
            for row in rows:
                raw = row["value"]
                print(f"🧾 Case ID {cid} - {row['name']} 原始 value: {raw}")
                parsed = parse_amount_string(raw)
                if parsed:
                    value_dict[cid] = parsed
    if not value_dict:
        return {}, 0
    avg = sum(value_dict.values()) / len(value_dict)
    return value_dict, avg


def query_compensation_details(case_ids):
    detail_dict = {}
    with NEO4J_DRIVER.session() as session:
        for cid in case_ids:
            result = session.run("""
                MATCH (c:Case {case_id: $cid})-[:包含]->(:Facts)-[:適用]->(:Laws)
                      -[:計算]->(:Compensation)-[:包含]->(cd:CompensationDetail)
                RETURN cd.text AS text
            """, cid=cid)
            details = [r["text"] for r in result if r["text"]]
            if details:
                detail_dict[cid] = details
    return detail_dict

def extract_facts_and_injuries(text):
    fact_match = re.search(r"事故發生緣由[:：]?\s*(.*?)(?=原告受傷情形|請求賠償|$)", text, re.S)
    injury_match = re.search(r"(原告)?受傷情形[:：]?\s*(.*?)(?=請求賠償|$)", text, re.S)
    return (fact_match.group(1).strip() if fact_match else text,
            injury_match.group(2).strip() if injury_match else text)

def get_case_summary_prompt(accident_facts, injuries):
    return f"""規則:
1. 依據輸入的事實描述，生成結構清晰的事故摘要，完整保留所有關鍵資訊，不得遺漏。
2. 僅使用輸入中明確提供的資訊，不得推測或補充未出現在輸入中的內容（例如：刑事判決）。
3. 以簡潔扼要的方式陳述內容，避免冗長敘述，確保資訊清楚易讀。
4. 若某個資訊缺失，則不輸出該項目，填入「無」或「不詳」。
5. 若事實中出現如「天候正常」「無不能注意情事」「路況良好」等間接描述，亦請納入 [當天環境]。
輸出格式：
=======================
[事故緣由]: [內容]
[當天環境]: [內容]
[傷勢情形]: [內容]
=======================
嚴格遵照上述規則，根據輸入資訊生成事故摘要。

事故事實：
{accident_facts}

受傷情形：
{injuries}
"""

def query_case_fulltext_sections(case_id: str) -> dict:
    """ 從 Neo4j 抓取起訴狀四段落 """
    with NEO4J_DRIVER.session() as session:
        result = session.run("""
            MATCH (c:Case {case_id: $cid})-[:包含]->(f:Facts)
            OPTIONAL MATCH (f)-[:適用]->(l:Laws)
            OPTIONAL MATCH (l)-[:計算]->(comp:Compensation)
            OPTIONAL MATCH (comp)-[:推導]->(con:Conclusion)
            RETURN f.description AS facts,
                   l.description AS laws,
                   comp.description AS compensation,
                   con.description AS conclusion
        """, cid=case_id).single()

        return {
            "facts": result["facts"] if result else "",
            "laws": result["laws"] if result else "",
            "compensation": result["compensation"] if result else "",
            "conclusion": result["conclusion"] if result else "",
        }

def generate_final_prompt(
    user_query: str,
    summary: str,
    top_facts: List[str],
    law_counts: Dict[str, int],
    law_texts: List[str],
    amount_stats: Dict[str, Any],
    compensation_details: Optional[str],
    full_sections: Dict[str, str],
    parties: Dict[str, str],
    case_type: str
) -> str:
    """
    重寫後的起訴書 Prompt 組裝函式，區分資訊來源，清楚提示 LLM。
    """

    # 🔹【案件當事人】
    party_block = (
        f"🔹【案件當事人】\n"
        f"- 原告：{parties.get('原告', '未提及')}\n"
        f"- 被告：{parties.get('被告', '未提及')}\n"
        f"- 案件類型：{case_type or '未分類'}\n"
    )

    # 🔹【律師輸入原文】
    query_block = f"🔹【律師輸入原文】\n{user_query.strip()}"

    # 🔹【本案摘要（由 LLM 從輸入推論）】
    summary_block = f"🔹【本案摘要】（依據輸入，自動整理）\n{summary.strip()}"

    # 🔹【參考案例摘要（Top-K）】
    if top_facts:
        similar_case_block = "🔹【參考案例摘要】（Top-K 相似案例節錄，僅供參考）\n"
        for i, s in enumerate(top_facts, 1):
            similar_case_block += f"{i}. {s.strip()}\n"
    else:
        similar_case_block = "🔹【參考案例摘要】\n無"

    # 🔹【常見法條摘要】
    if law_texts:
        law_text_block = "🔹【常見法條摘要】（從 Top-K 類似案件統計彙整）\n"
        for i, text in enumerate(law_texts, 1):
            law_text_block += f"{i}. {text.strip()}\n"
        law_text_block += "\n以上法條供參考，不代表本案一定適用。"
    else:
        law_text_block = "🔹【常見法條摘要】\n無"

    # 🔹【賠償統計摘要】
    amount_lines = []
    if isinstance(amount_stats.get("avg"), (int, float)):
        amount_lines.append(f"- 平均賠償金額：約 {format(amount_stats['avg'], ',')} 元")
    for cid, val in amount_stats.get("values", {}).items():
        amount_lines.append(f"- Case {cid}：{format(val, ',')} 元")
    if not amount_lines:
        amount_lines = ["（無統計結果）"]
    amount_text = "🔹【賠償統計摘要】（從 Top-K 結論節點擷取）\n" + "\n".join(amount_lines)

    # 🔹【Top1 範本四段】（僅供格式參考）
    full_example = ""
    if full_sections:
        full_example = (
            "🔹【Top1 起訴書範本】（以下僅為格式參考，請勿直接引用內容）\n"
            f"一、事故發生經過：\n{full_sections.get('facts', '').strip()}\n\n"
            f"二、法律依據：\n{full_sections.get('laws', '').strip()}\n\n"
            f"三、損害項目：\n{full_sections.get('compensation', '').strip()}\n\n"
            f"四、結論：\n{full_sections.get('conclusion', '').strip()}\n"
        )

    # 📌【撰寫指令】
    instruction = (
        "📌【撰寫指令】\n"
        "請根據上述資訊撰寫完整的起訴狀草稿。\n"
        "必須依照以下結構產出：\n"
        "一、事故發生經過\n"
        "二、法律依據\n"
        "三、損害項目\n"
        "四、結論\n\n"
        "請勿抄襲範本或其他案例內容，應根據律師輸入與本案摘要重新組織語句，使用清晰、客觀的法律語言描述。"
    )

    # 🔧 組裝 Final Prompt
    final_prompt = "\n\n".join([
        party_block,
        query_block,
        summary_block,
        similar_case_block,
        law_text_block,
        amount_text,
        instruction,
        full_example
    ])

    return final_prompt
    


def generate_case_summary(text):
    print("\n生成案件摘要...")
    facts, injuries = extract_facts_and_injuries(text)
    prompt = get_case_summary_prompt(facts, injuries)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma3:27b",
            "prompt": prompt,
            "stream": True
        }
    )

    if response.status_code == 200:
        result = response.json()["response"]
        print("\n📋 案件摘要：\n")
        print(result.strip())
    else:
        print("❌ Ollama 請求錯誤:", response.status_code, response.text)

def get_laws_prompt(article_ids: List[str], law_descriptions: dict) -> str:
    """
    根據條號與對應描述，自動組成法律依據段落 prompt
    """
    if not article_ids:
        return "查無任何相關法條，請確認是否有提供足夠事實資料。"

    law_segments = [f"「{law_descriptions[a]}」" for a in article_ids if a in law_descriptions]
    law_text_block = "、\n".join(law_segments)
    article_list = "、".join(article_ids)

    return f"""你是一位熟悉台灣民事訴訟的律師助理。請依據下列條文說明與條號，撰寫法律依據段落，格式需正式、客觀，不得過度推論或加入未提供事實。

【條文說明】
{law_text_block}

【條號】
{article_list}

請依以下格式撰寫：

按「（條文簡述1）」、「（條文簡述2）」...，民法第XXX條、第YYY條...分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任：
"""

# 法條條文說明表
law_descriptions_dict = {
    "民法第184條第1項前段": "因故意或過失，不法侵害他人之權利者，負損害賠償責任。",
    "民法第185條": "數人共同不法侵害他人之權利者，連帶負損害賠償責任。",
    "民法第187條": "無行為能力或限制行為能力人之法定代理人，應負賠償責任。",
    "民法第188條": "受僱人因執行職務，不法侵害他人之權利者，由僱用人與行為人連帶負責。",
    "民法第191-2條": "動力車輛在使用中致人損害者，駕駛人應負損害賠償責任。",
    "民法第193條第1項": "不法侵害他人之身體或健康者，應負損害賠償責任。",
    "民法第195條第1項前段": "不法侵害人格法益而情節重大者，得請求精神慰撫金。",
    "民法第213條": "負損害賠償責任者，應回復損害發生前之原狀。",
    "民法第216條": "損害賠償包括已發生損害與所失利益。",
    "民法第217條": "被害人與有過失時，法院得減輕賠償金額。",
    "民法第190條": "動物加損害於他人者，由其占有人負損害賠償責任。"
    
}

def generate_four_parts(
    user_query: str,
    accident_facts: str,
    injuries: str,
    summary: str,
    reference_facts: str,
    law_texts: list,
    comp_details: list,
    avg_amount: float,
    plaintiffs_info: str = "",
    top_law_numbers: List[str] = None,
    raw_comp_text: str = ""
) -> str:
    """
    四段式生成起訴狀，使用 raw_comp_text 作為損害段輸入，清理標題與附件語句。
    """

    # 🟦 第一段：事故發生經過
    print("\n📍開始生成第一段（事故發生經過）...")
    facts_prompt = get_facts_prompt(accident_facts, reference_facts)
    facts_resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma3:27b", "prompt": facts_prompt, "stream": False}
    )
    facts_result = facts_resp.json()["response"].strip() if facts_resp.ok else "⚠️ 無法生成事實段落"
    facts_result = re.sub(r'^一[、.． ]+', '', facts_result)
    facts_result = "一、事實概述：\n" + facts_result

    time.sleep(1)

    # 🟧 第二段：法律依據
    print("\n📍開始生成第二段（法律依據）...")
    laws_prompt = get_laws_prompt(top_law_numbers, law_descriptions_dict)
    laws_resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma3:27b", "prompt": laws_prompt, "stream": False}
    )
    laws_result = laws_resp.json()["response"].strip() if laws_resp.ok else "⚠️ 無法生成法律段落"
    laws_result = re.sub(r'^#+ *二[、.． ]*法律依據[:：]?', '', laws_result)
    laws_result = "二、法律依據：\n" + laws_result

    time.sleep(1)

    # 🟥 第三段：損害項目（使用 raw_comp_text）
    print("\n📍開始生成第三段（損害項目）...")
    comp_prompt = get_compensation_prompt_from_raw_input(
        raw_text=raw_comp_text,
        avg=avg_amount,
        plaintiffs_info=plaintiffs_info
    )
    comp_resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma3:27b", "prompt": comp_prompt, "stream": False}
    )
    comp_result = comp_resp.json()["response"].strip() if comp_resp.ok else "⚠️ 無法生成損害段落"
    comp_result = re.sub(r'(詳如附件.*?|附件.*?所示)', '', comp_result)
    comp_result = "三、損害項目：\n" + comp_result

    time.sleep(1)

    # 🟩 第四段：結論
    print("\n📍開始生成第四段（結論）...")
    conclusion_prompt = get_compensation_prompt_part3(comp_result, "請求如上所列", plaintiffs_info=plaintiffs_info)
    con_resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma3:27b", "prompt": conclusion_prompt, "stream": False}
    )
    conclusion_result = con_resp.json()["response"].strip() if con_resp.ok else "⚠️ 無法生成結論段落"
    conclusion_result = "四、結論：" + conclusion_result

    # 🧾 組裝
    return "\n\n".join([facts_result, laws_result, comp_result, conclusion_result])



def generate_compensation_facts_snippet(details: list) -> str:
    if not details:
        return "無詳細說明。"
    return "\n".join(f"- {d.strip()}" for d in details if d and isinstance(d, str))


def process_query(query_text: str):
    print("🔍 處理用戶查詢分類...")
    
    print("\n🧪 斷詞測試（含新詞表）:")
    test = "原告於事故中受有腦震盪及左膝蓋骨裂，須休養三個月。"
    print("/".join(jieba.cut(test)))

    # 1️⃣ 抽取姓名與類型
    party_info_raw = get_people(query_text)
    parties = extract_parties_from(party_info_raw)

    print("原告:", parties.get("原告", "-"))
    print("被告:", parties.get("被告", "-"))

    case_type = get_case_type(query_text)
    if isinstance(case_type, (tuple, list)):
        case_type = case_type[0]
    print("案件類型:", case_type)

    # 2️⃣ 選擇搜尋參數
    search_type = input("請選擇搜尋類型 (1=全文, 2=fact): ").strip()
    index_label = "Facts" if search_type == "2" else "FullText"
    top_k = int(input("請輸入要搜尋的 Top-K 數量: ").strip())
    grab_type = input("請選擇要抓取的內容 (1=law, 2=law+conclusion): ")

    # 3️⃣ ES 搜尋
    hits = es_search(embed(query_text), case_type, top_k, label=index_label)
    if not hits:
        print("❌ 查無相似案例")
        return
    retrieved_case_ids = [hit['_source']['case_id'] for hit in hits]
    case_ids = rerank_case_ids_by_paragraphs(query_text, retrieved_case_ids, label=index_label)


    # 4️⃣ 印出相似段落摘要
    top_facts = []
    for i, hit in enumerate(hits, 1):
        cid = hit['_source']['case_id']
        print(f"{i}. Case ID: {cid}, 相似度分數: {hit['_score']:.4f}")
        original_text = hit["_source"].get("original_text", "").strip()
        if original_text:
            print(f"🔸 相似段落內容:\n{original_text}\n")
            top_facts.append(original_text)

        
    # 5️⃣ Neo4j 補強資訊
    if grab_type.strip() in {"1", "2"}:
        law_counts, law_texts = query_laws(case_ids)
    else:
        law_counts, law_texts = {}, {}

    if grab_type.strip() == "2":
        values_dict, avg = query_conclusion_amounts(case_ids)
        detail_dict = query_compensation_details(case_ids)
    else:
        values_dict, avg = {}, 0
        detail_dict = {}


    # 6️⃣ 案件摘要 by Gemma
    print("\n📋 案件摘要（Gemma 逐行生成中）...\n")
    accident_facts, injuries = extract_facts_and_injuries(query_text)
    # ⏬ 抽取「三、請求賠償的事實根據」段落作為損害輸入
    def extract_raw_compensation_text(user_input: str) -> str:
        match = re.search(r"三[、.．：:]?\s*請求賠償的事實根據[:：]?\s*(.*)", user_input, re.S)
        return match.group(1).strip() if match else ""

    raw_comp_text = extract_raw_compensation_text(query_text)

    summary_prompt = get_case_summary_prompt(accident_facts, injuries)
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "gemma3:27b", "prompt": summary_prompt, "stream": True}
    )
    summary_lines = []
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                try:
                    content = json.loads(line.decode("utf-8"))["response"]
                    print(content, end="", flush=True)
                    summary_lines.append(content)
                except Exception:
                    continue
        print("\n")
    else:
        print("❌ LLM 請求錯誤:", response.status_code, response.text)
        return
    summary = "".join(summary_lines).strip()

    # 7️⃣ 抓 Top1 範本四段（提供格式參考）
    top1_case_id = case_ids[0]
    full_sections = query_case_fulltext_sections(top1_case_id)
    print("\n📘 Top1 範例起訴書（僅供格式參考）:")
    # print("一、事實概述：")
    print(full_sections.get("facts", "").strip(), "\n")
    # print("二、法律依據：")
    print(full_sections.get("laws", "").strip(), "\n")
    print("三、損害賠償項目：")
    print(full_sections.get("compensation", "").strip(), "\n")
    print("四、結論：")
    print(full_sections.get("conclusion", "").strip(), "\n")


    # 8️⃣ 整理損害事實字串
    comp_details = detail_dict.get(top1_case_id, [])
    comp_facts = generate_compensation_facts_snippet(comp_details)

    # 9️⃣ 四段式 LLM 生成
    top_law_numbers = keyword_law_filter(accident_facts, injuries, comp_facts)
    top_law_texts = [law_texts[l] for l in top_law_numbers if l in law_texts]
    if not top_law_texts:
        top_law_texts = list(law_texts.values())[:3]  # fallback


    full_text = generate_four_parts(
        user_query=query_text,
        accident_facts=accident_facts,
        injuries=injuries,
        summary=summary,
        reference_facts=full_sections.get("facts", ""),
        law_texts=top_law_texts,
        comp_details=comp_details,
        avg_amount=avg,
        plaintiffs_info=parties.get("原告", ""),
        top_law_numbers=top_law_numbers,
        raw_comp_text=raw_comp_text  # ✅ 新增這行
    )


    # 🔟 顯示最終結果
    print("\n📑 最終生成的四段起訴狀：\n")
    print(full_text)


if __name__ == "__main__":
    print("請輸入 User Query (請貼上完整的律師回覆文本，格式需包含「一、二、三、」三個部分)")
    print("輸入完畢後按 Enter 再輸入 'q' 或 'quit' 結束:")

    buf = []
    while True:
        line = input()
        if line.strip().lower() in {"q", "quit"}:
            break
        buf.append(line)

    query_text = "\n".join(buf).strip()
    if query_text:
        process_query(query_text)
    else:
        print("⚠️  未輸入任何內容。")