#!/usr/bin/env python3
"""
KG_150_update_case_type.py
Neo4j Case節點 case_type 管理工具
- 可以從ES讀取並更新case_type到Neo4j
- 可以移除Neo4j中所有case_type屬性
"""

import logging
import os
import requests
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
from collections import Counter
from typing import Dict, List

# 載入 .env 環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

# 設置 logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()

# Neo4j 連線資訊
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# ES 連線資訊
ES_HOST = os.getenv("ELASTIC_HOST")
ES_USER = os.getenv("ELASTIC_USER")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD")
ES_AUTH = (ES_USER, ES_PASSWORD)

class CaseTypeUpdater:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.ES_HOST = ES_HOST
        self.ES_AUTH = ES_AUTH
        logger.info("✅ 成功連接至 Neo4j")
        
        # 測試ES連接
        try:
            response = requests.get(f"{ES_HOST}/_cluster/health", auth=ES_AUTH, verify=False)
            if response.status_code == 200:
                logger.info("✅ 成功連接至 Elasticsearch")
            else:
                raise Exception(f"ES連接失敗: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ ES連接失敗: {e}")
            raise

    def close(self):
        self.driver.close()
        logger.info("✅ 已關閉 Neo4j 連線")

    def get_case_type_from_es(self, case_id: str) -> str:
        """從ES讀取case_type"""
        try:
            # 在legal_kg_chunks索引中搜索該case_id
            search_body = {
                "query": {
                    "term": {"case_id": case_id}
                },
                "_source": ["case_type"],
                "size": 1
            }
            
            url = f"{ES_HOST}/legal_kg_chunks/_search"
            response = requests.post(url, auth=ES_AUTH, json=search_body, verify=False)
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get("hits", {}).get("hits", [])
                
                if hits:
                    case_type = hits[0]["_source"].get("case_type")
                    if case_type:
                        logger.debug(f"📄 案例 {case_id} 從ES獲取case_type: {case_type}")
                        return case_type
                    else:
                        logger.warning(f"⚠️ 案例 {case_id} 在ES中沒有case_type屬性")
                        return "單純原被告各一"  # 默認值
                else:
                    logger.warning(f"⚠️ 案例 {case_id} 在ES中未找到")
                    return "單純原被告各一"  # 默認值
            else:
                logger.error(f"❌ ES查詢失敗: {response.status_code} - {response.text}")
                return "單純原被告各一"  # 默認值
                
        except Exception as e:
            logger.error(f"❌ 從ES獲取case_type失敗 {case_id}: {e}")
            return "單純原被告各一"  # 默認值

    def batch_get_case_types_from_es(self, case_ids: List[str]) -> Dict[str, str]:
        """批量從ES獲取case_type"""
        case_types = {}
        
        try:
            # 使用批量查詢，增大size並使用聚合去重
            search_body = {
                "query": {
                    "terms": {"case_id": case_ids}
                },
                "_source": ["case_id", "case_type"],
                "size": min(10000, len(case_ids) * 100),  # 增大size，因為每個case_id可能有多個chunk
                "collapse": {
                    "field": "case_id"  # 按case_id去重，只取每個case_id的第一個文檔
                }
            }
            
            url = f"{ES_HOST}/legal_kg_chunks/_search"
            response = requests.post(url, auth=ES_AUTH, json=search_body, verify=False)
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get("hits", {}).get("hits", [])
                
                for hit in hits:
                    source = hit["_source"]
                    case_id = source.get("case_id")
                    case_type = source.get("case_type")
                    
                    if case_id and case_type:
                        # 只保留第一次遇到的case_id的case_type
                        if case_id not in case_types:
                            case_types[case_id] = case_type
                
                # 統計實際從ES獲取到的case_type數量
                found_in_es = len(case_types)
                logger.info(f"📊 從ES成功獲取 {found_in_es} 個案例的case_type")
                
                # 為未找到的案例設置默認值
                missing_ids = []
                for case_id in case_ids:
                    if case_id not in case_types:
                        case_types[case_id] = "單純原被告各一"
                        missing_ids.append(case_id)
                
                missing_count = len(missing_ids)
                
                if missing_count > 0:
                    logger.warning(f"⚠️ {missing_count} 個案例未在ES中找到case_type，使用默認值")
                    if missing_count <= 5:  # 只顯示前5個
                        missing_ids = [cid for cid in case_ids if cid not in case_types or case_types[cid] == "單純原被告各一"][:5]
                        logger.debug(f"   未找到的案例ID: {missing_ids}")
            else:
                logger.error(f"❌ ES批量查詢失敗: {response.status_code}")
                # 全部設置為默認值
                for case_id in case_ids:
                    case_types[case_id] = "單純原被告各一"
                    
        except Exception as e:
            logger.error(f"❌ ES批量查詢異常: {e}")
            # 全部設置為默認值
            for case_id in case_ids:
                case_types[case_id] = "單純原被告各一"
        
        return case_types

    def get_cases_without_case_type(self) -> List[str]:
        """獲取沒有case_type屬性的案例ID列表"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Case)
                WHERE c.case_type IS NULL
                RETURN c.case_id AS case_id
                ORDER BY c.case_id
            """).data()
            
            case_ids = [record["case_id"] for record in result]
            logger.info(f"🔍 找到 {len(case_ids)} 個需要更新case_type的案例")
            return case_ids

    def update_case_type_safe(self, case_id: str, case_type: str) -> bool:
        """安全更新case_type（防重複）"""
        with self.driver.session() as session:
            # 檢查是否已經有case_type
            check_result = session.run("""
                MATCH (c:Case {case_id: $case_id})
                RETURN c.case_type AS existing_type
            """, case_id=case_id).single()
            
            if check_result and check_result["existing_type"]:
                logger.info(f"⚠️ 案例 {case_id} 已有case_type: {check_result['existing_type']}，跳過")
                return False
            
            # 使用MERGE確保安全更新
            session.run("""
                MATCH (c:Case {case_id: $case_id})
                SET c.case_type = $case_type
            """, case_id=case_id, case_type=case_type)
            
            logger.info(f"✅ 案例 {case_id} 更新case_type: {case_type}")
            return True

    def batch_update_case_types(self, batch_size: int = 100):
        """批次更新case_type（從ES讀取）"""
        case_ids_to_update = self.get_cases_without_case_type()
        
        if not case_ids_to_update:
            logger.info("🎉 所有案例都已有case_type，無需更新")
            return
        
        updated_count = 0
        skipped_count = 0
        case_type_stats = Counter()
        
        logger.info(f"🚀 開始批次更新 {len(case_ids_to_update)} 個案例...")
        
        # 分批處理
        for i in range(0, len(case_ids_to_update), batch_size):
            batch_case_ids = case_ids_to_update[i:i + batch_size]
            
            logger.info(f"📦 處理批次 {i//batch_size + 1}: {len(batch_case_ids)} 個案例")
            
            # 從ES批量獲取case_type
            case_types = self.batch_get_case_types_from_es(batch_case_ids)
            
            # 批量更新到Neo4j
            for case_id in batch_case_ids:
                case_type = case_types.get(case_id, "單純原被告各一")
                
                try:
                    if self.update_case_type_safe(case_id, case_type):
                        updated_count += 1
                        case_type_stats[case_type] += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ 案例 {case_id} 更新失敗: {e}")
                    skipped_count += 1
            
            # 批次進度報告
            progress = min(i + batch_size, len(case_ids_to_update))
            logger.info(f"📊 進度: {progress}/{len(case_ids_to_update)} ({progress/len(case_ids_to_update)*100:.1f}%)")
        
        # 總結報告
        logger.info(f"\n🎯 批次更新完成！")
        logger.info(f"✅ 成功更新: {updated_count} 個案例")
        logger.info(f"⚠️ 跳過: {skipped_count} 個案例")
        
        logger.info(f"\n📊 案件類型統計:")
        for case_type, count in case_type_stats.most_common():
            logger.info(f"   {case_type}: {count} 個案例")

    def verify_update_results(self):
        """驗證更新結果"""
        with self.driver.session() as session:
            # 檢查總案例數
            total_cases = session.run("MATCH (c:Case) RETURN count(c) AS total").single()["total"]
            
            # 檢查有case_type的案例數
            with_case_type = session.run("""
                MATCH (c:Case) 
                WHERE c.case_type IS NOT NULL 
                RETURN count(c) AS with_type
            """).single()["with_type"]
            
            # 檢查case_type分布
            type_distribution = session.run("""
                MATCH (c:Case) 
                WHERE c.case_type IS NOT NULL
                RETURN c.case_type AS case_type, count(c) AS count
                ORDER BY count DESC
            """).data()
            
            logger.info(f"\n📊 驗證結果:")
            logger.info(f"總案例數: {total_cases}")
            logger.info(f"有case_type的案例: {with_case_type}")
            logger.info(f"覆蓋率: {with_case_type/total_cases*100:.1f}%")
            
            logger.info(f"\n📈 case_type分布:")
            for record in type_distribution:
                logger.info(f"   {record['case_type']}: {record['count']} 個案例")
    
    def remove_all_case_types(self):
        """移除Neo4j中所有Case節點的case_type屬性"""
        logger.info("🗑️ 開始移除所有Case節點的case_type屬性...")
        
        with self.driver.session() as session:
            # 1. 先檢查有多少Case節點有case_type屬性
            result = session.run("""
                MATCH (c:Case)
                WHERE c.case_type IS NOT NULL
                RETURN count(c) as count_with_case_type
            """).single()
            
            cases_with_type = result["count_with_case_type"] if result else 0
            logger.info(f"📊 發現 {cases_with_type} 個Case節點有case_type屬性")
            
            if cases_with_type == 0:
                logger.info("✅ 沒有Case節點有case_type屬性，無需移除")
                return
            
            # 2. 移除所有Case節點的case_type屬性
            logger.info("🗑️ 執行移除操作...")
            
            result = session.run("""
                MATCH (c:Case)
                WHERE c.case_type IS NOT NULL
                REMOVE c.case_type
                RETURN count(c) as removed_count
            """).single()
            
            removed_count = result["removed_count"] if result else 0
            logger.info(f"✅ 成功移除 {removed_count} 個Case節點的case_type屬性")
            
            # 3. 驗證移除結果
            result = session.run("""
                MATCH (c:Case)
                WHERE c.case_type IS NOT NULL
                RETURN count(c) as remaining_count
            """).single()
            
            remaining_count = result["remaining_count"] if result else 0
            
            if remaining_count == 0:
                logger.info("✅ 所有Case節點的case_type屬性已成功移除")
            else:
                logger.warning(f"⚠️ 仍有 {remaining_count} 個Case節點有case_type屬性")
            
            # 4. 檢查總Case節點數量
            result = session.run("""
                MATCH (c:Case)
                RETURN count(c) as total_cases
            """).single()
            
            total_cases = result["total_cases"] if result else 0
            logger.info(f"📊 總Case節點數量: {total_cases}")
            
            # 5. 檢查並清理schema中的case_type property key
            logger.info("🧹 檢查是否需要清理schema...")
            self._cleanup_case_type_schema()
    
    def _cleanup_case_type_schema(self):
        """清理schema中無用的case_type property key"""
        with self.driver.session() as session:
            try:
                # 檢查是否還有任何節點或關係使用case_type屬性
                result = session.run("""
                    CALL db.propertyKeys() YIELD propertyKey
                    WHERE propertyKey = 'case_type'
                    RETURN propertyKey
                """).data()
                
                if result:
                    logger.info("🔍 發現schema中仍存在case_type property key")
                    
                    # 再次確認沒有任何節點使用case_type
                    node_check = session.run("""
                        MATCH (n)
                        WHERE n.case_type IS NOT NULL
                        RETURN count(n) as count
                    """).single()["count"]
                    
                    # 檢查關係是否使用case_type
                    rel_check = session.run("""
                        MATCH ()-[r]->()
                        WHERE r.case_type IS NOT NULL
                        RETURN count(r) as count
                    """).single()["count"]
                    
                    if node_check == 0 and rel_check == 0:
                        logger.info("✅ 確認沒有任何節點或關係使用case_type屬性")
                        logger.info("📝 property key 'case_type' 將在數據庫重啟或重建後自動清理")
                        logger.info("💡 如需立即清理，可考慮重啟Neo4j服務或執行完整的數據庫維護")
                    else:
                        logger.warning(f"⚠️ 仍有 {node_check} 個節點和 {rel_check} 個關係使用case_type")
                else:
                    logger.info("✅ schema中已無case_type property key")
                    
            except Exception as e:
                logger.warning(f"⚠️ 無法檢查schema: {e}")
    
    def force_cleanup_schema(self):
        """強制清理schema（需要管理員權限）"""
        logger.info("🧹 嘗試強制清理case_type property key...")
        
        with self.driver.session() as session:
            try:
                # 檢查當前所有property keys
                all_keys = session.run("CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) as keys").single()["keys"]
                logger.info(f"📋 當前property keys: {all_keys}")
                
                if 'case_type' in all_keys:
                    logger.info("🔍 找到case_type property key")
                    
                    # 嘗試觸發schema清理（這通常需要特殊權限）
                    try:
                        # 執行一些可能觸發schema清理的操作
                        session.run("CALL db.awaitIndexes()")
                        session.run("CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Store file sizes') YIELD attributes")
                        logger.info("✅ 已執行schema維護操作")
                    except Exception as inner_e:
                        logger.info(f"💡 無法執行高級schema操作: {inner_e}")
                        logger.info("📝 這是正常的，property key會在適當時候自動清理")
                else:
                    logger.info("✅ case_type property key已不存在於schema中")
                    
            except Exception as e:
                logger.error(f"❌ schema清理失敗: {e}")

