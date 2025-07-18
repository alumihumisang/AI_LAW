import logging
import sys
import os
import time
from datetime import datetime
import pandas as pd
import torch
from dotenv import load_dotenv
from tqdm import tqdm
from elasticsearch import Elasticsearch
from transformers import AutoTokenizer, AutoModel

# 載入 `.env` 環境變數
load_dotenv()

# 設定 FP16 模式
torch_dtype = torch.float16
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 設定 BigBird & Longformer
BIGBIRD_MODEL = "google/bigbird-roberta-base"
LONGFORMER_MODEL = "allenai/longformer-base-4096"

class LegalEmbeddingSystem:
    def __init__(self):
        """ 初始化 RAG 系統，包含模型與 Elasticsearch """
        self.logger = self.setup_logging()
        
        # 初始化 BigBird 與 Longformer
        self.logger.info("載入 BigBird 與 Longformer 模型...")
        self.bigbird_tokenizer = AutoTokenizer.from_pretrained(BIGBIRD_MODEL, use_fast=False)
        self.bigbird_model = AutoModel.from_pretrained(BIGBIRD_MODEL, torch_dtype=torch_dtype).to(device)

        self.longformer_tokenizer = AutoTokenizer.from_pretrained(LONGFORMER_MODEL, use_fast=False)
        self.longformer_model = AutoModel.from_pretrained(LONGFORMER_MODEL, torch_dtype=torch_dtype).to(device)

        # 初始化 Elasticsearch 連線
        self.logger.info("連線至 Elasticsearch...")
        self.es_manager = Elasticsearch(
            os.getenv("ELASTIC_HOST"),
            basic_auth=(os.getenv("ELASTIC_USER"), os.getenv("ELASTIC_PASSWORD")),
            verify_certs=False  # 如果使用自簽憑證，請設為 False
        )

        self.index_name = "legal_cases"
        self.setup_elasticsearch_index()

    def setup_logging(self):
        """ 設置 logging 紀錄日誌 """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"embedding_log_{timestamp}.txt"

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def get_embedding(self, text, use_longformer=False):
        """ 使用 BigBird 或 Longformer 進行 FP16 向量化 """
        tokenizer, model, max_len = (
            (self.longformer_tokenizer, self.longformer_model, 4096)
            if use_longformer else
            (self.bigbird_tokenizer, self.bigbird_model, 4096)
        )

        inputs = tokenizer(text, return_tensors="pt", padding="max_length", truncation=True, max_length=max_len)
        inputs = {key: val.to(device) for key, val in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
        
        return outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()  # 平均池化

    def setup_elasticsearch_index(self):
        """ 建立 Elasticsearch 索引（如果不存在） """
        if not self.es_manager.indices.exists(index=self.index_name):
            self.es_manager.indices.create(index=self.index_name, body={
                "mappings": {
                    "properties": {
                        "case_id": {"type": "integer"},
                        "模擬律師輸入": {"type": "text"},
                        "緣由": {"type": "text"},
                        "後果": {"type": "text"},
                        "模擬律師輸入_向量": {"type": "dense_vector", "dims": 768},
                        "緣由_向量": {"type": "dense_vector", "dims": 768},
                        "後果_向量": {"type": "dense_vector", "dims": 768},
                    }
                }
            })
            self.logger.info(f"✅ 已建立 Elasticsearch 索引: {self.index_name}")

    def process_and_store_embeddings(self, file_path):
        """ 讀取 Excel，向量化文本，並存入 Elasticsearch """
        self.logger.info(f"讀取 Excel 檔案: {file_path}")
        df = pd.read_excel(file_path, engine="openpyxl")

        self.logger.info("開始向量化案件數據...")
        df["模擬律師輸入_向量"] = df["模擬律師輸入"].apply(lambda x: self.get_embedding(str(x)))
        df["後果_向量"] = df["後果"].apply(lambda x: self.get_embedding(str(x)))

        df["緣由_向量"] = df["緣由"].apply(lambda x: self.get_embedding(str(x), use_longformer=(len(str(x)) < 4096)))

        self.logger.info("向量化完成，開始寫入 Elasticsearch...")

        for _, row in tqdm(df.iterrows(), total=len(df)):
            doc = {
                "case_id": row["case_id"],
                "模擬律師輸入": row["模擬律師輸入"],
                "緣由": row["緣由"],
                "後果": row["後果"],
                "模擬律師輸入_向量": row["模擬律師輸入_向量"].tolist(),
                "緣由_向量": row["緣由_向量"].tolist(),
                "後果_向量": row["後果_向量"].tolist(),
            }
            self.es_manager.index(index=self.index_name, body=doc)

        self.logger.info("✅ 所有案件向量已存入 Elasticsearch！")

    def main(self):
        """ 程式入口 """
        file_path = input("請輸入 Excel 檔案路徑: ").strip()
        self.process_and_store_embeddings(file_path)


if __name__ == "__main__":
    start_time = time.time()

    rag_system = LegalEmbeddingSystem()
    rag_system.main()

    end_time = time.time()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    logger = logging.getLogger()
    logger.info(f"\nTotal execution time: {hours}h {minutes}m {seconds}s")
    print(f"\nTotal execution time: {hours}h {minutes}m {seconds}s")
