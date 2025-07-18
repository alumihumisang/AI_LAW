# ✅ 新版：段落分段向量化並存入 Elasticsearch（支援標點細切 chunk）
# 支援從 semantic_summaries.jsonl 中讀入，每段為一筆 ES 文件，並記錄句長

import os
import json
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
from elasticsearch import Elasticsearch
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np

load_dotenv()

BERT_MODEL = "shibing624/text2vec-base-chinese"

torch_dtype = torch.float16
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class RAGChunkIndexer:
    def __init__(self):
        self.logger = self.setup_logging()
        self.logger.info("初始化 Elasticsearch...")
        self.es_client = Elasticsearch(
            os.getenv("ELASTIC_HOST"),
            basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
            verify_certs=False
        )
        self.index_name = "legal_kg_chunks"
        self.setup_index()

        self.logger.info("載入 BERT 模型...")
        self.tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL)
        self.model = AutoModel.from_pretrained(BERT_MODEL, torch_dtype=torch_dtype).to(device)

    def setup_logging(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"index_chunks_log_{timestamp}.txt"
        logger = logging.getLogger("chunk_indexer")
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(log_filename, encoding="utf-8")
        ch = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger

    def setup_index(self):
        if not self.es_client.indices.exists(index=self.index_name):
            self.es_client.indices.create(index=self.index_name, body={
                "mappings": {
                    "properties": {
                        "case_id": {"type": "integer"},
                        "label": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "semantic_text": {"type": "text"},
                        "original_text": {"type": "text"},
                        "sentence_length": {"type": "integer"},
                        "embedding": {"type": "dense_vector", "dims": 768}
                    }
                }
            })
            self.logger.info(f"✅ 已建立索引：{self.index_name}")

    def embed(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", padding="max_length", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            output = self.model(**inputs)
        return output.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()

    def split_by_punctuation(self, text):
        import re
        return [s.strip() for s in re.split(r'[。！？；]', text) if s.strip()]

    def index_from_jsonl(self, filepath="semantic_summaries.jsonl"):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in tqdm(f):
                obj = json.loads(line)
                case_id = obj["case_id"]
                for segment in obj.get("segments", []):
                    label = segment["section"]
                    for i, chunk in enumerate(segment["content"]):
                        sentences = self.split_by_punctuation(chunk)
                        for j, sent in enumerate(sentences):
                            chunk_id = f"{case_id}_{label}_{i+1:03d}_{j+1:02d}"
                            sentence_length = len(sent)
                            emb = self.embed(sent)
                            doc = {
                                "case_id": case_id,
                                "label": label,
                                "chunk_id": chunk_id,
                                "semantic_text": sent,
                                "original_text": chunk,
                                "sentence_length": sentence_length,
                                "embedding": emb.tolist()
                            }
                            self.es_client.index(index=self.index_name, body=doc)
        self.logger.info("✅ 所有分段語意文本已完成向量化與上傳")

if __name__ == "__main__":
    indexer = RAGChunkIndexer()
    indexer.index_from_jsonl("semantic_summaries.jsonl")
