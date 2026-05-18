#!/usr/bin/env python3
"""
起訴書資料處理與CAG整合腳本
處理Excel格式的起訴書資料,生成問答對,並執行KV-Encode
"""

import pandas as pd
import torch
import argparse
import os
import random
import json
from typing import List, Tuple, Iterator
from time import time
from transformers import AutoTokenizer, AutoModelForCausalLM

# 嘗試導入量化配置,如果失敗則設為None
try:
    from transformers import BitsAndBytesConfig
    HAS_BITSANDBYTES = True
except ImportError:
    BitsAndBytesConfig = None
    HAS_BITSANDBYTES = False
from transformers.cache_utils import DynamicCache
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 載入環境變數
from dotenv import load_dotenv
load_dotenv()

# 全局變數
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = None
tokenizer = None

def load_model(model_name: str = "microsoft/DialoGPT-medium", use_ollama: bool = False):
    """載入LLM模型和tokenizer"""
    global model, tokenizer
    
    logger.info(f"正在載入模型: {model_name}")
    
    # 如果使用Ollama
    if use_ollama:
        logger.info("使用Ollama模型")
        try:
            import ollama
            # 測試Ollama連接
            models = ollama.list()
            logger.info("Ollama連接成功")
            logger.info(f"可用模型: {[m.model for m in models.models]}")
            
            # 檢查指定模型是否存在
            available_models = [m.model for m in models.models]
            model_exists = model_name in available_models
            if not model_exists:
                logger.error(f"模型 {model_name} 不存在於Ollama中")
                logger.info(f"可用模型: {available_models}")
                logger.info(f"請確認模型名稱或執行: ollama pull {model_name}")
                raise ValueError(f"模型 {model_name} 不存在")
            
            # 設置全局變數以表示使用Ollama
            model = "ollama"
            tokenizer = None
            logger.info(f"已設置使用Ollama模型: {model_name}")
            return
        except ImportError:
            logger.warning("未安裝ollama套件,改用transformers")
            logger.info("請執行: pip install ollama")
        except Exception as e:
            logger.warning(f"Ollama連接失敗: {e}")
            logger.error("無法使用Ollama模型,請檢查:")
            logger.error("1. Ollama服務是否運行: ollama list")
            logger.error("2. 模型名稱是否正確")
            logger.error("3. 網路連接是否正常")
            raise
    
    # 量化配置(如果有bitsandbytes)
    quantization_config = None
    if HAS_BITSANDBYTES:
        logger.info("使用4-bit量化")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
    else:
        logger.warning("未找到bitsandbytes,將使用標準精度載入模型")
    
    # 載入tokenizer
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            token=os.getenv("HF_TOKEN"),
            padding_side="left"
        )
    except Exception as e:
        logger.error(f"載入tokenizer失敗: {e}")
        # 嘗試不使用token
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                padding_side="left"
            )
        except Exception as e2:
            logger.error(f"載入tokenizer失敗 (無token): {e2}")
            raise
    
    # 準備模型載入參數
    model_kwargs = {
        "device_map": "auto",
        "torch_dtype": torch.float16,
    }
    
    # 如果有token則添加
    if os.getenv("HF_TOKEN"):
        model_kwargs["token"] = os.getenv("HF_TOKEN")
    
    # 如果有量化配置則添加
    if quantization_config:
        model_kwargs["quantization_config"] = quantization_config
    
    # 嘗試使用flash attention,如果失敗則使用標準attention
    try:
        model_kwargs["attn_implementation"] = "flash_attention_2"
        model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        logger.info("使用Flash Attention 2")
    except Exception as e:
        logger.warning(f"Flash Attention 2 載入失敗: {e}")
        model_kwargs.pop("attn_implementation", None)
        try:
            model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
            logger.info("使用標準Attention")
        except Exception as e2:
            logger.error(f"模型載入失敗: {e2}")
            raise
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    logger.info("模型載入完成")

def extract_facts_only(document):
    """只提取事實部分"""
    
    # 找到法條部分開始的標記
    legal_markers = ['二、按', '二、法律依據', '依民法第', '按民法第']
    
    end_pos = len(document)
    for marker in legal_markers:
        if marker in document:
            pos = document.find(marker)
            if pos > 50:  # 確保不是在很前面
                end_pos = min(end_pos, pos)
    
    # 只保留事實部分
    facts_only = document[:end_pos].strip()
    
    # 清理格式
    if facts_only.startswith('一、'):
        facts_only = facts_only[2:].strip()
    
    return facts_only

def determine_applicable_laws(accident_facts, injuries="", compensation_facts=""):
    """智能判斷適用法條"""
    applicable_laws = []
    
    # 基本侵權責任（必定適用）
    applicable_laws.append("民法第184條第1項前段")
    
    # 車輛事故相關
    vehicle_keywords = ['車輛', '汽車', '機車', '駕駛', '追撞', '碰撞', '行駛']
    if any(keyword in accident_facts for keyword in vehicle_keywords):
        applicable_laws.append("民法第191條之2")
    
    # 身體傷害相關
    injury_keywords = ['受傷', '傷害', '骨折', '挫傷', '撞傷', '醫療', '治療', '休養']
    if any(keyword in accident_facts or keyword in injuries for keyword in injury_keywords):
        applicable_laws.append("民法第193條第1項")
    
    # 精神損害相關
    mental_keywords = ['精神', '慰撫金', '痛苦', '創傷']
    if any(keyword in accident_facts or keyword in compensation_facts for keyword in mental_keywords):
        applicable_laws.append("民法第195條第1項前段")
    
    return applicable_laws

def generate_standard_laws(accident_facts, injuries="", compensation_facts=""):
    """規則化生成法律依據"""
    
    # 智能判斷適用法條
    applicable_laws = determine_applicable_laws(accident_facts, injuries, compensation_facts)
    
    # 法條條文對照表
    law_descriptions = {
        "民法第184條第1項前段": "因故意或過失，不法侵害他人之權利者，負損害賠償責任。",
        "民法第191條之2": "汽車、機車或其他非依軌道行駛之動力車輛，在使用中加損害於他人者，駕駛人應賠償因此所生之損害。",
        "民法第193條第1項": "不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。",
        "民法第195條第1項前段": "不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。"
    }
    
    # 組合法條內容
    law_texts = []
    valid_laws = []
    
    for law in applicable_laws:
        if law in law_descriptions:
            law_texts.append(f"「{law_descriptions[law]}」")
            valid_laws.append(law)
    
    # 組合標準格式
    law_content_block = "、".join(law_texts)
    article_list = "、".join(valid_laws)
    
    return f"""二、按{law_content_block}{article_list}分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任："""

