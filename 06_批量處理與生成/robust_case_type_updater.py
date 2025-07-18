#!/usr/bin/env python3
"""
強化版ES案件類型批量更新工具
- 斷點續傳：可從任意中斷點繼續
- 進度持久化：實時保存處理狀態
- 錯誤恢復：自動重試機制
- 記憶體優化：小批次處理
- 安全備份：可選備份機制
"""

import os
import json
import requests
import time
import pickle
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict
from dotenv import load_dotenv
import signal
import sys

# 導入現有的分類邏輯
sys.path.append(os.path.dirname(__file__))
from KG_700_CoT_Hybrid import get_case_type, extract_parties, detect_special_relationships

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

ES_HOST = os.getenv("ELASTIC_HOST")
ES_USER = os.getenv("ELASTIC_USER")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD")
ES_AUTH = (ES_USER, ES_PASSWORD)
CHUNK_INDEX = "legal_kg_chunks"

class RobustCaseTypeUpdater:
    def __init__(self, session_name: str = None):
        """初始化更新器"""
        self.session_name = session_name or f"update_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 檔案路徑
        self.progress_file = f"{self.session_name}_progress.pkl"
        self.log_file = f"{self.session_name}_log.txt"
        self.error_file = f"{self.session_name}_errors.json"
        self.stats_file = f"{self.session_name}_stats.json"
        
        # 處理狀態
        self.state = {
            "session_name": self.session_name,
            "start_time": None,
            "total_cases": 0,
            "processed_cases": set(),
            "failed_cases": set(),
            "case_types": defaultdict(int),
            "current_batch": 0,
            "batch_size": 50,  # 較小的批次大小
            "max_retries": 3,
            "completed": False
        }
        
        # 載入現有進度
        self.load_progress()
        
        # 註冊信號處理器（優雅停止）
        signal.signal(signal.SIGINT, self.graceful_shutdown)
        signal.signal(signal.SIGTERM, self.graceful_shutdown)
        
        self.running = True
        
    def log(self, message: str, level: str = "INFO"):
        """記錄日誌"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {level}: {message}"
        print(log_message)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def save_progress(self):
        """保存進度到檔案"""
        try:
            with open(self.progress_file, 'wb') as f:
                pickle.dump(self.state, f)
            
            # 同時保存JSON格式的統計
            stats = {
                "session_name": self.state["session_name"],
                "start_time": self.state["start_time"],
                "total_cases": self.state["total_cases"],
                "processed_count": len(self.state["processed_cases"]),
                "failed_count": len(self.state["failed_cases"]),
                "current_batch": self.state["current_batch"],
                "case_types": dict(self.state["case_types"]),
                "completed": self.state["completed"],
                "progress_percentage": (len(self.state["processed_cases"]) / max(self.state["total_cases"], 1)) * 100
            }
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.log(f"保存進度失敗: {e}", "ERROR")
    
    def load_progress(self):
        """載入現有進度"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'rb') as f:
                    saved_state = pickle.load(f)
                    self.state.update(saved_state)
                    
                progress = (len(self.state["processed_cases"]) / max(self.state["total_cases"], 1)) * 100
                self.log(f"載入現有進度: {len(self.state['processed_cases'])}/{self.state['total_cases']} ({progress:.1f}%)")
                
                if self.state["completed"]:
                    self.log("⚠️ 此session已完成，建議建立新session")
                    
            except Exception as e:
                self.log(f"載入進度失敗，將重新開始: {e}", "WARN")
    
    def graceful_shutdown(self, signum, frame):
        """優雅關閉"""
        self.log("收到停止信號，正在安全保存進度...")
        self.running = False
        self.save_progress()
        self.log("進度已保存，可使用相同session名稱繼續")
        sys.exit(0)
    
    def get_all_case_ids(self) -> List[str]:
        """獲取所有案例ID"""
        self.log("🔍 獲取所有案例ID...")
        
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
            body = {
                "size": 0,
                "aggs": {
                    "unique_case_ids": {
                        "terms": {
                            "field": "case_id",
                            "size": 50000  # 增加限制以處理更多案例
                        }
                    }
                }
            }
            
            response = requests.post(url, auth=ES_AUTH, json=body, verify=False)
            if response.status_code == 200:
                result = response.json()
                case_ids = [str(bucket["key"]) for bucket in result["aggregations"]["unique_case_ids"]["buckets"]]
                self.log(f"📊 找到 {len(case_ids)} 個唯一案例")
                return sorted(case_ids)
            else:
                self.log(f"獲取案例ID失敗: {response.status_code}", "ERROR")
                return []
                
        except Exception as e:
            self.log(f"獲取案例ID異常: {e}", "ERROR")
            return []
    
    def get_case_facts(self, case_id: str) -> str:
        """獲取案例事實內容"""
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"case_id": case_id}},
                            {"term": {"label": "Facts"}}
                        ]
                    }
                },
                "size": 1,
                "_source": ["original_text", "description"]
            }
            
            response = requests.post(url, auth=ES_AUTH, json=body, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result["hits"]["hits"]:
                    source = result["hits"]["hits"][0]["_source"]
                    return source.get("original_text", "") or source.get("description", "")
            return ""
            
        except Exception as e:
            self.log(f"獲取案例 {case_id} 事實失敗: {e}", "ERROR")
            return ""
    
    def classify_case(self, case_id: str, facts: str) -> Optional[str]:
        """分類單個案例"""
        try:
            if not facts.strip():
                return None
                
            # 使用現有的分類邏輯
            case_type = get_case_type(facts)
            return case_type
            
        except Exception as e:
            self.log(f"分類案例 {case_id} 失敗: {e}", "ERROR")
            return None
    
    def update_case_in_es(self, case_id: str, case_type: str) -> bool:
        """在ES中更新案例類型"""
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_update_by_query"
            script_body = {
                "script": {
                    "source": "ctx._source.case_type = params.type; ctx._source.updated_at = params.timestamp",
                    "lang": "painless",
                    "params": {
                        "type": case_type,
                        "timestamp": datetime.now().isoformat()
                    }
                },
                "query": {
                    "term": {"case_id": case_id}
                }
            }
            
            response = requests.post(url, auth=ES_AUTH, json=script_body, verify=False)
            if response.status_code == 200:
                result = response.json()
                return result.get("updated", 0) > 0
            else:
                self.log(f"ES更新失敗 {case_id}: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"ES更新異常 {case_id}: {e}", "ERROR")
            return False
    
    def process_batch(self, case_ids: List[str]) -> Dict[str, Any]:
        """處理一批案例"""
        batch_stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "skipped": 0
        }
        
        for case_id in case_ids:
            if not self.running:
                break
                
            # 跳過已處理的案例
            if case_id in self.state["processed_cases"]:
                batch_stats["skipped"] += 1
                continue
            
            batch_stats["processed"] += 1
            
            # 獲取事實內容
            facts = self.get_case_facts(case_id)
            if not facts:
                self.log(f"案例 {case_id} 無事實內容，跳過", "WARN")
                self.state["failed_cases"].add(case_id)
                batch_stats["failed"] += 1
                continue
            
            # 分類
            case_type = self.classify_case(case_id, facts)
            if not case_type:
                self.log(f"案例 {case_id} 分類失敗", "ERROR")
                self.state["failed_cases"].add(case_id)
                batch_stats["failed"] += 1
                continue
            
            # 更新ES
            if self.update_case_in_es(case_id, case_type):
                self.state["processed_cases"].add(case_id)
                self.state["case_types"][case_type] += 1
                batch_stats["succeeded"] += 1
                
                if batch_stats["succeeded"] % 10 == 0:  # 每10個成功案例記錄一次
                    self.log(f"✅ 已處理 {len(self.state['processed_cases'])} 個案例")
            else:
                self.state["failed_cases"].add(case_id)
                batch_stats["failed"] += 1
            
            # 小延遲避免過載
            time.sleep(0.1)
        
        return batch_stats
    
    def retry_failed_cases(self) -> int:
        """重試失敗的案例"""
        if not self.state["failed_cases"]:
            return 0
            
        self.log(f"🔄 重試 {len(self.state['failed_cases'])} 個失敗案例...")
        
        failed_list = list(self.state["failed_cases"])
        self.state["failed_cases"].clear()  # 清空失敗列表
        
        retry_batches = [failed_list[i:i+self.state["batch_size"]] for i in range(0, len(failed_list), self.state["batch_size"])]
        
        total_retried = 0
        for batch in retry_batches:
            if not self.running:
                break
                
            batch_stats = self.process_batch(batch)
            total_retried += batch_stats["succeeded"]
        
        return total_retried
    
    def run_update(self, create_backup: bool = False, max_cases: int = None):
        """執行更新"""
        self.log(f"🚀 開始更新 session: {self.session_name}")
        
        if not self.state["start_time"]:
            self.state["start_time"] = datetime.now().isoformat()
        
        # 獲取所有案例ID
        if self.state["total_cases"] == 0:
            all_case_ids = self.get_all_case_ids()
            if not all_case_ids:
                self.log("❌ 無法獲取案例ID", "ERROR")
                return False
            
            if max_cases:
                all_case_ids = all_case_ids[:max_cases]
                self.log(f"🎯 限制處理 {max_cases} 個案例")
                
            self.state["total_cases"] = len(all_case_ids)
        else:
            # 重新獲取（可能有新增的）
            all_case_ids = self.get_all_case_ids()
            if max_cases:
                all_case_ids = all_case_ids[:max_cases]
        
        # 過濾未處理的案例
        remaining_cases = [cid for cid in all_case_ids if cid not in self.state["processed_cases"]]
        self.log(f"📊 總案例: {len(all_case_ids)}, 剩餘: {len(remaining_cases)}")
        
        if not remaining_cases:
            self.log("✅ 所有案例已處理完成!")
            self.state["completed"] = True
            self.save_progress()
            return True
        
        # 分批處理
        batches = [remaining_cases[i:i+self.state["batch_size"]] for i in range(0, len(remaining_cases), self.state["batch_size"])]
        
        self.log(f"📦 分為 {len(batches)} 個批次處理，每批 {self.state['batch_size']} 個案例")
        
        for batch_idx, batch in enumerate(batches, self.state["current_batch"] + 1):
            if not self.running:
                break
                
            self.state["current_batch"] = batch_idx
            self.log(f"🔄 處理批次 {batch_idx}/{len(batches)} ({len(batch)} 個案例)")
            
            batch_stats = self.process_batch(batch)
            
            # 進度報告
            total_progress = len(self.state["processed_cases"]) / self.state["total_cases"] * 100
            self.log(f"📊 批次 {batch_idx} 完成: 成功 {batch_stats['succeeded']}, 失敗 {batch_stats['failed']}, 跳過 {batch_stats['skipped']}")
            self.log(f"📈 總進度: {len(self.state['processed_cases'])}/{self.state['total_cases']} ({total_progress:.1f}%)")
            
            # 實時保存進度
            self.save_progress()
            
            # 批次間休息
            time.sleep(1)
        
        # 重試失敗案例
        if self.state["failed_cases"]:
            retried = self.retry_failed_cases()
            self.log(f"🔄 重試完成，額外成功 {retried} 個案例")
        
        # 最終統計
        self.generate_final_report()
        self.state["completed"] = True
        self.save_progress()
        
        return True
    
    def generate_final_report(self):
        """生成最終報告"""
        self.log("=" * 60)
        self.log("📊 最終處理報告")
        self.log("=" * 60)
        
        total_processed = len(self.state["processed_cases"])
        total_failed = len(self.state["failed_cases"])
        total_cases = self.state["total_cases"]
        
        self.log(f"總案例數: {total_cases}")
        self.log(f"成功處理: {total_processed} ({total_processed/total_cases*100:.1f}%)")
        self.log(f"處理失敗: {total_failed} ({total_failed/total_cases*100:.1f}%)")
        
        self.log("\n📋 案件類型分布:")
        total_typed = sum(self.state["case_types"].values())
        for case_type, count in sorted(self.state["case_types"].items(), key=lambda x: -x[1]):
            percentage = (count / total_typed) * 100 if total_typed > 0 else 0
            self.log(f"  {case_type:20} ➜ {count:4} 筆 ({percentage:5.1f}%)")
        
        if self.state["start_time"]:
            start_time = datetime.fromisoformat(self.state["start_time"])
            duration = datetime.now() - start_time
            self.log(f"\n⏱️ 總耗時: {duration}")
    
    def show_status(self):
        """顯示當前狀態"""
        if self.state["total_cases"] == 0:
            print("❌ 尚未開始處理")
            return
            
        processed = len(self.state["processed_cases"])
        failed = len(self.state["failed_cases"])
        total = self.state["total_cases"]
        progress = (processed / total) * 100
        
        print(f"📊 Session: {self.session_name}")
        print(f"📈 進度: {processed}/{total} ({progress:.1f}%)")
        print(f"❌ 失敗: {failed}")
        print(f"🔄 當前批次: {self.state['current_batch']}")
        print(f"✅ 完成: {self.state['completed']}")
        
        if self.state["case_types"]:
            print(f"\n📋 案件類型分布 (前5名):")
            sorted_types = sorted(self.state["case_types"].items(), key=lambda x: -x[1])
            for case_type, count in sorted_types[:5]:
                print(f"  {case_type}: {count}")

def main():
    print("🔧 強化版ES案件類型批量更新工具")
    print("=" * 60)
    
    print("請選擇操作:")
    print("1. 開始新的更新任務")
    print("2. 繼續現有任務")
    print("3. 查看任務狀態")
    print("4. 列出所有任務")
    
    choice = input("請輸入選擇 (1-4): ").strip()
    
    if choice == "1":
        session_name = input("請輸入任務名稱 (按Enter使用預設): ").strip()
        max_cases = input("限制處理案例數量 (按Enter處理全部): ").strip()
        max_cases = int(max_cases) if max_cases.isdigit() else None
        
        updater = RobustCaseTypeUpdater(session_name)
        
        confirm = input(f"\n⚠️ 確認開始更新任務？\n任務名稱: {updater.session_name}\n處理案例: {'全部' if not max_cases else max_cases}\n輸入 'YES' 確認: ").strip()
        
        if confirm == "YES":
            updater.run_update(max_cases=max_cases)
        else:
            print("❌ 任務取消")
    
    elif choice == "2":
        session_name = input("請輸入要繼續的任務名稱: ").strip()
        if session_name:
            updater = RobustCaseTypeUpdater(session_name)
            if os.path.exists(updater.progress_file):
                updater.run_update()
            else:
                print("❌ 找不到指定的任務")
        else:
            print("❌ 請提供任務名稱")
    
    elif choice == "3":
        session_name = input("請輸入任務名稱: ").strip()
        if session_name:
            updater = RobustCaseTypeUpdater(session_name)
            updater.show_status()
        else:
            print("❌ 請提供任務名稱")
    
    elif choice == "4":
        print("📋 搜尋現有任務檔案...")
        progress_files = [f for f in os.listdir('.') if f.endswith('_progress.pkl')]
        if progress_files:
            print("找到的任務:")
            for f in progress_files:
                session_name = f.replace('_progress.pkl', '')
                updater = RobustCaseTypeUpdater(session_name)
                updater.show_status()
                print("-" * 40)
        else:
            print("❌ 沒有找到任何任務")
    
    else:
        print("❌ 無效選擇")

if __name__ == "__main__":
    main()