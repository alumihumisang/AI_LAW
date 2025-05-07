import os
import re
import sys
import json
import torch
import requests
from collections import Counter
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from neo4j import GraphDatabase
from transformers import AutoTokenizer, AutoModel
from ts_define_case_type import get_case_type  # ✅ 改為引用同學邏輯
from ts_input_filter import get_people  # ✅ 加入姓名抽取模組

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
        print("\n📤 查詢 payload (向量略去)...")
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

def parse_amount_string(raw):
    # 嘗試從文字中找出「xxx元」或「xxx萬元」
    match_million = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?=\s*萬[\s\u5143元])", raw)
    if match_million:
        return float(match_million.group(1).replace(",", "")) * 10000
    match_plain = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?=\s*[\u5143元])", raw)
    if match_plain:
        return float(match_plain.group(1).replace(",", ""))
    return None

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


def generate_case_summary(text):
    print("\n生成案件摘要...")
    facts, injuries = extract_facts_and_injuries(text)
    prompt = get_case_summary_prompt(facts, injuries)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "kenneth85/llama-3-taiwan:8b-instruct-dpo",
            "prompt": prompt,
            "stream": False
        }
    )

    if response.status_code == 200:
        result = response.json()["response"]
        print("\n📋 案件摘要：\n")
        print(result.strip())
    else:
        print("❌ Ollama 請求錯誤:", response.status_code, response.text)

def generate_final_prompt(user_query, summary_text, similar_facts, law_counts, law_texts, amount_stats, compensation_details):
    prompt = "根據以下律師輸入內容與相關案例資訊，請生成一份格式清晰的起訴狀草稿：\n\n"

    # A. 律師輸入原文
    prompt += "🔹【律師輸入內容】：\n" + user_query.strip() + "\n\n"

    # B. 案件摘要
    prompt += "🔹【案件摘要】：\n" + summary_text.strip() + "\n\n"

    # C. Top-K 語意相似段落
    if similar_facts:
        prompt += "🔹【相似案例段落（依語意相近排序）】：\n"
        for i, fact in enumerate(similar_facts[:3], 1):
            prompt += f"{i}. {fact.strip()}\n"
        prompt += "\n"

    # D. 法條摘要
    if law_counts:
        prompt += "🔹【Top 案例法條】：\n"
        for name, count in law_counts.most_common(5):
            text = law_texts.get(name, "")
            prompt += f"【{name}】(出現次數：{count})\n{text.strip()}\n\n"

    # E. 賠償金額統計與明細
    if amount_stats:
        amount_dict, avg = amount_stats
        prompt += "🔹【賠償金額統計】：\n"
        for cid, amt in amount_dict.items():
            prompt += f"Case ID {cid}: {amt:,.0f} 元\n"
        prompt += f"\n💡 平均金額：{avg:,.0f} 元\n\n"

    if compensation_details:
        prompt += "🔹【賠償項目明細】：\n"
        for cid, items in compensation_details.items():
            for i in items:
                prompt += f"Case ID {cid}: {i.strip()}\n"
        prompt += "\n"

    # F. 任務提示
    prompt += "請依照一般民事起訴書格式，撰寫出完整起訴書草稿，結構建議為：\n一、事故發生經過\n二、法律依據\n三、損害項目\n四、結論。\n\n請參考以上資訊進行撰寫。"

    return prompt.strip()



def process_query(query_text: str):
    print("🔍 處理用戶查詢分類...")

    # 萃取原告與被告
    party_info_raw = get_people(query_text)
    parties = extract_parties_from(party_info_raw)
    print("原告:", parties.get("原告", "-"))
    print("被告:", parties.get("被告", "-"))
    print("CASE INFO:", f"原告:{parties.get('原告', '-')}")

    # 判斷案件類型
    case_type = get_case_type(query_text)
    if isinstance(case_type, (tuple, list)):
        case_type = case_type[0]
    print("案件類型:", case_type)

    # 互動式選擇
    search_type = input("請選擇搜尋類型 (1=全文, 2=fact): ").strip()
    index_label = "Facts" if search_type == "2" else "FullText"
    top_k = int(input("請輸入要搜尋的 Top-K 數量: ").strip())
    grab_type = input("請選擇要抓取的內容 (1=law, 2=law+conclusion): ")

    # Elasticsearch 搜尋
    print(f"\n在 Elasticsearch 中搜索 '{index_label}' 類型的 Top {top_k} 個文檔...")
    hits = es_search(embed(query_text), case_type, top_k, label=index_label)
    if not hits:
        print("❌ 查無相似案例")
        return

    # 搜尋結果顯示
    case_ids = []
    top_facts = []  # 🔸 收集原始段落文字
    for i, hit in enumerate(hits, 1):
        cid = hit['_source']['case_id']
        case_ids.append(cid)
        score = hit["_score"]
        original_text = hit["_source"].get("original_text", "").strip()
        print(f"{i}. Case ID: {cid}, 相似度分數: {score:.4f}")
        if original_text:
            print(f"🔸 相似段落內容:\n{original_text}\n")
            top_facts.append(original_text)

    # 補強資訊：法條
    if grab_type.strip() in {"1", "2"}:
        law_counts, law_texts = query_laws(case_ids)
        print("\n📚 法條出現頻率:")
        for k, v in law_counts.most_common():
            print(f"法條 {k}: 出現 {v} 次")
        print("\n📘 法條內容對照表:")
        for k, text in law_texts.items():
            print(f"【{k}】\n{text}\n")

    # 補強資訊：結論金額與明細
    if grab_type.strip() == "2":
        values_dict, avg = query_conclusion_amounts(case_ids)
        print("\n💰 賠償金額統計:")
        for cid in case_ids:
            if cid in values_dict:
                print(f"Case ID {cid}: {values_dict[cid]:,.2f} 元")
            else:
                print(f"Case ID {cid}: ⛔ 無法解析金額")
        print(f"平均賠償金額: {avg:,.2f} 元")

        detail_dict = query_compensation_details(case_ids)
        print("\n📄 各案賠償項目明細:")
        for cid in case_ids:
            if cid in detail_dict:
                for desc in detail_dict[cid]:
                    print(f"Case ID {cid}: {desc}")
            else:
                print(f"Case ID {cid}: ⛔ 無法取得結論明細")

    # ✅ 產生案件摘要
    generate_case_summary(query_text)

    # ✅ 組裝 Final Prompt
    facts, injuries = extract_facts_and_injuries(query_text)
    summary_prompt = get_case_summary_prompt(facts, injuries)
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "kenneth85/llama-3-taiwan:8b-instruct-dpo", "prompt": summary_prompt, "stream": False}
    )
    summary = response.json()["response"] if response.status_code == 200 else "⛔ 無法取得摘要"

    final_prompt = generate_final_prompt(
    query_text,
    summary,
    top_facts[:3],
    law_counts,
    law_texts,
    (values_dict, avg),
    detail_dict
)
    print("\n🧠 組裝後 Final Prompt：\n")
    print(final_prompt)
    
    # === 執行 LLM 起訴書生成 ===
    print("\n📤 正在使用 LLM 生成起訴書...\n")
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "kenneth85/llama-3-taiwan:8b-instruct-dpo",
            "prompt": final_prompt,
            "stream": False
        }
    )

    if response.status_code == 200:
        result = response.json()["response"]
        print("\n📑 最終生成的起訴書：\n")
        print(result.strip())
    else:
        print("❌ LLM 請求失敗:", response.status_code, response.text)




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