def load_indictment_excel(filepath: str, max_knowledge: int = None, facts_only: bool = False) -> Tuple[List[str], List[dict]]:
    """
    讀取起訴書Excel檔案
    
    Args:
        filepath: Excel檔案路徑
        max_knowledge: 最大起訴書數量
        facts_only: 是否只提取事實部分
        
    Returns:
        text_list: 完整起訴書文本列表（或純事實文本列表）
        case_data: 案件資料列表
    """
    try:
        logger.info(f"讀取Excel檔案: {filepath}")
        
        # 讀取四個工作表
        df_facts = pd.read_excel(filepath, sheet_name="事實編輯")
        df_laws = pd.read_excel(filepath, sheet_name="2995法條")
        df_compensation = pd.read_excel(filepath, sheet_name="2995賠償")
        df_conclusion = pd.read_excel(filepath, sheet_name="2995結論")
        
        logger.info(f"讀取工作表完成:")
        logger.info(f"  事實編輯: {len(df_facts)} 筆")
        logger.info(f"  2995法條: {len(df_laws)} 筆")
        logger.info(f"  2995賠償: {len(df_compensation)} 筆")
        logger.info(f"  2995結論: {len(df_conclusion)} 筆")
        
        # 獲取實際的欄位名稱(在合併前確定欄位名稱)
        facts_col = "起訴書" if "起訴書" in df_facts.columns else df_facts.columns[1]
        laws_col = "法條引用" if "法條引用" in df_laws.columns else df_laws.columns[1]
        comp_col = "損害賠償項目" if "損害賠償項目" in df_compensation.columns else df_compensation.columns[1]
        conc_col = "結論" if "結論" in df_conclusion.columns else df_conclusion.columns[1]
        
        # 只選擇需要的欄位進行合併,避免重複欄位問題
        df_facts_clean = df_facts[['case_id', facts_col]].copy()
        df_laws_clean = df_laws[['case_id', laws_col]].copy()
        df_compensation_clean = df_compensation[['case_id', comp_col]].copy()
        df_conclusion_clean = df_conclusion[['case_id', conc_col]].copy()
        
        # 合併所有工作表基於case_id
        merged_df = df_facts_clean.merge(df_laws_clean, on="case_id", how="inner")
        merged_df = merged_df.merge(df_compensation_clean, on="case_id", how="inner")
        merged_df = merged_df.merge(df_conclusion_clean, on="case_id", how="inner")
        
        logger.info(f"合併後共有 {len(merged_df)} 筆完整資料")
        
        # 限制資料數量
        if max_knowledge:
            merged_df = merged_df.head(max_knowledge)
            logger.info(f"限制為 {max_knowledge} 筆資料")
        
        logger.info(f"欄位對應:")
        logger.info(f"  事實欄位: {facts_col}")
        logger.info(f"  法條欄位: {laws_col}")
        logger.info(f"  賠償欄位: {comp_col}")
        logger.info(f"  結論欄位: {conc_col}")
        
        # 建立完整的起訴書文本和案件資料
        text_list = []
        case_data = []
        
        for _, row in merged_df.iterrows():
            if facts_only:
                # 只提取事實部分
                facts_text = extract_facts_only(str(row[facts_col]))
                if len(facts_text) > 50:  # 降低門檻，包含更多簡潔但有效的案例
                    text_list.append(facts_text)
                else:
                    continue  # 跳過內容太少的案例
            else:
                # 組合完整的起訴書
                full_indictment = f"""案件編號: {row['case_id']}

一,事實部分:
{row[facts_col]}

二,法條部分:
{row[laws_col]}

三,賠償部分:
{row[comp_col]}

四,結論部分:
{row[conc_col]}
"""
                text_list.append(full_indictment)
            
            # 儲存結構化資料
            case_info = {
                "case_id": row['case_id'],
                "facts": row[facts_col],
                "laws": row[laws_col],
                "compensation": row[comp_col],
                "conclusion": row[conc_col]
            }
            case_data.append(case_info)
        
        logger.info(f"成功處理 {len(text_list)} 筆起訴書資料")
        return text_list, case_data
        
    except Exception as e:
        logger.error(f"讀取Excel檔案時發生錯誤: {e}")
        return [], []

def generate_legal_qa_pairs(case_data: List[dict], max_questions: int = None) -> Tuple[List[str], List[str]]:
    """
    基於起訴書資料生成問答對
    
    Args:
        case_data: 案件資料列表
        max_questions: 最大問題數量
        
    Returns:
        questions: 問題列表
        answers: 答案列表
    """
    logger.info("開始生成法律問答對...")
    
    questions = []
    answers = []
    
    # 問題模板
    question_templates = [
        # 事實相關問題
        ("案件 {case_id} 的事故發生經過為何?", "facts"),
        ("請描述案件 {case_id} 的事實背景.", "facts"),
        ("案件 {case_id} 中發生了什麼事故?", "facts"),
        
        # 法條相關問題
        ("案件 {case_id} 引用了哪些法條?", "laws"),
        ("請說明案件 {case_id} 的法律依據.", "laws"),
        ("案件 {case_id} 適用的法條為何?", "laws"),
        
        # 賠償相關問題
        ("案件 {case_id} 的賠償項目有哪些?", "compensation"),
        ("請列出案件 {case_id} 的損害賠償內容.", "compensation"),
        ("案件 {case_id} 要求賠償什麼?", "compensation"),
        
        # 結論相關問題
        ("案件 {case_id} 的結論為何?", "conclusion"),
        ("請說明案件 {case_id} 的最終結論.", "conclusion"),
        ("案件 {case_id} 的判決結果是什麼?", "conclusion"),
        
        # 綜合問題
        ("請完整說明案件 {case_id} 的內容.", "full"),
        ("案件 {case_id} 的重點為何?", "full")
    ]
    
    for case in case_data:
        case_id = case["case_id"]
        
        for question_template, answer_type in question_templates:
            question = question_template.format(case_id=case_id)
            
            if answer_type == "facts":
                answer = case["facts"]
            elif answer_type == "laws":
                answer = case["laws"]
            elif answer_type == "compensation":
                answer = case["compensation"]
            elif answer_type == "conclusion":
                answer = case["conclusion"]
            elif answer_type == "full":
                answer = f"事實:{case['facts']}\n法條:{case['laws']}\n賠償:{case['compensation']}\n結論:{case['conclusion']}"
            
            questions.append(question)
            answers.append(answer)
    
    # 隨機打亂問答對
    combined = list(zip(questions, answers))
    random.shuffle(combined)
    questions, answers = zip(*combined)
    questions, answers = list(questions), list(answers)
    
    # 限制問題數量
    if max_questions and len(questions) > max_questions:
        questions = questions[:max_questions]
        answers = answers[:max_questions]
    
    logger.info(f"生成了 {len(questions)} 個問答對")
    return questions, answers

