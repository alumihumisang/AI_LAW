# elasticsearch_utils.py
# 📦 通用型 ElasticsearchManager，支援向量儲存與檢索

from elasticsearch import Elasticsearch
from typing import List, Dict, Any
import os

class ElasticsearchManager:
    def __init__(self, host, username, password, verify_certs=False):
        self.index_name = "legal_knowledge_graph"
        self.client = Elasticsearch(
            host,
            basic_auth=(username, password),
            verify_certs=verify_certs
        )

    def setup_index(self, mapping: Dict[str, Any]) -> None:
        """ 如果 index 不存在則建立 """
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body={"mappings": mapping})
            print(f"✅ 已建立索引: {self.index_name}")
        else:
            print(f"ℹ️ 索引已存在: {self.index_name}")

    def index_document(self, doc: Dict[str, Any]) -> None:
        """ 將文件寫入索引 """
        self.client.index(index=self.index_name, body=doc)

    def search_similar(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """ 基於 embedding 向量進行語義相似檢索 """
        query = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": embedding}
                    }
                }
            }
        }
        response = self.client.search(index=self.index_name, body=query)
        return response["hits"]["hits"]

    def delete_index(self) -> None:
        """ 刪除整個索引（⚠️ 請小心使用） """
        if self.client.indices.exists(index=self.index_name):
            self.client.indices.delete(index=self.index_name)
            print(f"🗑️ 已刪除索引: {self.index_name}")
