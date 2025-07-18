#!/usr/bin/env python3
"""
檢查ES中case_type的分布情況
"""

import os
import requests
from dotenv import load_dotenv

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

ES_HOST = os.getenv("ELASTIC_HOST")
ES_USER = os.getenv("ELASTIC_USER")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD")
ES_AUTH = (ES_USER, ES_PASSWORD)

def check_case_type_distribution():
    """檢查ES中case_type的分布"""
    try:
        # 檢查有case_type的文檔數量
        search_body = {
            "query": {
                "exists": {
                    "field": "case_type"
                }
            },
            "size": 0
        }
        
        url = f"{ES_HOST}/legal_kg_chunks/_search"
        response = requests.post(url, auth=ES_AUTH, json=search_body, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            total_with_case_type = result["hits"]["total"]["value"]
            print(f"📊 ES中有case_type的文檔數: {total_with_case_type}")
        else:
            print(f"❌ 查詢失敗: {response.status_code}")
            return
        
        # 檢查case_type分布
        agg_body = {
            "size": 0,
            "aggs": {
                "case_type_distribution": {
                    "terms": {
                        "field": "case_type.keyword",
                        "size": 20
                    }
                }
            }
        }
        
        response = requests.post(url, auth=ES_AUTH, json=agg_body, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            buckets = result["aggregations"]["case_type_distribution"]["buckets"]
            
            print(f"\n📈 case_type分布:")
            for bucket in buckets:
                print(f"   {bucket['key']}: {bucket['doc_count']} 個文檔")
        
        # 檢查總文檔數
        total_body = {"size": 0}
        response = requests.post(url, auth=ES_AUTH, json=total_body, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            total_docs = result["hits"]["total"]["value"]
            print(f"\n📊 ES總文檔數: {total_docs}")
            if total_with_case_type > 0:
                print(f"📊 case_type覆蓋率: {total_with_case_type/total_docs*100:.1f}%")
        
        # 檢查唯一case_id數量
        case_id_agg_body = {
            "size": 0,
            "aggs": {
                "unique_case_ids": {
                    "cardinality": {
                        "field": "case_id"
                    }
                }
            }
        }
        
        response = requests.post(url, auth=ES_AUTH, json=case_id_agg_body, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            unique_case_ids = result["aggregations"]["unique_case_ids"]["value"]
            print(f"📊 唯一case_id數量: {unique_case_ids}")
            
    except Exception as e:
        print(f"❌ 檢查失敗: {e}")

if __name__ == "__main__":
    print("🔍 檢查ES中case_type分布")
    print("=" * 40)
    check_case_type_distribution()