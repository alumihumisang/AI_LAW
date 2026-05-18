#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系統容量極限測試 - 測試能處理的最大案例數
"""

import os
from indictment_cag import load_model, load_indictment_excel, prepare_indictment_kv_cache

def test_system_capacity():
    """測試系統的實際容量上限"""
    print("=== 系統容量極限測試 ===\n")
    
    # 載入模型
    try:
        load_model("gemma3:27b", use_ollama=True)
        print("✅ 模型載入成功")
    except Exception as e:
        print(f"❌ 模型載入失敗: {e}")
        return
    
    excel_path = "整合_起訴書_2995_CAG用.xlsx"
    
    # 測試不同數量級的案例處理能力
    test_cases = [1000, 1500, 2000, 2500, 2995]  # 逐步增加到全部案例
    
    for max_cases in test_cases:
        print(f"\n📊 測試 {max_cases} 個案例...")
        
        try:
            # 載入純事實數據
            facts_texts, _ = load_indictment_excel(
                excel_path, 
                max_knowledge=max_cases, 
                facts_only=True
            )
            
            actual_cases = len(facts_texts)
            total_chars = sum(len(text) for text in facts_texts)
            estimated_tokens = total_chars // 4  # 粗略估算token數
            
            print(f"✅ 成功載入 {actual_cases} 個事實案例")
            print(f"📈 總字符數: {total_chars:,}")
            print(f"🧮 估算tokens: {estimated_tokens:,}")
            
            # 檢查是否超過Ollama/gemma3:27b的上下文限制
            # gemma3:27b 的上下文窗口通常是 8192 tokens
            context_limit = 8192
            if estimated_tokens > context_limit:
                print(f"⚠️  超過模型上下文限制 ({context_limit:,} tokens)")
                print(f"📉 超出比例: {estimated_tokens/context_limit:.1f}倍")
                
                # 計算在上下文限制內能容納多少案例
                avg_tokens_per_case = estimated_tokens / actual_cases
                max_cases_in_limit = int(context_limit / avg_tokens_per_case)
                print(f"💡 在上下文限制內最多能容納: {max_cases_in_limit} 個案例")
                
                # 嘗試建立KV-Cache（會失敗或成功取決於實際限制）
                print(f"🧪 嘗試建立KV-Cache...")
                try:
                    # 只使用能容納在上下文限制內的案例數
                    safe_cases = facts_texts[:max_cases_in_limit]
                    kv_cache = prepare_indictment_kv_cache(
                        safe_cases,
                        model_name="gemma3:27b",
                        facts_only=True
                    )
                    print(f"✅ 成功建立 {len(safe_cases)} 個案例的KV-Cache")
                    
                except Exception as cache_error:
                    print(f"❌ KV-Cache建立失敗: {cache_error}")
            else:
                print(f"✅ 在上下文限制內 ({context_limit:,} tokens)")
                
                # 嘗試建立KV-Cache
                print(f"🧪 嘗試建立完整KV-Cache...")
                try:
                    kv_cache = prepare_indictment_kv_cache(
                        facts_texts,
                        model_name="gemma3:27b", 
                        facts_only=True
                    )
                    print(f"🎉 成功建立 {actual_cases} 個案例的完整KV-Cache！")
                    
                    return {
                        "max_successful_cases": actual_cases,
                        "total_chars": total_chars,
                        "estimated_tokens": estimated_tokens
                    }
                    
                except Exception as cache_error:
                    print(f"❌ KV-Cache建立失敗: {cache_error}")
                    
        except Exception as e:
            print(f"❌ 載入 {max_cases} 個案例失敗: {e}")
            break
    
    print(f"\n🔍 系統容量分析完成")

if __name__ == "__main__":
    result = test_system_capacity()
    if result:
        print(f"\n🏆 最終結果:")
        print(f"最大成功處理案例數: {result['max_successful_cases']}")
        print(f"對應字符數: {result['total_chars']:,}")
        print(f"對應token數: {result['estimated_tokens']:,}")