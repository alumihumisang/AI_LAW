#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
視覺化 Query 向量檢索結果
展示 query 在向量空間中如何找到前 N 筆最相似的 sentence embeddings
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import requests
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModel
import torch

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

load_dotenv()

# ===== 配置 =====
ES_HOST = os.getenv("ELASTIC_HOST")
ES_USER = os.getenv("ELASTIC_USER")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD")
ES_AUTH = (ES_USER, ES_PASSWORD)
CHUNK_INDEX = "legal_kg_chunks"

BERT_MODEL = "shibing624/text2vec-base-chinese"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===== 載入模型 =====
print("🔄 載入 BERT 模型...")
tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL)
model = AutoModel.from_pretrained(BERT_MODEL, torch_dtype=torch.float16).to(device)
print("✅ 模型載入完成")

def embed_text(text: str) -> np.ndarray:
    """將文字轉換為向量"""
    inputs = tokenizer(text, truncation=True, padding="max_length", max_length=512, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        output = model(**inputs)
    return output.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()

def search_similar_sentences(query_vector: np.ndarray, top_k: int = 3, label: str = "Facts"):
    """從 ES 檢索最相似的 sentence"""
    body = {
        "size": top_k,
        "query": {
            "script_score": {
                "query": {"bool": {"must": [{"match": {"label": label}}]}},
                "script": {
                    "source": "cosineSimilarity(params.qv, 'embedding') + 1.0",
                    "params": {"qv": query_vector.tolist()},
                },
            }
        }
    }

    try:
        url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
        response = requests.post(url, auth=ES_AUTH, json=body, verify=False)
        if response.status_code == 200:
            result = response.json()
            hits = result["hits"]["hits"]
            return hits
        else:
            print(f"❌ ES 查詢失敗: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ ES 查詢異常: {e}")
        return []

def visualize_retrieval(query_text: str, top_k: int = 3, label: str = "Facts",
                        method: str = "tsne", include_background: int = 50):
    """
    視覺化檢索結果

    Args:
        query_text: 查詢文字
        top_k: 檢索前 K 筆
        label: ES 中的 label 類型
        method: 降維方法 ("tsne" 或 "pca")
        include_background: 額外取樣多少筆背景資料點，讓視覺化更有對比
    """
    print(f"🔍 Query: {query_text[:50]}...")

    # 1. 取得 query embedding
    print("📊 計算 query embedding...")
    query_vec = embed_text(query_text)

    # 2. 從 ES 檢索相似句子
    print(f"🔎 從 ES 檢索 top-{top_k} 相似句子...")
    hits = search_similar_sentences(query_vec, top_k=top_k, label=label)

    if not hits:
        print("❌ 未找到相似句子")
        return

    # 3. 取得背景資料點（隨機抽樣其他句子）
    print(f"🎲 隨機抽樣 {include_background} 筆背景資料點...")
    bg_body = {
        "size": include_background,
        "query": {
            "function_score": {
                "query": {"match": {"label": label}},
                "random_score": {}
            }
        }
    }
    bg_response = requests.post(f"{ES_HOST}/{CHUNK_INDEX}/_search",
                                 auth=ES_AUTH, json=bg_body, verify=False)
    bg_hits = bg_response.json()["hits"]["hits"] if bg_response.status_code == 200 else []

    # 4. 組織資料
    all_embeddings = [query_vec]
    all_labels = ["🎯 Query"]
    all_colors = ['red']
    all_sizes = [300]

    # Top-K 相似句子
    for i, hit in enumerate(hits):
        embedding = np.array(hit["_source"]["embedding"])
        text = hit["_source"]["semantic_text"]
        score = hit["_score"]
        case_id = hit["_source"]["case_id"]

        all_embeddings.append(embedding)
        all_labels.append(f"Top-{i+1} (案例{case_id}, 分數:{score:.2f})\n{text[:30]}...")
        all_colors.append('lime')
        all_sizes.append(200)

    # 背景資料點
    for hit in bg_hits:
        embedding = np.array(hit["_source"]["embedding"])
        all_embeddings.append(embedding)
        all_labels.append("")  # 背景點不標註
        all_colors.append('lightgray')
        all_sizes.append(30)

    # 5. 降維
    embeddings_matrix = np.vstack(all_embeddings)
    print(f"📐 降維中... (使用 {method.upper()})")

    if method == "tsne":
        reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(all_embeddings)-1))
    else:  # pca
        reducer = PCA(n_components=2, random_state=42)

    coords_2d = reducer.fit_transform(embeddings_matrix)

    # 6. 繪圖
    fig, ax = plt.subplots(figsize=(16, 12))

    # 畫背景點
    bg_start = 1 + top_k
    ax.scatter(coords_2d[bg_start:, 0], coords_2d[bg_start:, 1],
               c='lightgray', s=30, alpha=0.3, label='其他案例句子 (背景)')

    # 畫 Query 點
    ax.scatter(coords_2d[0, 0], coords_2d[0, 1],
               c='red', s=300, marker='*', edgecolors='black', linewidths=2,
               label='Query', zorder=10)

    # 畫 Top-K 相似句子
    for i in range(1, top_k + 1):
        ax.scatter(coords_2d[i, 0], coords_2d[i, 1],
                   c='lime', s=200, marker='o', edgecolors='darkgreen', linewidths=2,
                   label=f'Top-{i}' if i == 1 else "", zorder=9)

        # 畫箭頭連線
        ax.annotate('', xy=(coords_2d[i, 0], coords_2d[i, 1]),
                    xytext=(coords_2d[0, 0], coords_2d[0, 1]),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color='orange', alpha=0.6))

    # 標註文字 (只標註 Query 和 Top-K)
    for i in range(top_k + 1):
        ax.annotate(all_labels[i],
                    xy=(coords_2d[i, 0], coords_2d[i, 1]),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=9, bbox=dict(boxstyle='round,pad=0.5',
                                         facecolor='yellow' if i == 0 else 'lightgreen',
                                         alpha=0.7),
                    ha='left')

    ax.set_xlabel(f'{method.upper()} 維度 1', fontsize=12)
    ax.set_ylabel(f'{method.upper()} 維度 2', fontsize=12)
    ax.set_title(f'向量檢索視覺化 - Query 與 Top-{top_k} 相似句子\n'
                 f'降維方法: {method.upper()} | 背景資料點: {include_background} 筆',
                 fontsize=14, pad=20)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # 儲存圖片
    output_path = f"vector_retrieval_visualization_{method}.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 圖表已儲存至: {output_path}")

    plt.show()

    # 7. 列印檢索結果詳情
    print("\n" + "="*80)
    print("📋 檢索結果詳情:")
    print("="*80)
    for i, hit in enumerate(hits):
        print(f"\n【Top-{i+1}】")
        print(f"案例 ID: {hit['_source']['case_id']}")
        print(f"相似度分數: {hit['_score']:.4f}")
        print(f"段落類型: {hit['_source']['label']}")
        print(f"內容: {hit['_source']['semantic_text'][:100]}...")
        print("-" * 80)