def preprocess_knowledge(prompt: str, model_name: str = None):
    """
    為CAG準備知識KV緩存 (KV-Encode核心功能)
    
    Args:
        prompt: 知識提示文本
        model_name: 模型名稱(用於Ollama)
        
    Returns:
        DynamicCache 或 str: KV緩存或知識提示
    """
    logger.info("開始執行KV-Encode...")
    
    # 如果使用Ollama
    if model == "ollama":
        logger.info("使用Ollama模擬KV-Encode (實際為提示預處理)")
        # 對於Ollama,我們返回知識提示本身
        # 這不是真正的KV-cache,但可以達到類似效果
        logger.info(f"知識提示大小: {len(prompt)} 字符")
        return prompt
    
    # 使用transformers的真正KV-cache
    try:
        # 兼容不同模型結構
        if hasattr(model, 'model') and hasattr(model.model, 'embed_tokens'):
            # Llama style
            embed_device = model.model.embed_tokens.weight.device
        elif hasattr(model, 'transformer') and hasattr(model.transformer, 'wte'):
            # GPT style (DialoGPT)
            embed_device = model.transformer.wte.weight.device
        else:
            # Fallback to model device
            embed_device = next(model.parameters()).device
        
        # 分批處理長文本以避免記憶體問題
        max_chunk_size = 1024  # 每次處理1024個tokens
        input_text = prompt
        
        # 如果文本太長,截斷到合理大小
        if len(input_text) > 100000:  # 約100k字符
            input_text = input_text[:100000]
            logger.warning("文本過長,已截斷至100k字符")
        
        input_ids = tokenizer.encode(input_text, return_tensors="pt", max_length=8192, truncation=True).to(embed_device)
        logger.info(f"輸入token數量: {input_ids.shape[1]}")
        
        # 嘗試不同的KV-cache方法
        try:
            past_key_values = DynamicCache()
            
            with torch.no_grad():
                # 分批處理
                if input_ids.shape[1] > max_chunk_size:
                    logger.info("使用分批處理來建立KV緩存...")
                    for i in range(0, input_ids.shape[1], max_chunk_size):
                        chunk = input_ids[:, i:i+max_chunk_size]
                        outputs = model(
                            input_ids=chunk,
                            past_key_values=past_key_values,
                            use_cache=True,
                            output_attentions=False,
                            output_hidden_states=False
                        )
                        past_key_values = outputs.past_key_values
                        logger.info(f"處理了 {i+chunk.shape[1]} / {input_ids.shape[1]} tokens")
                else:
                    outputs = model(
                        input_ids=input_ids,
                        past_key_values=past_key_values,
                        use_cache=True,
                        output_attentions=False,
                        output_hidden_states=False
                    )
                    past_key_values = outputs.past_key_values
            
            logger.info(f"KV緩存大小: {past_key_values.key_cache[0].shape[-2]} tokens")
            return past_key_values
            
        except Exception as cache_error:
            logger.warning(f"DynamicCache失敗: {cache_error}")
            # 嘗試傳統方法
            try:
                with torch.no_grad():
                    outputs = model(
                        input_ids=input_ids,
                        use_cache=True,
                        output_attentions=False,
                        output_hidden_states=False
                    )
                    past_key_values = outputs.past_key_values
                
                if past_key_values is not None:
                    logger.info(f"使用傳統KV緩存,層數: {len(past_key_values)}")
                    return past_key_values
                else:
                    raise Exception("無法建立KV緩存")
                    
            except Exception as traditional_error:
                logger.warning(f"傳統KV緩存也失敗: {traditional_error}")
                raise Exception("所有KV緩存方法都失敗")
        
    except Exception as e:
        logger.error(f"KV-cache建立失敗: {e}")
        logger.warning("回退到Ollama模式")
        return prompt

def prepare_indictment_kv_cache(documents: List[str], output_path: str = None, model_name: str = None, facts_only: bool = False):
    """
    為起訴書準備KV緩存
    
    Args:
        documents: 起訴書文本列表（或純事實文本列表）
        output_path: 緩存保存路徑
        model_name: 模型名稱
        facts_only: 是否為純事實模式
        
    Returns:
        DynamicCache 或 str: KV緩存或知識提示
    """
    logger.info("準備起訴書KV緩存...")
    
    # 組合所有起訴書文本並添加索引
    indexed_docs = []
    for i, doc in enumerate(documents, 1):
        indexed_docs.append(f"=== 案例 {i} ===\n{doc}")
    
    knowledge_text = "\n\n".join(indexed_docs)
    
    # 構建系統提示
    if model == "ollama":
        if facts_only:
            # 純事實模式的提示格式
            system_prompt = f"""你是專業的法律案例分析助手。已載入{len(documents)}個起訴書案例的事實部分資料庫。

📚 案例事實資料庫內容：
{knowledge_text}

🔍 資料庫包含{len(documents)}個起訴書案例的事實部分，專注於：
- 事故經過和時間地點
- 當事人信息和過失認定
- 傷害類型和醫療情況
- 原始賠償金額和項目

這個專注於事實的資料庫能更精確地匹配相似案例，不受法條條文風格影響。

請基於上述事實資料庫進行案例匹配和分析。"""
        else:
            # 為Ollama優化的提示格式，包含明確的案例索引
            system_prompt = f"""你是專業的法律案例分析助手。已載入2995個起訴書案例的完整資料庫。

📚 案例資料庫內容：
{knowledge_text}

🔍 資料庫包含2995個完整起訴書案例，每個案例包含：
- 事實部分：事故經過和當事人信息
- 法條部分：適用的法律條文
- 賠償部分：具體的賠償項目和金額
- 結論部分：總結和利息計算

你可以準確檢索和分析這些案例，找出最相似的案例進行比較和參考。

請基於上述完整的案例資料庫回答問題。"""
    else:
        # 為transformers模型的提示格式
        system_prompt = f"""<|begin_of_text|>
<|start_header_id|>system<|end_header_id|>
你是專業的法律文件分析助手.請基於提供的起訴書內容準確回答問題.
起訴書內容包含事實,法條,賠償,結論四個部分.
請根據問題內容,從相關的起訴書中找出對應的資訊進行回答.<|eot_id|>
<|start_header_id|>user<|end_header_id|>
以下是起訴書內容:
{knowledge_text}

請基於上述起訴書內容回答問題:
Question: """
    
    # 執行KV-Encode
    t1 = time()
    kv_cache = preprocess_knowledge(system_prompt, model_name)
    t2 = time()
    
    logger.info(f"KV-Encode完成,耗時: {t2-t1:.2f}秒")
    
    # 保存緩存
    if output_path and model != "ollama":
        torch.save(kv_cache, output_path)
        logger.info(f"KV緩存已保存至: {output_path}")
    elif output_path and model == "ollama":
        # 為Ollama保存知識提示
        import json
        with open(output_path.replace('.pt', '.json'), 'w', encoding='utf-8') as f:
            json.dump({"knowledge_prompt": kv_cache}, f, ensure_ascii=False, indent=2)
        logger.info(f"知識提示已保存至: {output_path.replace('.pt', '.json')}")
    
    return kv_cache

