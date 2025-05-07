# ✅ KG_6.5_Vectorize_Paragraph_Summaries.py：段落級語意摘要向量化上傳 ES（含 tqdm 進度條）

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

class ParagraphIndexer:
    def __init__(self):
        self.logger = self.setup_logger()
        self.es = Elasticsearch(
            os.getenv("ELASTIC_HOST"),
            basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
            verify_certs=False
        )
        self.index_name = "legal_kg_paragraphs"
        self.setup_index()

        self.tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL)
        self.model = AutoModel.from_pretrained(BERT_MODEL, torch_dtype=torch_dtype).to(device)

    def setup_logger(self):
        logger = logging.getLogger("para_indexer")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def setup_index(self):
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body={
                "mappings": {
                    "properties": {
                        "case_id": {"type": "integer"},
                        "label": {"type": "keyword"},
                        "paragraph_id": {"type": "keyword"},
                        "semantic_text": {"type": "text"},
                        "embedding": {"type": "dense_vector", "dims": 768}
                    }
                }
            })
            self.logger.info(f"✅ 已建立索引：{self.index_name}")

    def embed(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", padding="max_length", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()

    def index_paragraphs(self, filepath="semantic_summaries.jsonl"):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in tqdm(f, desc="🧠 上傳段落摘要中"):
                obj = json.loads(line)
                case_id = obj["case_id"]
                for segment in obj.get("segments", []):
                    label = segment["section"]
                    for i, paragraph in enumerate(segment["content"]):
                        paragraph_id = f"{case_id}_{label}_{i+1:03d}"
                        emb = self.embed(paragraph)
                        doc = {
                            "case_id": case_id,
                            "label": label,
                            "paragraph_id": paragraph_id,
                            "semantic_text": paragraph,
                            "embedding": emb.tolist()
                        }
                        self.es.index(index=self.index_name, body=doc)
        self.logger.info("✅ 所有段落已完成向量化與上傳")

if __name__ == "__main__":
    indexer = ParagraphIndexer()
    indexer.index_paragraphs("semantic_summaries.jsonl")