def compare_reduction_methods(query_text: str, top_k: int = 3):
    """比較 t-SNE 和 PCA 兩種降維方法"""
    print("🔬 比較 t-SNE 和 PCA 兩種降維方法...")
    print("\n1️⃣ 使用 t-SNE:")
    visualize_retrieval(query_text, top_k=top_k, method="tsne")

    print("\n2️⃣ 使用 PCA:")
    visualize_retrieval(query_text, top_k=top_k, method="pca")

if __name__ == "__main__":
    # 範例 Query（可以替換成你的案例）
    example_query = """
    被告於民國110年8月18日晚間9時26分許，騎乘重型機車行經新北市板橋區長江路1段往北向民生路方向，
    當時天候晴朗、視線良好、路面平坦乾燥且設有路燈照明，被告本應依規定於欲左轉時先行打方向燈、
    暫停並注意來往車輛，竟疏未為之，逕自行駛至路旁欲左轉，適原告騎乘機車自被告後方同向直行而至，
    因閃避不及，遂與被告所駕駛機車發生碰撞。原告因而人車倒地，造成原告受有左膝挫傷併十字韌帶撕裂性骨折及左肩挫擦傷。
    """

    print("="*80)
    print("🎨 向量檢索視覺化工具")
    print("="*80)

    # 選項1: 單一方法視覺化
    visualize_retrieval(
        query_text=example_query,
        top_k=5,  # 檢索前5筆
        label="Facts",  # 只檢索 Facts 類型
        method="tsne",  # 使用 t-SNE 降維
        include_background=100  # 包含100筆背景資料點
    )

    # 選項2: 比較兩種降維方法
    # compare_reduction_methods(example_query, top_k=3)