def extract_key_facts(accident_facts: str, model_name: str = None):
    """
    第1階段：事實抽取和保護
    """
    import ollama
    
    extraction_prompt = f"""請從以下事故事實中精確抽取關鍵信息，保持原文不變：

{accident_facts}

請按以下格式提取，不可修改任何數字、時間、地點：

時間：[精確抽取原文中的時間]
地點：[精確抽取原文中的地點] 
車輛類型：[精確抽取車輛類型]
當事人：原告、被告
傷害類型：[精確抽取傷害描述]
醫療費用：[精確抽取金額]
車輛修復費：[精確抽取金額]
交通費：[精確抽取金額]
工作損失：[精確抽取金額]
精神慰撫金：[精確抽取金額]
總金額：[精確抽取總計金額]

注意：絕對不可更改、推測或修正任何數字和事實！"""

    try:
        response = ollama.generate(
            model=model_name,
            prompt=extraction_prompt,
            options={"temperature": 0.1}  # 低溫度確保精確性
        )
        return response['response'].strip()
    except Exception as e:
        logger.error(f"事實抽取失敗: {e}")
        return accident_facts

def find_similar_cases(accident_facts: str, extracted_facts: str, kv_cache, model_name: str = None):
    """
    第2階段：智能案例匹配
    """
    import ollama
    
    # 為Ollama構建包含知識的完整提示
    matching_prompt = f"""作為專業的法律案例分析師，你需要基於已載入的起訴書資料庫來找出相似案例。

{kv_cache}

現在請仔細分析資料庫中的案例，找出與以下事故事實最相似的3個具體案例：

【待分析事故】
事故事實：{accident_facts}

關鍵信息：{extracted_facts}

【分析要求】
請從資料庫的2995個案例中，根據以下標準找出最相似的案例：
1. 事故類型匹配（追撞/左轉/併排等）
2. 傷害類型相似（膝傷/擦傷等）  
3. 賠償項目相近（醫療費/車輛修復費/精神慰撫金）
4. 車輛類型相同或相近

請嚴格按照以下格式回答，必須給出具體的案例編號：

最相似案例1：
案例編號：[從1-2995中選擇具體數字]
相似度：[85%-95%]
相似原因：[詳細分析為什麼此案例最相似]

最相似案例2：
案例編號：[從1-2995中選擇具體數字]
相似度：[75%-90%]
相似原因：[詳細說明相似之處]

最相似案例3：
案例編號：[從1-2995中選擇具體數字]  
相似度：[70%-85%]
相似原因：[說明選擇理由]

注意：必須基於實際載入的案例資料庫進行分析，不可虛構案例編號。"""

    try:
        response = ollama.generate(
            model=model_name,
            prompt=matching_prompt,
            options={
                "temperature": 0.2,
                "top_p": 0.8,
                "max_tokens": 1000
            }
        )
        return response['response'].strip()
    except Exception as e:
        logger.error(f"案例匹配失敗: {e}")
        return "匹配失敗"