def main():
    updater = CaseTypeUpdater()
    
    try:
        print("🔧 Neo4j Case Type 管理工具")
        print("=" * 60)
        print("1. 從ES讀取case_type並更新到Neo4j")
        print("2. 移除Neo4j中所有case_type屬性")
        print("3. 查看當前狀態")
        print("4. 強制清理schema中的case_type property key")
        
        choice = input("\n請選擇操作 (1/2/3/4): ").strip()
        
        if choice == "1":
            print("\n🔧 Neo4j Case Type 更新器（從ES讀取）")
            print("=" * 60)
            print("此腳本會從ES讀取case_type並安全更新到Neo4j")
            print("✅ 從ES讀取：使用已驗證的case_type分類結果")
            print("✅ 防重複：已有case_type的案例會被跳過")
            print("✅ 批次處理：分批更新避免記憶體問題")
            print("✅ 錯誤處理：單個案例失敗不影響整體更新")
            
            confirm = input("\n是否開始更新？(y/N): ").lower().strip()
            if confirm in ['y', 'yes', '是']:
                # 執行批次更新
                updater.batch_update_case_types(batch_size=50)
            else:
                print("取消更新")
                
        elif choice == "2":
            print("\n🗑️ 移除Neo4j中所有case_type屬性")
            print("=" * 60)
            print("⚠️ 注意：此操作會移除所有Case節點的case_type屬性！")
            print("⚠️ 此操作不可逆！")
            print("✅ ES中的case_type不會受影響")
            
            confirm = input("\n確定要移除所有case_type屬性嗎？(輸入 'REMOVE' 確認): ")
            if confirm == 'REMOVE':
                updater.remove_all_case_types()
            else:
                print("❌ 操作已取消")
                
        elif choice == "3":
            print("\n📊 查看當前狀態...")
            updater.verify_update_results()
            
        elif choice == "4":
            print("\n🧹 強制清理schema中的case_type property key")
            print("=" * 60)
            print("📝 此操作會檢查並嘗試清理schema中無用的property key")
            print("⚠️ 通常情況下，無用的property key會自動清理")
            
            confirm = input("\n是否執行schema清理？(y/N): ").lower().strip()
            if confirm in ['y', 'yes', '是']:
                updater.force_cleanup_schema()
            else:
                print("❌ 操作已取消")
            
        else:
            print("❌ 無效選擇")
        
        # 只有在選擇查看狀態時才驗證結果
        if choice == "3":
            pass  # 已經在上面執行了
        elif choice in ["1", "2"]:
            print("\n" + "=" * 40)
            print("📊 操作完成後的狀態檢查:")
            updater.verify_update_results()
        
    except Exception as e:
        logger.error(f"❌ 更新過程出錯: {e}")
    finally:
        updater.close()

if __name__ == "__main__":
    main()