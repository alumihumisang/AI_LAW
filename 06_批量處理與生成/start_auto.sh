#!/bin/bash
# 一鍵啟動自動更新器

echo "🚀 ES案件分類自動更新器"
echo "=============================="

# 檢查Python腳本是否存在
if [ ! -f "auto_updater.py" ]; then
    echo "❌ 找不到 auto_updater.py"
    exit 1
fi

echo "🤖 啟動自動更新器..."
echo "💡 程序會自動監控和重啟"
echo "💡 按 Ctrl+C 可停止"
echo ""

# 使用 nohup 讓程序在背景執行，即使終端關閉也會繼續
if [ "$1" = "background" ]; then
    echo "🔧 背景模式啟動..."
    nohup python3 auto_updater.py > auto_updater.log 2>&1 &
    echo "✅ 已在背景啟動，日誌檔案: auto_updater.log"
    echo "💡 使用 'python3 quick_status.py' 檢查狀態"
else
    # 前台執行
    python3 auto_updater.py
fi