def generate_indictment_from_facts(accident_facts: str, kv_cache, model_name: str = None, use_rule_based_laws: bool = False) -> dict:
    """
    基於事故事實生成完整起訴書 (多階段CAG版本)
    
    Args:
        accident_facts: 事故事實描述
        kv_cache: KV緩存或知識提示
        model_name: 模型名稱
        use_rule_based_laws: 是否使用規則化法條生成
        
    Returns:
        完整的四段式起訴書字典
    """
    logger.info("開始多階段CAG生成起訴書...")
    
    # 第1階段：事實抽取和保護
    logger.info("第1階段：抽取並保護關鍵事實...")
    extracted_facts = extract_key_facts(accident_facts, model_name)
    logger.info(f"抽取的事實: {extracted_facts[:200]}...")
    
    # 第2階段：智能案例匹配
    logger.info("第2階段：匹配相似案例...")
    similar_cases = find_similar_cases(accident_facts, extracted_facts, kv_cache, model_name)
    logger.info(f"匹配的案例: {similar_cases[:200]}...")
    
    # 新增：規則化法條生成（如果啟用）
    rule_based_legal_section = None
    if use_rule_based_laws:
        logger.info("使用規則化法條生成...")
        rule_based_legal_section = generate_standard_laws(accident_facts)
        logger.info(f"規則化法條: {rule_based_legal_section[:100]}...")
    
    # 如果使用Ollama
    if model == "ollama":
        import ollama
        
        # 第3階段：約束生成提示
        logger.info("第3階段：基於匹配案例約束生成...")
        
        if use_rule_based_laws and rule_based_legal_section:
            # 使用規則化法條的生成提示
            generation_prompt = f"""你是專業的法律文件起草助手。請基於以下信息生成標準格式的起訴書，務必嚴格遵守格式和約束條件：

【原始用戶輸入 - 必須完全保留所有金額】
{accident_facts}

【抽取的關鍵事實】
{extracted_facts}

【匹配的相似案例參考】
{similar_cases}

【已準備的標準法條部分】
{rule_based_legal_section}

【絕對重要：金額保護規則】
⚠️ 從抽取的關鍵事實中找到的確切金額，必須一字不變地複製：
從抽取的關鍵事實可見：
- 醫療費用：190元 → 起訴書必須寫「190元」
- 車輛修復費：181,144元 → 起訴書必須寫「181,144元」
- 交通費：4,500元 → 起訴書必須寫「4,500元」
- 工作損失：33,000元 → 起訴書必須寫「33,000元」
- 精神慰撫金：99,000元 → 起訴書必須寫「99,000元」
- 總金額：317,834元 → 起訴書必須寫「317,834元」

❌ 嚴格禁止：
- 不可將181,144元改成10000元
- 不可將4,500元改成500元  
- 不可將33,000元改成2000元
- 不可將99,000元改成3000元
- 必須使用抽取事實中的確切數字

【嚴格約束規則】
1. 時間日期必須完全照抄原文
2. 地點名稱必須完全照抄原文  
3. 金額數字必須完全照抄原文，一個數字都不可更改
4. 當事人稱謂必須完全照抄原文
5. 傷害描述必須完全照抄原文

【標準格式要求】
請嚴格按照以下格式生成起訴書，並直接複製抽取的關鍵事實中的信息：

格式要求：請將【抽取的關鍵事實】中的具體信息填入相應位置
- 時間：從抽取事實中的"時間"直接複製
- 地點：從抽取事實中的"地點"直接複製  
- 傷害：從抽取事實中的"傷害類型"直接複製
- 金額：從抽取事實中的各項金額直接複製，不可修改

一、被告於【時間】，駕駛【車輛類型】在【地點】，因未保持安全距離，追撞原告駕駛之自用小客車。因被告之過失，致原告受有【傷害類型】等傷害，經醫師診斷需休養1個月，無法正常工作。

{rule_based_legal_section}

（一）醫療費用：【從抽取事實複製醫療費用】
原告因本事故受傷，支出醫療費用新台幣【醫療費用金額】。

（二）車輛修復費：【從抽取事實複製車輛修復費】
原告車輛因本事故受損，產生修復費用新台幣【車輛修復費金額】。

（三）交通費：【從抽取事實複製交通費】
原告因就醫及處理事故相關事宜，產生交通費用新台幣【交通費金額】。

（四）工作損失：【從抽取事實複製工作損失】
原告因本事故無法正常工作，造成工作損失新台幣【工作損失金額】。

（五）精神慰撫金：【從抽取事實複製精神慰撫金】
原告因被告過失行為，身心受創，請求精神慰撫金新台幣【精神慰撫金金額】。

（六）綜上所陳，被告應賠償原告之損害，包含醫療費用【醫療費用】、車輛修復費【車輛修復費】、交通費【交通費】、工作損失【工作損失】、精神慰撫金【精神慰撫金】，總計【從抽取事實複製總金額】，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。

【生成要求】
- 完全使用原始輸入的確切金額，絕不修改任何數字
- 法條部分請直接使用已提供的標準法條內容
- 賠償項目使用（一）（二）（三）格式
- 最後必須以「綜上所陳」開頭作為結論
- 不可使用任何markdown格式符號如**或##
- 絕對禁止將任何明確的金額改為0元或「尚無法確定」

請生成標準格式的起訴書："""
        else:
            # 原始的生成提示（模型生成法條）
            generation_prompt = f"""你是專業的法律文件起草助手。請基於以下信息生成標準格式的起訴書，務必嚴格遵守格式和約束條件：

【原始用戶輸入 - 必須完全保留所有金額】
{accident_facts}

【抽取的關鍵事實】
{extracted_facts}

【匹配的相似案例參考】
{similar_cases}

【絕對重要：金額保護規則】
⚠️ 從原始輸入中必須完全照抄的具體金額（絕不可改為0元或「尚無法確定」）：
- 如果原文明確寫出金額，起訴書必須完全照抄
- 絕對禁止將任何明確給出的金額改為0元或「尚無法確定」

【嚴格約束規則】
1. 時間日期必須完全照抄原文
2. 地點名稱必須完全照抄原文  
3. 金額數字必須完全照抄原文，一個數字都不可更改
4. 當事人稱謂必須完全照抄原文
5. 傷害描述必須完全照抄原文

【標準格式要求】
必須嚴格按照以下傳統法律文書格式生成，不可使用markdown符號：

一、[事實部分內容，包含事故經過、過失認定、傷害結果]

二、按「民法條文引用」......分別定有明文。查被告因上開侵權行為，致原告受有下列損害，依前揭規定，被告應負損害賠償責任：

（一）醫療費用：[從原始輸入照抄確切金額，絕不可寫0元]
詳細說明......

（二）車輛修復費：[從原始輸入照抄確切金額，絕不可寫0元]
詳細說明......

（三）交通費：[從原始輸入照抄確切金額，絕不可寫0元]
詳細說明......

（四）工作損失：[從原始輸入照抄確切金額，絕不可寫0元]
詳細說明......

（五）精神慰撫金：[從原始輸入照抄確切金額，絕不可寫0元]
詳細說明......

（六）綜上所陳，被告應賠償原告之損害，包含醫療費用○元、車輛修復費○元、交通費○元、工作損失○元、精神慰撫金○元，總計[從原始輸入照抄總金額]元，並自起訴狀副本送達翌日起至清償日止，按年息5%計算之利息。

【生成要求】
- 完全使用原始輸入的確切金額，絕不修改任何數字
- 法條引用使用完整條文內容
- 賠償項目使用（一）（二）（三）格式
- 最後必須以「綜上所陳」開頭作為結論
- 不可使用任何markdown格式符號如**或##
- 絕對禁止將任何明確的金額改為0元或「尚無法確定」

請生成標準格式的起訴書："""
        
        try:
            response = ollama.generate(
                model=model_name,
                prompt=generation_prompt,
                options={
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "max_tokens": 2000
                }
            )
            
            # 解析回應並結構化
            full_response = response['response'].strip()
            
            def parse_section(text, start_marker, end_marker=None):
                """解析特定段落"""
                if start_marker not in text:
                    return None
                
                start_idx = text.find(start_marker) + len(start_marker)
                if end_marker and end_marker in text[start_idx:]:
                    end_idx = text.find(end_marker, start_idx)
                    return text[start_idx:end_idx].strip()
                else:
                    return text[start_idx:].strip()
            
            # 提取各個段落 - 新的標準格式解析
            sections = {}
            
            # 由於新格式不使用「零、一、二、三、四」，需要重新解析整個響應
            # 新格式是標準法律文書格式，沒有明確分段標記
            
            # 提取事實部分（從「一、」開始到「二、」結束）
            facts = parse_section(full_response, "一、", "二、")
            if facts:
                sections["facts"] = facts
                sections["similar_cases"] = "格式已整合到完整起訴書中"
            else:
                sections["facts"] = "解析失敗"
                sections["similar_cases"] = "解析失敗"
            
            # 提取法條部分（從「二、」開始到第一個「（一）」結束）  
            legal_start = full_response.find("二、")
            if legal_start != -1:
                remaining_text = full_response[legal_start:]
                compensation_start = remaining_text.find("（一）")
                if compensation_start != -1:
                    legal_text = remaining_text[:compensation_start].strip()
                    sections["legal"] = legal_text
                else:
                    sections["legal"] = remaining_text.strip()
            else:
                sections["legal"] = "解析失敗"
            
            # 提取賠償部分（從「（一）」開始到「綜上所陳」結束）
            compensation_start = full_response.find("（一）")
            conclusion_start = full_response.find("綜上所陳")
            
            if compensation_start != -1 and conclusion_start != -1:
                compensation_text = full_response[compensation_start:conclusion_start].strip()
                sections["compensation"] = compensation_text
            elif compensation_start != -1:
                sections["compensation"] = full_response[compensation_start:].strip()
            else:
                sections["compensation"] = "解析失敗"
            
            # 提取結論部分（從「綜上所陳」開始到結尾）
            if conclusion_start != -1:
                conclusion_text = full_response[conclusion_start:].strip()
                sections["conclusion"] = conclusion_text
            else:
                sections["conclusion"] = full_response
            
            return {
                "similar_cases": sections.get("similar_cases", "未明確指出相似案例"),
                "facts_section": sections.get("facts", ""),
                "legal_section": sections.get("legal", ""),
                "compensation_section": sections.get("compensation", ""),
                "conclusion_section": sections.get("conclusion", ""),
                "full_indictment": full_response
            }
            
        except Exception as e:
            logger.error(f"Ollama起訴書生成失敗: {e}")
            return {
                "similar_cases": f"生成失敗: {str(e)}",
                "facts_section": f"生成失敗: {str(e)}",
                "legal_section": f"生成失敗: {str(e)}", 
                "compensation_section": f"生成失敗: {str(e)}",
                "conclusion_section": f"生成失敗: {str(e)}",
                "full_indictment": f"生成失敗: {str(e)}"
            }
    
    # 使用transformers模型的真正KV-cache
    try:
        question_prompt = f"""基於上述起訴書案例,請根據以下事故事實生成完整的起訴書內容:

事故事實:{accident_facts}

請生成四個部分:
一,事實部分:
二,法條部分:
三,賠償部分:
四,結論部分:(以"及自起訴狀繕本送達翌日起至清償日止,按年息5%計算之利息."結束)

起訴書內容:"""

        # 兼容不同模型結構
        if hasattr(model, 'model') and hasattr(model.model, 'embed_tokens'):
            embed_device = model.model.embed_tokens.weight.device
        elif hasattr(model, 'transformer') and hasattr(model.transformer, 'wte'):
            embed_device = model.transformer.wte.weight.device
        else:
            embed_device = next(model.parameters()).device
        
        input_ids = tokenizer.encode(question_prompt, return_tensors="pt").to(embed_device)
        
        # 檢查kv_cache類型
        if isinstance(kv_cache, str):
            # 如果是字符串,說明KV-cache建立失敗,回退到普通生成
            logger.warning("KV-cache是字符串,回退到普通文本生成")
            full_prompt = kv_cache + "\n\n" + question_prompt
            input_ids = tokenizer.encode(full_prompt, return_tensors="pt", max_length=2048, truncation=True).to(embed_device)
            
            with torch.no_grad():
                outputs = model.generate(
                    input_ids,
                    max_new_tokens=500,
                    do_sample=True,
                    temperature=0.3,
                    pad_token_id=tokenizer.eos_token_id,
                    use_cache=True
                )
        else:
            # 使用真正的KV-cache
            with torch.no_grad():
                outputs = model.generate(
                    input_ids,
                    past_key_values=kv_cache,
                    max_new_tokens=1000,
                    do_sample=True,
                    temperature=0.3,
                    pad_token_id=tokenizer.eos_token_id,
                    use_cache=True
                )
        
        # 解碼回答(只取新生成的部分)
        full_response = tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True).strip()
        
        # 解析回應並結構化
        sections = {}
        if "一,事實部分:" in full_response:
            parts = full_response.split("一,事實部分:")[1]
            if "二,法條部分:" in parts:
                sections["facts"] = parts.split("二,法條部分:")[0].strip()
                parts = parts.split("二,法條部分:")[1]
                if "三,賠償部分:" in parts:
                    sections["legal"] = parts.split("三,賠償部分:")[0].strip()
                    parts = parts.split("三,賠償部分:")[1]
                    if "四,結論部分:" in parts:
                        sections["compensation"] = parts.split("四,結論部分:")[0].strip()
                        sections["conclusion"] = parts.split("四,結論部分:")[1].strip()
        
        # 如果解析失敗,返回完整回應
        if not sections:
            sections = {
                "facts": "解析失敗",
                "legal": "解析失敗", 
                "compensation": "解析失敗",
                "conclusion": full_response
            }
        
        return {
            "similar_cases": sections.get("similar_cases", "未明確指出相似案例"),
            "facts_section": sections.get("facts", ""),
            "legal_section": sections.get("legal", ""),
            "compensation_section": sections.get("compensation", ""),
            "conclusion_section": sections.get("conclusion", ""),
            "full_indictment": full_response
        }
        
    except Exception as e:
        logger.error(f"Transformers起訴書生成失敗: {e}")
        return {
            "similar_cases": f"生成失敗: {str(e)}",
            "facts_section": f"生成失敗: {str(e)}",
            "legal_section": f"生成失敗: {str(e)}", 
            "compensation_section": f"生成失敗: {str(e)}",
            "conclusion_section": f"生成失敗: {str(e)}",
            "full_indictment": f"生成失敗: {str(e)}"
        }

