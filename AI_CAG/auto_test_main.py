#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動測試主程式 - 模擬用戶輸入
"""

import subprocess
import sys

def test_main_program():
    """自動測試主程式"""
    print("=== 自動測試 indictment_cag.py ===\n")
    
    # 準備輸入指令
    inputs = [
        "2",  # 選擇生成模式
        "1",  # 選擇gemma3:27b模型  
        "",   # 使用預設事故事實
    ]
    
    # 將輸入轉換為字符串
    input_string = "\n".join(inputs) + "\n"
    
    try:
        # 運行主程式並提供輸入
        result = subprocess.run(
            ["python", "indictment_cag.py"],
            input=input_string,
            capture_output=True,
            text=True,
            timeout=120  # 2分鐘超時
        )
        
        print("📤 程式輸出:")
        print("-" * 50)
        print(result.stdout)
        
        if result.stderr:
            print("\n⚠️ 錯誤輸出:")
            print("-" * 50)
            print(result.stderr)
        
        print(f"\n✅ 程式執行完成，返回代碼: {result.returncode}")
        
    except subprocess.TimeoutExpired:
        print("⏱️ 程式執行超時（2分鐘）")
    except Exception as e:
        print(f"❌ 執行失敗: {e}")

if __name__ == "__main__":
    test_main_program()