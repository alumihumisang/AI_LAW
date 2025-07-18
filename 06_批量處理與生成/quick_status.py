#!/usr/bin/env python3
"""
快速狀態檢查器 - 立即顯示當前進度
"""

import os
import pickle
import subprocess
from datetime import datetime

def check_status():
    """快速檢查狀態"""
    print("🔍 ES案件分類進度檢查")
    print("="*50)
    print(f"⏰ 檢查時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 檢查進度檔案
    session_name = "continue_remaining_cases"
    progress_file = f"{session_name}_progress.pkl"
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'rb') as f:
                state = pickle.load(f)
            
            processed = len(state.get('processed_cases', set()))
            total = state.get('total_cases', 0)
            percentage = (processed / total) * 100 if total > 0 else 0
            batch = state.get('current_batch', 0)
            completed = state.get('completed', False)
            failed = len(state.get('failed_cases', set()))
            
            print("📊 進度資訊:")
            print(f"   已處理: {processed:,} / {total:,} 案例")
            print(f"   完成率: {percentage:.1f}%")
            print(f"   當前批次: {batch}")
            print(f"   失敗案例: {failed}")
            print(f"   任務狀態: {'✅ 完成' if completed else '🔄 進行中'}")
            
        except Exception as e:
            print(f"❌ 讀取進度檔案失敗: {e}")
    else:
        print("❌ 找不到進度檔案")
    
    print()
    
    # 2. 檢查程序是否在運行
    try:
        result = subprocess.run(
            ["pgrep", "-f", "robust_case_type_updater"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"🔄 程序狀態: ✅ 運行中 (PID: {', '.join(pids)})")
        else:
            print("🔄 程序狀態: ❌ 未運行")
    except Exception as e:
        print(f"🔄 程序狀態: ❓ 檢查失敗 ({e})")
    
    print()
    
    # 3. 檢查最新日誌
    log_file = f"{session_name}_log.txt"
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if lines:
                print("📝 最新日誌 (最後5行):")
                for line in lines[-5:]:
                    print(f"   {line.strip()}")
            else:
                print("📝 日誌檔案是空的")
                
        except Exception as e:
            print(f"❌ 讀取日誌失敗: {e}")
    else:
        print("❌ 找不到日誌檔案")
    
    print()
    print("💡 如果程序未運行，可以使用:")
    print("   python3 auto_updater.py  (自動重啟模式)")
    print("   python3 robust_case_type_updater.py  (手動模式)")

if __name__ == "__main__":
    check_status()