def generate_response(question: str, kv_cache, max_new_tokens: int = 300, model_name: str = None) -> str:
    """
    使用KV緩存生成回答
    
    Args:
        question: 問題
        kv_cache: KV緩存或知識提示
        max_new_tokens: 最大新token數
        model_name: 模型名稱
        
    Returns:
        回答文本
    """
    # 如果使用Ollama
    if model == "ollama":
        import ollama
        
        # 組合完整的提示
        full_prompt = f"{kv_cache}\n\n問題: {question}\n\n回答:"
        
        try:
            response = ollama.generate(
                model=model_name,
                prompt=full_prompt,
                options={
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": max_new_tokens
                }
            )
            return response['response'].strip()
        except Exception as e:
            logger.error(f"Ollama生成失敗: {e}")
            return f"生成失敗: {str(e)}"
    
    # 使用transformers模型
    question_prompt = f"{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
    
    # 兼容不同模型結構
    if hasattr(model, 'model') and hasattr(model.model, 'embed_tokens'):
        # Llama style
        embed_device = model.model.embed_tokens.weight.device
    elif hasattr(model, 'transformer') and hasattr(model.transformer, 'wte'):
        # GPT style (DialoGPT)
        embed_device = model.transformer.wte.weight.device
    else:
        # Fallback to model device
        embed_device = next(model.parameters()).device
    
    input_ids = tokenizer.encode(question_prompt, return_tensors="pt").to(embed_device)
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            past_key_values=kv_cache,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
            use_cache=True
        )
    
    # 解碼回答(只取新生成的部分)
    response = tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)
    return response.strip()

