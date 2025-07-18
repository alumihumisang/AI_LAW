# ✅ KG_6.75_Chunkwise_Query_RAG.py：長輸入切句後查 ES 並組成 LLM prompt 格式 + 案例總結 + citation 標記 + 類型統計

import os
import re
import torch
import json
import numpy as np
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from transformers import AutoTokenizer, AutoModel
from collections import Counter, defaultdict

load_dotenv()
BERT_MODEL = "shibing624/text2vec-base-chinese"
torch_dtype = torch.float16

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class ChunkwiseSemanticSearcher:
    def __init__(self):
        self.es = Elasticsearch(
            os.getenv("ELASTIC_HOST"),
            basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
            verify_certs=False
        )
        self.tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL)
        self.model = AutoModel.from_pretrained(BERT_MODEL, torch_dtype=torch_dtype).to(device)

    def split_by_punctuation(self, text):
        return [s.strip() for s in re.split(r'[。！？；\n]', text) if s.strip()]

    def embed(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", padding="max_length", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()

    def search_single_chunk(self, query_text, index_name="legal_kg_chunks", top_k=1):
        vector = self.embed(query_text)
        es_query = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": vector.tolist()}
                    }
                }
            }
        }
        response = self.es.search(index=index_name, body=es_query)
        return response["hits"]["hits"]

    def process_long_input(self, long_text, index_name="legal_kg_chunks", top_k=1):
        chunks = self.split_by_punctuation(long_text)
        results = []
        case_counter = Counter()
        label_counter = Counter()
        for i, chunk in enumerate(chunks):
            hits = self.search_single_chunk(chunk, index_name=index_name, top_k=top_k)
            if hits:
                top = hits[0]
                cid = top["_source"].get("case_id")
                label = top["_source"].get("label")
                score_raw = top["_score"]
                score_normalized = min(max(round((score_raw / 2.0) * 100), 0), 100)  # Normalize to 0~100
                case_counter[cid] += 1
                label_counter[label] += 1
                results.append({
                    "query_chunk": chunk,
                    "matched_chunk": top["_source"].get("semantic_text"),
                    "original_text": top["_source"].get("original_text", ""),
                    "case_id": cid,
                    "label": label,
                    "score": score_raw,
                    "score_100": score_normalized
                })
        return results, case_counter, label_counter

if __name__ == "__main__":
    searcher = ChunkwiseSemanticSearcher()

    long_query = """
    一、事故發生緣由:
    被告於民國105年4月12日13時27分許，駕駛租賃小客車沿新北市某區某路往富國路方向行駛。
    行經福營路342號前時，被告跨越分向限制線欲繞越前方由原告所駕駛併排於路邊臨時停車後適欲起駛之車輛。
    被告為閃避對向來車，因而駕車自後追撞原告駕駛車輛左後車尾。
    當時天候晴朗、日間自然光線、柏油道路乾燥無缺陷或障礙物、視距良好，
    被告理應注意車前狀況及兩車並行之間隔，隨時採取必要之安全措施，但卻疏未注意而發生事故。

    二、原告受傷情形:
    原告因此車禍受有左膝挫傷、半月軟骨受傷等傷害。
    原告於105年5月2日、7日、7月16日、8月13日、8月29日至醫院門診就診，105年8月2日進行核磁共振造影檢查。
    根據醫院開立的診斷證明書，原告需休養1個月。

    三、請求賠償的事實根據:
    醫療費用190元、車輛修復費用181,144元、交通費用4,500元、休養損失33,000元、慰撫金99,000元。
    原告因傷不良於行，修理費用包括工資費用88,774元和零件費92,370元，另需搭乘計程車上下班。
    原告請求被告依民法第184條、第191條之2、第193條及第195條賠償上述損害，總計317,834元。
    """

    results, case_counter, label_counter = searcher.process_long_input(long_query)

    print("\n📚 LLM Prompt 輸入區：\n")
    for res in results:
        print(f"[Q] {res['query_chunk']}")
        print(f"[R] {res['matched_chunk']}\n（出自 Case #{res['case_id']} 的 {res['label']}，語意相似度評分：{res['score_100']} 分）\n")

    print("\n📊 與輸入最相似的 Top 3 案件 ID：")
    for cid, count in case_counter.most_common(3):
        print(f"✔️ Case ID: {cid} 出現次數: {count}")

    print("\n📑 命中主幹統計（Facts / Laws / Compensation / Conclusion）：")
    for label, count in label_counter.most_common():
        print(f"- {label}: {count} 筆")
