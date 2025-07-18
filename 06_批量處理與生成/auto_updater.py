#!/usr/bin/env python3
"""
自動案件分類更新器 - 自動重啟和監控
當程序中斷時會自動重新啟動，並提供簡單的狀態顯示
"""

import os
import time
import subprocess
import signal
import sys
from datetime import datetime

class AutoUpdater:
    def __init__(self):
        self.session_name = "continue_remaining_cases"
        self.script_path = "robust_case_type_updater.py"
        self.running = True
        self.restart_count = 0
        self.max_restarts = 10  # 最多重啟10次
        
        # 註冊信號處理器
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
    
    def stop(self, signum=None, frame=None):
        """停止自動更新器"""
        print("\n🛑 收到停止信號，正在安全關閉...")
        self.running = False
        sys.exit(0)
    
    def check_progress(self):
        """檢查當前進度"""
        try:
            import pickle
            progress_file = f"{self.session_name}_progress.pkl"
            
            if os.path.exists(progress_file):
                with open(progress_file, 'rb') as f:
                    state = pickle.load(f)
                
                processed = len(state.get('processed_cases', set()))
                total = state.get('total_cases', 0)
                percentage = (processed / total) * 100 if total > 0 else 0
                completed = state.get('completed', False)
                
                return {
                    'processed': processed,
                    'total': total,
                    'percentage': percentage,
                    'completed': completed,
                    'exists': True
                }
            else:
                return {'exists': False}
                
        except Exception as e:
            print(f"❌ 檢查進度失敗: {e}")
            return {'exists': False}
    
    def is_process_running(self):
        """檢查更新程序是否在運行"""
        try:
            # 檢查是否有 robust_case_type_updater.py 在運行
            result = subprocess.run(
                ["pgrep", "-f", "robust_case_type_updater"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def start_updater(self):
        """啟動更新程序"""
        print(f"🚀 啟動更新程序... (重啟次數: {self.restart_count})")
        
        try:
            # 使用 subprocess 在背景執行
            process = subprocess.Popen(
                [
                    "python3", self.script_path
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 發送自動輸入來繼續現有任務
            input_data = f"2\n{self.session_name}\n"
            stdout, stderr = process.communicate(input=input_data, timeout=10)
            
            if process.returncode != 0:
                print(f"❌ 程序啟動失敗: {stderr}")
                return False
            
            print("✅ 更新程序已啟動")
            return True
            
        except subprocess.TimeoutExpired:
            # 10秒後沒有回應表示程序正在正常運行
            print("✅ 更新程序啟動成功（正在背景運行）")
            return True
        except Exception as e:
            print(f"❌ 啟動程序異常: {e}")
            return False
    
    def show_status(self):
        """顯示當前狀態"""
        print("\n" + "="*60)
        print(f"🤖 自動更新器狀態 - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        # 檢查進度
        progress = self.check_progress()
        
        if progress['exists']:
            if progress['completed']:
                print("🎉 任務已完成！")
                print(f"📊 最終結果: {progress['processed']:,}/{progress['total']:,} (100%)")
                return True
            else:
                print(f"📊 當前進度: {progress['processed']:,}/{progress['total']:,} ({progress['percentage']:.1f}%)")
        else:
            print("⚠️ 找不到進度檔案")
        
        # 檢查程序狀態
        is_running = self.is_process_running()
        print(f"🔄 程序狀態: {'運行中' if is_running else '已停止'}")
        print(f"🔁 重啟次數: {self.restart_count}")
        
        return False  # 未完成
    
    def run(self):
        """主運行循環"""
        print("🤖 ES案件分類自動更新器")
        print("="*60)
        print("💡 此程序會自動監控和重啟更新任務")
        print("💡 按 Ctrl+C 可安全停止")
        print()
        
        while self.running:
            try:
                # 顯示狀態
                completed = self.show_status()
                
                if completed:
                    print("🎉 所有案例處理完成！自動更新器退出。")
                    break
                
                # 檢查程序是否在運行
                if not self.is_process_running():
                    print("⚠️ 檢測到程序已停止，準備重啟...")
                    
                    if self.restart_count >= self.max_restarts:
                        print(f"❌ 已達到最大重啟次數 ({self.max_restarts})，停止自動重啟")
                        break
                    
                    # 等待一下再重啟
                    print("⏳ 等待5秒後重啟...")
                    time.sleep(5)
                    
                    if self.start_updater():
                        self.restart_count += 1
                        print(f"✅ 程序已重啟 (第 {self.restart_count} 次)")
                    else:
                        print("❌ 重啟失敗，將在30秒後重試")
                        time.sleep(30)
                else:
                    print("✅ 程序運行正常")
                
                # 等待30秒再檢查
                print(f"⏳ 等待30秒後再次檢查...")
                print("="*60)
                time.sleep(30)
                
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                print(f"❌ 監控過程異常: {e}")
                time.sleep(30)

def main():
    print("🚀 ES案件分類自動更新器")
    print("="*60)
    
    choice = input("""請選擇操作：
1. 啟動自動更新器（推薦）
2. 僅檢查當前狀態
3. 手動啟動更新程序一次

請輸入選擇 (1-3): """).strip()
    
    auto_updater = AutoUpdater()
    
    if choice == "1":
        print("\n🤖 啟動自動監控模式...")
        print("💡 程序會自動監控和重啟，您可以安心離開")
        auto_updater.run()
        
    elif choice == "2":
        print("\n📊 檢查當前狀態...")
        auto_updater.show_status()
        
    elif choice == "3":
        print("\n🚀 手動啟動一次...")
        if auto_updater.start_updater():
            print("✅ 程序已啟動，但不會自動重啟")
        else:
            print("❌ 啟動失敗")
    else:
        print("❌ 無效選擇")

if __name__ == "__main__":
    main()