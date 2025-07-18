#!/usr/bin/env python3
"""
測試case_type更新功能
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from KG_150_update_case_type import CaseTypeUpdater

def test_update():
    updater = CaseTypeUpdater()
    
    try:
        print("🧪 測試ES到Neo4j的case_type更新")
        print("=" * 50)
        
        # 1. 檢查ES中case_type分布
        print("🔍 檢查ES中case_type分布...")
        import requests
        
        # 檢查case_type分布
        agg_body = {
            "size": 0,
            "aggs": {
                "case_type_distribution": {
                    "terms": {
                        "field": "case_type",
                        "size": 20
                    }
                },
                "unique_case_ids": {
                    "cardinality": {
                        "field": "case_id"
                    }
                }
            }
        }
        
        url = f"{updater.ES_HOST}/legal_kg_chunks/_search"
        response = requests.post(url, auth=updater.ES_AUTH, json=agg_body, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            
            # 總case_id數量
            total_case_ids = result["aggregations"]["unique_case_ids"]["value"]
            print(f"📊 ES中唯一case_id總數: {total_case_ids}")
            
            # case_type分布
            buckets = result["aggregations"]["case_type_distribution"]["buckets"]
            print(f"\n📈 case_type分布:")
            for bucket in buckets:
                print(f"   {bucket['key']}: {bucket['doc_count']} 個文檔")
        
        # 檢查前10個不同case_id的文檔
        search_body = {
            "size": 50,  # 增加size以獲取更多不同的case_id
            "_source": ["case_id", "case_type"]
        }
        
        response = requests.post(url, auth=updater.ES_AUTH, json=search_body, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            hits = result["hits"]["hits"]
            
            # 收集不同的case_id和對應的case_type
            unique_cases = {}
            for hit in hits:
                source = hit["_source"]
                case_id = source.get('case_id')
                case_type = source.get('case_type')
                if case_id not in unique_cases:
                    unique_cases[case_id] = case_type
                if len(unique_cases) >= 10:  # 只要前10個不同的
                    break
            
            print(f"\n🔍 前10個不同case_id的case_type:")
            for case_id, case_type in list(unique_cases.items())[:10]:
                print(f"   case_id {case_id}: {case_type}")
        
        # 2. 檢查需要更新的案例數量
        case_ids = updater.get_cases_without_case_type()
        print(f"\n📊 需要更新的案例數: {len(case_ids)}")
        
        if len(case_ids) > 0:
            # 3. 測試從ES獲取前5個案例的case_type
            test_case_ids = case_ids[:5]
            print(f"\n🔍 測試獲取前5個案例的case_type:")
            
            # 逐個查詢調試
            for case_id in test_case_ids:
                case_type = updater.get_case_type_from_es(case_id)
                print(f"   {case_id}: {case_type}")
            
            # 4. 批量查詢測試
            print(f"\n🔍 測試批量查詢:")
            case_types = updater.batch_get_case_types_from_es(test_case_ids)
            for case_id, case_type in case_types.items():
                print(f"   {case_id}: {case_type}")
            
            # 5. 測試更新一個案例
            if test_case_ids:
                test_case_id = test_case_ids[0]
                test_case_type = case_types.get(test_case_id, "單純原被告各一")
                
                print(f"\n🧪 測試更新案例 {test_case_id} 的case_type為 {test_case_type}")
                success = updater.update_case_type_safe(test_case_id, test_case_type)
                print(f"結果: {'✅ 成功' if success else '⚠️ 跳過（已存在）'}")
        
        # 6. 驗證結果
        print(f"\n📊 當前狀態:")
        updater.verify_update_results()
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
    finally:
        updater.close()

if __name__ == "__main__":
    test_update()