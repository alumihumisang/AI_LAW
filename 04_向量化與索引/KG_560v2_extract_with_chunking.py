"""
KG_560v2_extract_with_chunking.py
🆕 使用LLM從段落中提取結構化信息（含Chunking機制）

改進：
1. 先按句號切分段落成chunk（保留完整上下文）
2. 對每個chunk提取結構化信息
3. 輸出包含chunk_id的結構化數據

Chunking策略：只按句號(。)切分
- 優點：保留完整語義單元，上下文不斷裂
- 避免：按逗號切分會導致碎片化，LLM難以理解

執行順序: 在刪除舊Detail節點後執行
輸入: Excel檔案 (整合_起訴書_四段(FINAL)_6057.xlsx)
輸出: structured_summaries_with_chunks.jsonl
"""

import json
import logging
import os
import re
import requests
import pandas as pd
from typing import Dict, List, Any
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[
        logging.FileHandler("kg_560v2_chunking.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Ollama API設定
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:27b"

# Excel檔案路徑
EXCEL_FILE = "/home/aru/AI_LAW/09_輸入輸出資料/整合_起訴書_四段(FINAL)_6057.xlsx"


def chunk_by_sentence(text: str, case_id: str, section_name: str) -> List[Dict[str, Any]]:
    """
    按句號切分段落成句子級chunk

    Args:
        text: 段落原文
        case_id: 案件ID
        section_name: 段落名稱 (facts/laws/compensation/conclusion)

    Returns:
        list of dict: [{chunk_id, chunk_text, chunk_index, parent_section}, ...]
    """
    if not text or pd.isna(text):
        return []

    # 按句號切分（保留標點）
    sentences = re.split(r'([。])', str(text))

    chunks = []
    chunk_index = 0

    for i in range(0, len(sentences)-1, 2):
        sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
        sentence = sentence.strip()

        # 過濾太短的句子
        if sentence and len(sentence) > 5:
            chunks.append({
                'chunk_id': f'case_{case_id}_{section_name}_chunk_{chunk_index}',
                'chunk_text': sentence,
                'chunk_index': chunk_index,
                'parent_section': section_name,
                'case_id': case_id
            })
            chunk_index += 1

    return chunks


def call_ollama(prompt: str, system_prompt: str = "") -> str:
    """呼叫Ollama API"""
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2000
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        logger.error(f"Ollama API呼叫失敗: {str(e)}")
        return ""


def filter_smart(data: Dict[str, Any]) -> Dict[str, Any]:
    """過濾掉None、空字串、空列表、空字典"""
    # 🔧 如果 Gemma 回傳 list，取第一個元素
    if isinstance(data, list):
        if len(data) == 0:
            return {}
        data = data[0]  # 取第一個元素

    # 如果不是 dict，返回空字典
    if not isinstance(data, dict):
        return {}

    def is_meaningful(value):
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True

    return {k: v for k, v in data.items() if is_meaningful(v)}


def extract_fact_detail_from_chunk(chunk_text: str) -> Dict[str, Any]:
    """從事實chunk提取FactDetail結構化信息"""

    prompt = f"""請從這句話中提取結構化信息。如果某類信息不存在，就不要包含該欄位。

句子：{chunk_text}

請以JSON格式回答，只包含確實存在的信息：
{{
  "detail_type": "InjuryInfo",  // 或 VehicleInfo, TimeInfo, LocationInfo, PartyInfo, EvidenceInfo
  "extracted_info": {{
    // 根據detail_type填寫對應欄位
    // InjuryInfo範例：
    "injuries": [{{"body_part": "左膝", "injury_type": "骨折", "medical_term": "十字韌帶撕裂性骨折"}}],
    "severity_score": 8.5,
    "treatment": ["手術"]

    // VehicleInfo範例：
    // "vehicle_type": "重型機車", "fault_indication": true

    // TimeInfo範例：
    // "date": "2024-08-18", "time": "21:26"

    // LocationInfo範例：
    // "city": "新北市", "district": "板橋區"
  }},
  "semantic_summary": "原告左膝嚴重骨折需手術"
}}

如果這句話沒有可提取的結構化信息，回答：{{"detail_type": null}}

回答（只要JSON）："""

    try:
        system_prompt = "你是法律文書分析助手。只回答JSON格式。"
        response_text = call_ollama(prompt, system_prompt)

        # 清理markdown
        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        return filter_smart(result)

    except Exception as e:
        logger.error(f"❌ Chunk提取失敗: {str(e)}")
        return {}


def extract_law_detail_from_chunk(chunk_text: str) -> Dict[str, Any]:
    """從法條chunk提取LawDetail結構化信息"""

    prompt = f"""請從這句法條引用中提取結構化信息。

句子：{chunk_text}

請以JSON格式回答：
{{
  "article": "民法第184條第1項前段",
  "applicable_reason": "被告過失侵權",
  "supporting_facts": ["未注意車前狀況"],
  "fault_type": "negligence",
  "semantic_summary": "被告過失侵權，符合民法184條要件"
}}

如果沒有法條，回答：{{"article": null}}

回答（只要JSON）："""

    try:
        system_prompt = "你是法律分析專家。只回答JSON格式。"
        response_text = call_ollama(prompt, system_prompt)

        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        return filter_smart(result)

    except Exception as e:
        logger.error(f"❌ 法條chunk提取失敗: {str(e)}")
        return {}


def extract_compensation_detail_from_chunk(chunk_text: str) -> Dict[str, Any]:
    """從賠償chunk提取CompensationDetail結構化信息"""

    prompt = f"""請從這句賠償描述中提取結構化信息。

句子：{chunk_text}

請以JSON格式回答：
{{
  "category": "medical",  // medical/nursing/vehicle/income_loss/mental/equipment/transportation/other
  "item_name": "醫療費用",
  "amount": 171170,
  "calculation_method": "實際支出",
  "semantic_summary": "原告支出醫療費17萬元"
}}

如果沒有賠償項目，回答：{{"category": null}}

回答（只要JSON）："""

    try:
        system_prompt = "你是法律財務分析專家。只回答JSON格式。"
        response_text = call_ollama(prompt, system_prompt)

        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        return filter_smart(result)

    except Exception as e:
        logger.error(f"❌ 賠償chunk提取失敗: {str(e)}")
        return {}


def extract_conclusion_detail_from_chunk(chunk_text: str) -> Dict[str, Any]:
    """從結論chunk提取ConclusionDetail結構化信息"""

    prompt = f"""請從這句結論中提取結構化信息。

句子：{chunk_text}

請以JSON格式回答：
{{
  "total_claimed": 1237470,
  "interest_rate": 0.05,
  "semantic_summary": "請求被告賠償123萬元"
}}

如果沒有結論信息，回答：{{"total_claimed": null}}

回答（只要JSON）："""

    try:
        system_prompt = "你是法律分析專家。只回答JSON格式。"
        response_text = call_ollama(prompt, system_prompt)

        response_text = response_text.strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        return filter_smart(result)

    except Exception as e:
        logger.error(f"❌ 結論chunk提取失敗: {str(e)}")
        return {}


def process_all_cases(output_file: str = "structured_summaries_with_chunks.jsonl", limit: int = None):
    """處理所有案件，生成帶chunk_id的結構化數據（支援斷點續傳）"""

    # 🔄 斷點續傳：檢查已處理的案件
    processed_case_ids = set()
    if os.path.exists(output_file):
        logger.info(f"🔍 發現已存在的輸出檔案，檢查已處理的案件...")
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    processed_case_ids.add(data['case_id'])
            logger.info(f"✅ 已處理 {len(processed_case_ids)} 個案件，將從斷點繼續")
        except Exception as e:
            logger.warning(f"⚠️  讀取現有檔案失敗: {e}，將重新開始")
            processed_case_ids = set()

    logger.info(f"📖 讀取Excel檔案: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE, sheet_name="案件主幹(含四段原文)")

    if limit:
        df = df.head(limit)
        logger.info(f"🧪 測試模式：只處理前 {limit} 個案件")

    total_cases = len(df)
    remaining_cases = total_cases - len(processed_case_ids)
    logger.info(f"📊 總共 {total_cases} 個案件，已完成 {len(processed_case_ids)} 個，剩餘 {remaining_cases} 個")

    # 使用append模式（如果檔案存在）或write模式（新檔案）
    file_mode = 'a' if processed_case_ids else 'w'
    with open(output_file, file_mode, encoding='utf-8') as f:
        for idx, row in df.iterrows():
            case_id = str(row['case_id'])

            # 🔄 跳過已處理的案件
            if case_id in processed_case_ids:
                logger.info(f"⏭️  [{idx+1}/{total_cases}] 跳過已處理案件 {case_id}")
                continue

            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 [{idx+1}/{total_cases}] 處理案件 {case_id}")
            logger.info(f"{'='*60}")

            # 1. 處理事實概述
            if pd.notna(row['事實概述']):
                fact_chunks = chunk_by_sentence(row['事實概述'], case_id, 'facts')
                logger.info(f"  📦 事實概述切分為 {len(fact_chunks)} 個chunks")

                for chunk in fact_chunks:
                    extracted = extract_fact_detail_from_chunk(chunk['chunk_text'])
                    if extracted.get('detail_type'):
                        chunk_data = {
                            **chunk,
                            'extracted_detail': extracted
                        }
                        f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')

            # 2. 處理法條引用
            if pd.notna(row['法條引用']):
                law_chunks = chunk_by_sentence(row['法條引用'], case_id, 'laws')
                logger.info(f"  📦 法條引用切分為 {len(law_chunks)} 個chunks")

                for chunk in law_chunks:
                    extracted = extract_law_detail_from_chunk(chunk['chunk_text'])
                    if extracted.get('article'):
                        chunk_data = {
                            **chunk,
                            'extracted_detail': extracted
                        }
                        f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')

            # 3. 處理損害賠償項目
            if pd.notna(row['損害賠償項目']):
                comp_chunks = chunk_by_sentence(row['損害賠償項目'], case_id, 'compensation')
                logger.info(f"  📦 賠償項目切分為 {len(comp_chunks)} 個chunks")

                for chunk in comp_chunks:
                    extracted = extract_compensation_detail_from_chunk(chunk['chunk_text'])
                    if extracted.get('category'):
                        chunk_data = {
                            **chunk,
                            'extracted_detail': extracted
                        }
                        f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')

            # 4. 處理結論 - ⏭️ 跳過（結論用Excel原始資料即可，不需要Gemma提取）
            # if pd.notna(row['結論']):
            #     conc_chunks = chunk_by_sentence(row['結論'], case_id, 'conclusion')
            #     logger.info(f"  📦 結論切分為 {len(conc_chunks)} 個chunks")
            #
            #     for chunk in conc_chunks:
            #         extracted = extract_conclusion_detail_from_chunk(chunk['chunk_text'])
            #         if extracted.get('total_claimed') or extracted.get('interest_rate'):
            #             chunk_data = {
            #                 **chunk,
            #                 'extracted_detail': extracted
            #             }
            #             f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')

            logger.info(f"✅ 案件 {case_id} 完成（已跳過結論處理）")

    # 完成統計
    new_processed = total_cases - len(processed_case_ids)
    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 處理完成！")
    logger.info(f"📊 本次新處理: {new_processed} 個案件")
    logger.info(f"📊 累計完成: {total_cases} 個案件")
    logger.info(f"📄 輸出檔案: {output_file}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    import sys

    try:
        # 檢查命令行參數
        if len(sys.argv) > 1:
            limit = int(sys.argv[1])
            output_file = f"structured_summaries_test_{limit}.jsonl"
            logger.info(f"🧪 測試模式：只處理前 {limit} 個案件")
        else:
            mode = input("選擇模式 (1=測試3個/2=全部處理): ").strip()
            if mode == "1":
                limit = 3
                output_file = "structured_summaries_test_3.jsonl"
            else:
                limit = None
                output_file = "structured_summaries_with_chunks.jsonl"
                confirm = input("⚠️  將處理所有6057案件，確定嗎? (y/n): ").strip().lower()
                if confirm != 'y':
                    logger.info("❌ 已取消")
                    exit(0)

        process_all_cases(output_file=output_file, limit=limit)
        logger.info(f"\n✅ 完成！輸出檔案：{output_file}")

    except Exception as e:
        logger.error(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