def get_user_input():
    """取得使用者輸入的參數"""
    print("=== 起訴書CAG處理系統 ===")
    print("請選擇運行模式:")
    print("1. 問答模式(預設)- 基於起訴書資料回答問題")
    print("2. 生成模式 - 基於事故事實生成起訴書")
    
    while True:
        mode_choice = input("選擇模式 [1]: ").strip()
        if not mode_choice or mode_choice == "1":
            generate_mode = False
            print("  → 使用問答模式")
            break
        elif mode_choice == "2":
            generate_mode = True
            print("  → 使用生成模式")
            break
        else:
            print("請輸入有效的選項!")
    
    if generate_mode:
        # 生成模式的參數
        print("\n=== 起訴書生成模式 ===")
        
        # Excel檔案路徑
        excel_path = input("Excel檔案路徑 [整合_起訴書_2995_CAG用.xlsx]: ").strip()
        if not excel_path:
            excel_path = "整合_起訴書_2995_CAG用.xlsx"
        
        # 事故事實描述
        print("\n請輸入事故事實描述(可以多行輸入,輸入'END'結束):")
        accident_facts_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            accident_facts_lines.append(line)
        accident_facts = '\n'.join(accident_facts_lines)
        
        if not accident_facts.strip():
            accident_facts = "被告於某日駕駛車輛,因疏失與原告發生碰撞,致原告受傷,請求損害賠償."
            print(f"  → 使用預設事故描述")
        
        return {
            'excel_path': excel_path,
            'max_knowledge': None,  # 生成模式使用全部資料
            'max_questions': None,
            'test_questions': 0,
            'model_name': 'gemma3:27b',
            'use_ollama': True,
            'output_dir': './indictment_generation_results',
            'cache_path': None,
            'generate_mode': True,
            'accident_facts': accident_facts
        }
    
    # 問答模式的參數
    print("\n=== 問答模式 ===")
    
    # Excel檔案路徑
    excel_path = input("Excel檔案路徑 [整合_起訴書_2995_CAG用.xlsx]: ").strip()
    if not excel_path:
        excel_path = "整合_起訴書_2995_CAG用.xlsx"
    
    # 最大起訴書數量
    while True:
        max_knowledge_input = input("要處理幾份起訴書?[預設: 全部2995份]: ").strip()
        if not max_knowledge_input:
            max_knowledge = None
            print("  → 將處理全部2995份起訴書")
            break
        try:
            max_knowledge = int(max_knowledge_input)
            if max_knowledge <= 0:
                print("請輸入正數!")
                continue
            print(f"  → 將處理 {max_knowledge} 份起訴書")
            break
        except ValueError:
            print("請輸入有效的數字!")
    
    # 最大問題數量
    while True:
        max_questions_input = input("要生成幾個問答對?[預設: 每份起訴書15個]: ").strip()
        if not max_questions_input:
            max_questions = None
            print("  → 將為每份起訴書生成15個問答對")
            break
        try:
            max_questions = int(max_questions_input)
            if max_questions <= 0:
                print("請輸入正數!")
                continue
            print(f"  → 將生成 {max_questions} 個問答對")
            break
        except ValueError:
            print("請輸入有效的數字!")
    
    # 測試問題數量
    while True:
        test_questions_input = input("要測試幾個問題?[預設: 10]: ").strip()
        if not test_questions_input:
            test_questions = 10
            print("  → 將測試10個問題")
            break
        try:
            test_questions = int(test_questions_input)
            if test_questions <= 0:
                print("請輸入正數!")
                continue
            print(f"  → 將測試 {test_questions} 個問題")
            break
        except ValueError:
            print("請輸入有效的數字!")
    
    # 模型選擇
    print("\n可用的模型:")
    print("1. gemma3:27b (Ollama)")
    print("2. kenneth85/llama-3-taiwan:8b-instruct-dpo-q4_K_M (Ollama)")
    print("3. microsoft/DialoGPT-medium (Transformers)")
    print("4. 自定義模型")
    
    while True:
        model_choice = input("選擇模型 [1]: ").strip()
        if not model_choice or model_choice == "1":
            model_name = "gemma3:27b"
            use_ollama = True
            print("  → 使用 Gemma3:27B (Ollama)")
            break
        elif model_choice == "2":
            model_name = "kenneth85/llama-3-taiwan:8b-instruct-dpo-q4_K_M"
            use_ollama = True
            print("  → 使用 台灣Llama (Ollama)")
            break
        elif model_choice == "3":
            model_name = "microsoft/DialoGPT-medium"
            use_ollama = False
            print("  → 使用 DialoGPT (Transformers)")
            break
        elif model_choice == "4":
            model_name = input("請輸入自定義模型名稱: ").strip()
            if not model_name:
                print("模型名稱不能為空!")
                continue
            ollama_choice = input("使用Ollama?[y/N]: ").strip().lower()
            use_ollama = ollama_choice in ['y', 'yes']
            print(f"  → 使用 {model_name} ({'Ollama' if use_ollama else 'Transformers'})")
            break
        else:
            print("請輸入有效的選項!")
    
    # 輸出目錄
    output_dir = input("輸出目錄 [./indictment_results]: ").strip()
    if not output_dir:
        output_dir = "./indictment_results"
    print(f"  → 結果將保存到: {output_dir}")
    
    print("\n=== 參數確認 ===")
    print(f"Excel檔案: {excel_path}")
    print(f"處理起訴書數量: {'全部' if max_knowledge is None else max_knowledge}")
    print(f"問答對數量: {'自動計算' if max_questions is None else max_questions}")
    print(f"測試問題數量: {test_questions}")
    print(f"模型: {model_name} ({'Ollama' if use_ollama else 'Transformers'})")
    print(f"輸出目錄: {output_dir}")
    
    confirm = input("\n確認開始處理?[Y/n]: ").strip().lower()
    if confirm and confirm not in ['y', 'yes']:
        print("已取消處理")
        exit(0)
    
    return {
        'excel_path': excel_path,
        'max_knowledge': max_knowledge,
        'max_questions': max_questions,
        'test_questions': test_questions,
        'model_name': model_name,
        'use_ollama': use_ollama,
        'output_dir': output_dir,
        'cache_path': None
    }

