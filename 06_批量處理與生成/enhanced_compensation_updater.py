#!/usr/bin/env python3
"""
增強版賠償金額更新器 - 整合金額標準化功能
解決各種金額格式問題，提供準確的賠償金額更新到ES
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

# 導入我們的金額標準化器
from legal_amount_standardizer import LegalAmountStandardizer

# 載入環境變數
env_path = os.path.join(os.path.dirname(__file__), '..', '01_設定與配置', '.env')
load_dotenv(dotenv_path=env_path)

ES_HOST = os.getenv("ELASTIC_HOST")
ES_USER = os.getenv("ELASTIC_USER")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD")
ES_AUTH = (ES_USER, ES_PASSWORD)
CHUNK_INDEX = "legal_kg_chunks"

class EnhancedCompensationUpdater:
    """增強版賠償金額更新器"""
    
    def __init__(self, session_name: str = None):
        self.session_name = session_name or f"compensation_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.standardizer = LegalAmountStandardizer()
        
        # 檔案路徑
        self.progress_file = f"{self.session_name}_progress.pkl"
        self.log_file = f"{self.session_name}_log.txt"
        self.results_file = f"{self.session_name}_results.json"
        
        # 處理狀態
        self.state = {
            "session_name": self.session_name,
            "start_time": None,
            "total_cases": 0,
            "processed_cases": set(),
            "failed_cases": set(),
            "compensation_stats": defaultdict(int),
            "current_batch": 0,
            "batch_size": 20,  # 較小批次避免過載
            "completed": False
        }
        
        # 載入現有進度
        self.load_progress()
        
        # 註冊信號處理器
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
        """保存進度"""
        try:
            with open(self.progress_file, 'wb') as f:
                pickle.dump(self.state, f)
        except Exception as e:
            self.log(f"保存進度失敗: {e}", "ERROR")
    
    def load_progress(self):
        """載入進度"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'rb') as f:
                    self.state.update(pickle.load(f))
                self.log(f"載入現有進度: {len(self.state['processed_cases'])}")
        except Exception as e:
            self.log(f"載入進度失敗，將重新開始: {e}", "WARN")
    
    def graceful_shutdown(self, signum, frame):
        """優雅關閉"""
        self.log("收到停止信號，正在保存進度...")
        self.running = False
        self.save_progress()
        sys.exit(0)
    
    def get_cases_with_compensation(self) -> List[str]:
        """獲取包含賠償金額的案例"""
        self.log("🔍 搜尋包含賠償金額的案例...")
        
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
            body = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"label": "Conclusion"}},
                            {"bool": {
                                "should": [
                                    {"wildcard": {"original_text": "*元*"}},
                                    {"wildcard": {"original_text": "*賠償*"}},
                                    {"wildcard": {"original_text": "*給付*"}},
                                    {"wildcard": {"description": "*元*"}}
                                ]
                            }}
                        ]
                    }
                },
                "aggs": {
                    "unique_case_ids": {
                        "terms": {
                            "field": "case_id",
                            "size": 10000
                        }
                    }
                }
            }
            
            response = requests.post(url, auth=ES_AUTH, json=body, verify=False)
            if response.status_code == 200:
                result = response.json()
                case_ids = [str(bucket["key"]) for bucket in result["aggregations"]["unique_case_ids"]["buckets"]]
                self.log(f"📊 找到 {len(case_ids)} 個包含賠償金額的案例")
                return sorted(case_ids)
            else:
                self.log(f"搜尋案例失敗: {response.status_code}", "ERROR")
                return []
                
        except Exception as e:
            self.log(f"搜尋案例異常: {e}", "ERROR")
            return []
    
    def get_conclusion_text(self, case_id: str) -> str:
        """獲取案例的結論文本"""
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_search"
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"case_id": case_id}},
                            {"term": {"label": "Conclusion"}}
                        ]
                    }
                },
                "size": 10,
                "_source": ["original_text", "description"]
            }
            
            response = requests.post(url, auth=ES_AUTH, json=body, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result["hits"]["hits"]:
                    # 合併所有結論文本
                    texts = []
                    for hit in result["hits"]["hits"]:
                        source = hit["_source"]
                        text = source.get("original_text", "") or source.get("description", "")
                        if text:
                            texts.append(text)
                    return " ".join(texts)
            return ""
            
        except Exception as e:
            self.log(f"獲取案例 {case_id} 結論失敗: {e}", "ERROR")
            return ""
    
    def process_compensation(self, case_id: str, conclusion_text: str) -> Optional[Dict[str, Any]]:
        """處理單個案例的賠償金額"""
        try:
            if not conclusion_text.strip():
                return None
            
            # 使用標準化器分析文本
            result = self.standardizer.standardize_document(conclusion_text)
            
            if not result['amounts']:
                return None
            
            # 準備賠償資訊
            compensation_info = {
                "case_id": case_id,
                "total_amount": result['calculations'].get('main_total', 0),
                "grand_total": result['calculations'].get('grand_total', 0),
                "amount_details": result['amounts'],
                "categorized_amounts": result['categorized_amounts'],
                "standardized_text": result['standardized_text'],
                "confidence_score": sum(amt['confidence'] for amt in result['amounts']) / len(result['amounts']),
                "processed_at": datetime.now().isoformat()
            }
            
            return compensation_info
            
        except Exception as e:
            self.log(f"處理案例 {case_id} 賠償金額失敗: {e}", "ERROR")
            return None
    
    def update_compensation_in_es(self, case_id: str, compensation_info: Dict[str, Any]) -> bool:
        """更新ES中的賠償金額資訊"""
        try:
            url = f"{ES_HOST}/{CHUNK_INDEX}/_update_by_query"
            script_body = {
                "script": {
                    "source": """
                        ctx._source.compensation_amount = params.total_amount;
                        ctx._source.compensation_details = params.details;
                        ctx._source.compensation_updated_at = params.timestamp;
                        if (ctx._source.containsKey('metadata')) {
                            ctx._source.metadata.put('compensation_confidence', params.confidence);
                        } else {
                            ctx._source.metadata = ['compensation_confidence': params.confidence];
                        }
                    """,
                    "lang": "painless",
                    "params": {
                        "total_amount": compensation_info["total_amount"],
                        "details": json.dumps(compensation_info["amount_details"], ensure_ascii=False),
                        "confidence": compensation_info["confidence_score"],
                        "timestamp": compensation_info["processed_at"]
                    }
                },
                "query": {
                    "term": {"case_id": case_id}
                }
            }
            
            response = requests.post(url, auth=ES_AUTH, json=script_body, verify=False)
            if response.status_code == 200:
                result = response.json()
                updated_count = result.get("updated", 0)
                if updated_count > 0:
                    self.log(f"✅ 案例 {case_id} 更新了 {updated_count} 個文檔")
                    return True
                else:
                    self.log(f"⚠️ 案例 {case_id} 沒有文檔被更新", "WARN")
                    return False
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
        
        batch_results = []
        
        for case_id in case_ids:
            if not self.running:
                break
            
            # 跳過已處理的案例
            if case_id in self.state["processed_cases"]:
                batch_stats["skipped"] += 1
                continue
            
            batch_stats["processed"] += 1
            
            # 獲取結論文本
            conclusion_text = self.get_conclusion_text(case_id)
            if not conclusion_text:
                self.log(f"案例 {case_id} 無結論內容，跳過", "WARN")
                self.state["failed_cases"].add(case_id)
                batch_stats["failed"] += 1
                continue
            
            # 處理賠償金額
            compensation_info = self.process_compensation(case_id, conclusion_text)
            if not compensation_info:
                self.log(f"案例 {case_id} 無法提取賠償金額", "WARN")
                self.state["failed_cases"].add(case_id)
                batch_stats["failed"] += 1
                continue
            
            # 更新ES
            if self.update_compensation_in_es(case_id, compensation_info):
                self.state["processed_cases"].add(case_id)
                self.state["compensation_stats"]["total_amount"] += compensation_info["total_amount"]
                self.state["compensation_stats"]["processed_count"] += 1
                batch_stats["succeeded"] += 1
                batch_results.append(compensation_info)
                
                self.log(f"💰 案例 {case_id}: {compensation_info['total_amount']:,}元")
            else:
                self.state["failed_cases"].add(case_id)
                batch_stats["failed"] += 1
            
            # 小延遲避免過載
            time.sleep(0.2)
        
        # 保存批次結果
        if batch_results:
            self._save_batch_results(batch_results)
        
        return batch_stats
    
    def _save_batch_results(self, batch_results: List[Dict[str, Any]]):
        """保存批次處理結果"""
        try:
            # 載入現有結果
            all_results = []
            if os.path.exists(self.results_file):
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    all_results = json.load(f)
            
            # 添加新結果
            all_results.extend(batch_results)
            
            # 保存更新後的結果
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.log(f"保存批次結果失敗: {e}", "ERROR")
    
    def run_update(self, max_cases: int = None):
        """執行賠償金額更新"""
        self.log(f"🚀 開始賠償金額更新 session: {self.session_name}")
        
        if not self.state["start_time"]:
            self.state["start_time"] = datetime.now().isoformat()
        
        # 獲取包含賠償金額的案例
        if self.state["total_cases"] == 0:
            all_case_ids = self.get_cases_with_compensation()
            if not all_case_ids:
                self.log("❌ 無法找到包含賠償的案例", "ERROR")
                return False
            
            if max_cases:
                all_case_ids = all_case_ids[:max_cases]
                self.log(f"🎯 限制處理 {max_cases} 個案例")
            
            self.state["total_cases"] = len(all_case_ids)
        else:
            all_case_ids = self.get_cases_with_compensation()
            if max_cases:
                all_case_ids = all_case_ids[:max_cases]
        
        # 過濾未處理的案例
        remaining_cases = [cid for cid in all_case_ids if cid not in self.state["processed_cases"]]
        self.log(f"📊 總案例: {len(all_case_ids)}, 剩餘: {len(remaining_cases)}")
        
        if not remaining_cases:
            self.log("✅ 所有案例已處理完成!")
            self._generate_final_report()
            self.state["completed"] = True
            self.save_progress()
            return True
        
        # 分批處理
        batches = [remaining_cases[i:i+self.state["batch_size"]] 
                  for i in range(0, len(remaining_cases), self.state["batch_size"])]
        
        self.log(f"📦 分為 {len(batches)} 個批次處理，每批 {self.state['batch_size']} 個案例")
        
        # 開始處理
        for batch_idx, batch in enumerate(batches, self.state["current_batch"] + 1):
            if not self.running:
                break
            
            self.state["current_batch"] = batch_idx
            self.log(f"🔄 處理批次 {batch_idx}/{len(batches)} ({len(batch)} 個案例)")
            
            batch_stats = self.process_batch(batch)
            
            self.log(f"📊 批次 {batch_idx} 完成: 成功 {batch_stats['succeeded']}, 失敗 {batch_stats['failed']}, 跳過 {batch_stats['skipped']}")
            self.log(f"📈 總進度: {len(self.state['processed_cases'])}/{self.state['total_cases']} ({(len(self.state['processed_cases'])/self.state['total_cases'])*100:.1f}%)")
            
            # 保存進度
            self.save_progress()
            
            # 批次間小延遲
            time.sleep(1)
        
        # 生成最終報告
        if self.running:
            self._generate_final_report()
            self.state["completed"] = True
            self.save_progress()
            
        return True
    
    def _generate_final_report(self):
        """生成最終處理報告"""
        self.log("=" * 60)
        self.log("📊 賠償金額更新最終報告")
        self.log("=" * 60)
        
        processed_count = len(self.state["processed_cases"])
        failed_count = len(self.state["failed_cases"])
        total_amount = self.state["compensation_stats"]["total_amount"]
        
        self.log(f"總處理案例: {processed_count}")
        self.log(f"處理失敗: {failed_count}")
        self.log(f"累計賠償金額: {total_amount:,}元")
        
        if processed_count > 0:
            avg_amount = total_amount / processed_count
            self.log(f"平均賠償金額: {avg_amount:,.0f}元")
        
        # 計算耗時
        if self.state["start_time"]:
            start_time = datetime.fromisoformat(self.state["start_time"])
            duration = datetime.now() - start_time
            self.log(f"⏱️ 總耗時: {duration}")

def main():
    """主程序"""
    print("💰 增強版賠償金額更新器")
    print("=" * 60)
    
    choice = input("""請選擇操作：
1. 開始新的更新任務
2. 繼續現有任務
3. 查看任務狀態

請輸入選擇 (1-3): """).strip()
    
    if choice == "1":
        session_name = input("請輸入任務名稱 (留空使用預設): ").strip()
        if not session_name:
            session_name = f"compensation_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        max_cases = input("限制處理案例數量 (留空處理全部): ").strip()
        max_cases = int(max_cases) if max_cases.isdigit() else None
        
        updater = EnhancedCompensationUpdater(session_name)
        updater.run_update(max_cases)
        
    elif choice == "2":
        session_name = input("請輸入要繼續的任務名稱: ").strip()
        if not session_name:
            print("❌ 請提供任務名稱")
            return
        
        updater = EnhancedCompensationUpdater(session_name)
        updater.run_update()
        
    elif choice == "3":
        session_name = input("請輸入要查看的任務名稱: ").strip()
        if not session_name:
            print("❌ 請提供任務名稱")
            return
        
        progress_file = f"{session_name}_progress.pkl"
        if os.path.exists(progress_file):
            with open(progress_file, 'rb') as f:
                state = pickle.load(f)
            
            print("\n📊 任務狀態:")
            print(f"任務名稱: {state['session_name']}")
            print(f"已處理: {len(state['processed_cases'])}")
            print(f"失敗案例: {len(state['failed_cases'])}")
            print(f"當前批次: {state['current_batch']}")
            print(f"是否完成: {state['completed']}")
            print(f"累計金額: {state['compensation_stats']['total_amount']:,}元")
        else:
            print("❌ 找不到該任務的進度檔案")
    
    else:
        print("❌ 無效選擇")

if __name__ == "__main__":
    main()