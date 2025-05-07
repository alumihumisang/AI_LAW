import os
import torch
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from transformers import AutoTokenizer, AutoModel

# 載入環境變數
load_dotenv()

# 模型設定
BERT_MODEL = "shibing624/text2vec-base-chinese"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL)
model = AutoModel.from_pretrained(
    BERT_MODEL,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
).to(device)

# Elasticsearch 初始化
ES = Elasticsearch(
    os.getenv("ELASTIC_HOST"),
    basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
    verify_certs=False
)

INDEX_NAME = "legal_kg_chunks"

# 文字向量化
def embed(text: str):
    tokens = tokenizer(text, truncation=True, padding="max_length", max_length=512, return_tensors="pt")
    tokens = {k: v.to(device) for k, v in tokens.items()}
    with torch.no_grad():
        vec = model(**tokens).last_hidden_state.mean(dim=1).squeeze()
    return vec.cpu().numpy().tolist()

# 查詢 ES 並印出 semantic_text / original_text
def search_and_print(query_text: str, top_k: int = 5):
    query_vector = embed(query_text)
    body = {
        "size": top_k,
        "query": {
            "script_score": {
                "query": {"match": {"label": "Facts"}},
                "script": {
                    "source": "cosineSimilarity(params.qv,'embedding')+1.0",
                    "params": {"qv": query_vector},
                },
            }
        }
    }
    results = ES.search(index=INDEX_NAME, body=body)["hits"]["hits"]
    print(f"\n🔍 搜尋結果 Top {top_k} 筆：\n")
    for idx, hit in enumerate(results, 1):
        source = hit["_source"]
        cid = source.get("case_id")
        sid = source.get("semantic_id", hit["_id"])
        print(f"{idx}. Case ID: {cid}, Chunk ID: {sid}, 分數: {hit['_score']:.4f}")
        print(f"🔹 semantic_text: {source.get('semantic_text', '')[:100]}...")
        print(f"🔸 original_text: {source.get('original_text', '')[:100]}...")
        print("-" * 60)

# 主流程（支援逐行輸入）
if __name__ == "__main__":
    print("請輸入要查詢的律師輸入語句（逐行輸入，輸入 'q' 結束）：")

    buf = []
    while True:
        line = input()
        if line.strip().lower() in {"q", "quit"}:
            break
        buf.append(line)

    query = "\n".join(buf).strip()
    if query:
        search_and_print(query, top_k=5)
    else:
        print("⚠️ 未輸入任何查詢語句")