def main():
    parser = argparse.ArgumentParser(description="起訴書CAG處理腳本")
    parser.add_argument("--excel_path", type=str, help="Excel檔案路徑")
    parser.add_argument("--max_knowledge", type=int, default=None, help="最大起訴書數量")
    parser.add_argument("--max_questions", type=int, default=100, help="最大問題數量")
    parser.add_argument("--model_name", type=str, default="microsoft/DialoGPT-medium", help="模型名稱")
    parser.add_argument("--output_dir", type=str, default="./indictment_results", help="輸出目錄")
    parser.add_argument("--cache_path", type=str, default=None, help="KV緩存保存路徑")
    parser.add_argument("--test_questions", type=int, default=10, help="測試問題數量")
    parser.add_argument("--use_ollama", action="store_true", help="使用Ollama模型")
    parser.add_argument("--interactive", action="store_true", help="互動式輸入模式")
    parser.add_argument("--generate_mode", action="store_true", help="起訴書生成模式")
    parser.add_argument("--accident_facts", type=str, default=None, help="事故事實描述")
    parser.add_argument("--facts_only", action="store_true", help="使用純事實匹配模式（優化KV-Cache）")
    parser.add_argument("--use_rule_based_laws", action="store_true", help="使用規則化法條生成")
    
    args = parser.parse_args()
    
    # 如果沒有提供excel_path參數,或使用interactive模式,則進入互動式輸入
    if not args.excel_path or args.interactive:
        user_params = get_user_input()
        # 將用戶輸入的參數轉換為args格式
        for key, value in user_params.items():
            setattr(args, key, value)
    
    # 創建輸出目錄
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 載入模型
    load_model(args.model_name, args.use_ollama)
    
    # 讀取Excel資料（檢查是否使用facts_only模式）
    facts_only_mode = getattr(args, 'facts_only', False)
    text_list, case_data = load_indictment_excel(args.excel_path, args.max_knowledge, facts_only_mode)
    
    if not text_list:
        logger.error("無法讀取Excel資料,程式結束")
        return
    
    # 生成問答對(生成模式時跳過)
    questions, answers = [], []
    if not getattr(args, 'generate_mode', False):
        questions, answers = generate_legal_qa_pairs(case_data, args.max_questions)
        
        # 保存問答對
        qa_data = [{"question": q, "answer": a} for q, a in zip(questions, answers)]
        with open(os.path.join(args.output_dir, "qa_pairs.json"), "w", encoding="utf-8") as f:
            json.dump(qa_data, f, ensure_ascii=False, indent=2)
    
    # 準備KV緩存
    cache_path = args.cache_path or os.path.join(args.output_dir, "indictment_kv_cache.pt")
    kv_cache = prepare_indictment_kv_cache(text_list, cache_path, args.model_name, facts_only_mode)
    
    # 檢查是否為生成模式
    if getattr(args, 'generate_mode', False):
        logger.info("=== 起訴書生成模式 ===")
        
        # 生成起訴書（檢查是否使用規則化法條）
        use_rule_based = getattr(args, 'use_rule_based_laws', False)
        logger.info("開始生成起訴書...")
        t1 = time()
        generated_indictment = generate_indictment_from_facts(args.accident_facts, kv_cache, args.model_name, use_rule_based)
        t2 = time()
        
        logger.info(f"起訴書生成完成,耗時: {t2-t1:.2f}秒")
        
        # 保存生成結果
        with open(os.path.join(args.output_dir, "generated_indictment.json"), "w", encoding="utf-8") as f:
            json.dump({
                "input_facts": args.accident_facts,
                "generated_indictment": generated_indictment,
                "generation_time": t2 - t1
            }, f, ensure_ascii=False, indent=2)
        
        # 保存格式化的起訴書
        generation_time = t2 - t1
        formatted_indictment = "=== CAG生成的完整起訴書 ===" + "\n\n"
        formatted_indictment += "輸入事故事實:\n" + str(args.accident_facts) + "\n\n"
        formatted_indictment += "生成結果:\n\n"
        formatted_indictment += "零,參考的相似案例:\n" + generated_indictment.get('similar_cases', '未明確指出相似案例') + "\n\n"
        formatted_indictment += "一,事實部分:\n" + generated_indictment['facts_section'] + "\n\n"
        formatted_indictment += "二,法條部分:\n" + generated_indictment['legal_section'] + "\n\n"
        formatted_indictment += "三,賠償部分:\n" + generated_indictment['compensation_section'] + "\n\n"
        formatted_indictment += "四,結論部分:\n" + generated_indictment['conclusion_section'] + "\n\n"
        formatted_indictment += "=== 完整起訴書 ===\n" + generated_indictment['full_indictment'] + "\n\n"
        formatted_indictment += f"生成時間: {generation_time:.2f}秒"
        
        with open(os.path.join(args.output_dir, "formatted_indictment.txt"), "w", encoding="utf-8") as f:
            f.write(formatted_indictment)
        
        logger.info(f"起訴書已保存至: {args.output_dir}")
        logger.info(f"生成時間: {(t2-t1):.2f}秒")
        
        # 顯示生成結果摘要
        print("\n" + "="*50)
        print("起訴書生成完成!")
        print("="*50)
        print(f"事實部分長度: {len(generated_indictment['facts_section'])} 字符")
        print(f"法條部分長度: {len(generated_indictment['legal_section'])} 字符")
        print(f"賠償部分長度: {len(generated_indictment['compensation_section'])} 字符")
        print(f"結論部分長度: {len(generated_indictment['conclusion_section'])} 字符")
        print(f"生成時間: {(t2-t1):.2f}秒")
        
        return
    
    # 原本的問答測試模式
    if not questions:
        logger.info("未生成問答對,跳過測試")
        return
        
    # 測試系統
    logger.info(f"開始測試系統,使用前 {args.test_questions} 個問題...")
    
    test_results = []
    for i in range(min(args.test_questions, len(questions))):
        question = questions[i]
        expected_answer = answers[i]
        
        logger.info(f"測試問題 {i+1}: {question}")
        
        t1 = time()
        generated_answer = generate_response(question, kv_cache, 300, args.model_name)
        t2 = time()
        
        result = {
            "question": question,
            "expected_answer": expected_answer,
            "generated_answer": generated_answer,
            "response_time": t2 - t1
        }
        test_results.append(result)
        
        logger.info(f"生成答案: {generated_answer[:100]}...")
        logger.info(f"回答時間: {t2-t1:.2f}秒")
        logger.info("-" * 50)
    
    # 保存測試結果
    with open(os.path.join(args.output_dir, "test_results.json"), "w", encoding="utf-8") as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"處理完成!結果保存在: {args.output_dir}")
    
    # 顯示統計資訊
    if test_results:
        avg_response_time = sum(r["response_time"] for r in test_results) / len(test_results)
        logger.info(f"平均回答時間: {avg_response_time:.2f}秒")
    logger.info(f"總問答對數: {len(questions)}")
    
    if model == "ollama":
        logger.info(f"知識提示大小: {len(kv_cache)} 字符")
        logger.info("注意: 使用Ollama時,這不是真正的KV-cache,而是提示預處理")
    else:
        logger.info(f"KV緩存大小: {kv_cache.key_cache[0].shape[-2]} tokens")

if __name__ == "__main__":
    main()