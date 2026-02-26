"""
用 Gemma3:27b 重新提取3062筆結論的金額
解決多名原告時金額提取錯誤的問題

處理：
1. 單一原告總計金額(不含肇事責任)
2. 單一原告總計金額(不含肇事責任且已根據事實扣除費用)
3. 多名原告總計金額(不含肇事責任)
4. 多名原告總計金額(不含肇事責任且已根據事實扣除費用)
"""

import pandas as pd
import ollama
import logging
import re
from tqdm import tqdm
import time
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()


class ConclusionAmountExtractor:
    """用 Gemma3 提取結論中的4種金額"""

    def __init__(self, model_name='gemma3:27b'):
        self.model_name = model_name
        logger.info(f"✅ 使用模型: {model_name}")

    def extract_amounts_with_gemma(self, conclusion_text):
        """用 Gemma 從結論文本中提取4種金額"""

        prompt = f"""你是一個法律文書分析專家。請從以下判決結論文字中，提取4種金額。

結論文字：
{conclusion_text[:1000]}

請仔細分析這段結論，並提取以下4種金額（如果沒有該種金額，請回答"無"）：

1. 單一原告總計金額(不含肇事責任):
   - 指單一原告請求的總金額
   - 不包含肇事責任比例的扣除
   - 不包含已支付保險金、已領費用等的扣除

2. 單一原告總計金額(不含肇事責任且已根據事實扣除費用):
   - 指單一原告請求的總金額
   - 不包含肇事責任比例的扣除
   - 但已經扣除了保險金、已付醫療費等實際費用

3. 多名原告總計金額(不含肇事責任):
   - 如果有多名原告，這是所有原告請求的加總
   - 不包含肇事責任比例的扣除
   - 不包含已支付保險金、已領費用等的扣除

4. 多名原告總計金額(不含肇事責任且已根據事實扣除費用):
   - 如果有多名原告，這是所有原告請求的加總
   - 不包含肇事責任比例的扣除
   - 但已經扣除了保險金、已付醫療費等實際費用

請以JSON格式回答，格式如下：
{{
    "single_plaintiff_raw": "金額或無",
    "single_plaintiff_deducted": "金額或無",
    "multiple_plaintiffs_raw": "金額或無",
    "multiple_plaintiffs_deducted": "金額或無"
}}

注意：
- 金額請只寫數字，不要加「元」「新台幣」等文字
- 如果文中沒有明確提到該種金額，請寫"無"
- 如果只有單一原告，多名原告的欄位應該是"無"
- 如果只有多名原告，單一原告的欄位應該是"無"

請只回答JSON，不要有其他說明文字。
"""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'temperature': 0.1,
                    'num_predict': 200
                }
            )

            response_text = response['message']['content'].strip()

            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                amounts = json.loads(json_str)

                # 清理結果
                cleaned = {}
                for key, value in amounts.items():
                    if value in ["無", "None", None, ""]:
                        cleaned[key] = None
                    else:
                        # 提取純數字
                        number_match = re.search(r'[\d,]+', str(value))
                        if number_match:
                            cleaned[key] = number_match.group().replace(',', '')
                        else:
                            cleaned[key] = None

                return cleaned
            else:
                logger.warning(f"無法解析JSON: {response_text[:100]}")
                return self._get_empty_result()

        except Exception as e:
            logger.error(f"Gemma提取失敗: {e}")
            return self._get_empty_result()

    def _get_empty_result(self):
        """返回空結果"""
        return {
            'single_plaintiff_raw': None,
            'single_plaintiff_deducted': None,
            'multiple_plaintiffs_raw': None,
            'multiple_plaintiffs_deducted': None
        }

    def process_excel(self, input_file, output_file):
        """處理整個Excel檔案"""
        logger.info(f"📂 讀取檔案: {input_file}")

        # ✅ 修正：讀取「3062結論」工作表
        df = pd.read_excel(input_file, sheet_name="3062結論", engine='openpyxl')
        total = len(df)

        logger.info(f"📊 共 {total} 筆資料需要處理")

        # 檢查是否有「結論」欄位
        if '結論' not in df.columns:
            logger.error("❌ Excel中沒有「結論」欄位！")
            return

        logger.info("✅ 找到「結論」欄位，開始處理...")

        # 批次處理
        for i in tqdm(range(total), desc="提取金額"):
            conclusion = df.at[i, '結論']

            # 跳過空值
            if pd.isna(conclusion) or str(conclusion).strip() == '':
                continue

            # 用 Gemma 提取金額
            amounts = self.extract_amounts_with_gemma(str(conclusion))

            # ✅ 覆蓋更新這4個欄位（不是新增）
            df.at[i, '單一原告總計金額(不含肇事責任)'] = amounts['single_plaintiff_raw']
            df.at[i, '單一原告總計金額(不含肇事責任且已根據事實扣除費用)'] = amounts['single_plaintiff_deducted']
            df.at[i, '多名原告總計金額(不含肇事責任)'] = amounts['multiple_plaintiffs_raw']
            df.at[i, '多名原告總計金額(不含肇事責任且已根據事實扣除費用)'] = amounts['multiple_plaintiffs_deducted']

            # 每處理10筆休息一下
            if (i + 1) % 10 == 0:
                time.sleep(1)

                # 定期儲存進度
                if (i + 1) % 100 == 0:
                    temp_file = output_file.replace('.xlsx', f'_progress_{i+1}.xlsx')
                    # ✅ 儲存時使用相同的工作表名稱
                    df.to_excel(temp_file, sheet_name="3062結論", index=False, engine='openpyxl')
                    logger.info(f"💾 進度儲存: {i+1}/{total}")

        # 最終儲存
        logger.info(f"💾 儲存最終結果到: {output_file}")
        df.to_excel(output_file, sheet_name="3062結論", index=False, engine='openpyxl')

        # 統計結果
        logger.info("📊 提取結果統計：")
        logger.info(f"  單一原告(原始): {df['單一原告總計金額(不含肇事責任)'].notna().sum()} 筆")
        logger.info(f"  單一原告(扣除): {df['單一原告總計金額(不含肇事責任且已根據事實扣除費用)'].notna().sum()} 筆")
        logger.info(f"  多名原告(原始): {df['多名原告總計金額(不含肇事責任)'].notna().sum()} 筆")
        logger.info(f"  多名原告(扣除): {df['多名原告總計金額(不含肇事責任且已根據事實扣除費用)'].notna().sum()} 筆")

        logger.info("✅ 處理完成！")


if __name__ == "__main__":
    import sys

    print("🔧 結論金額重新提取工具")
    print("="*70)

    input_file = "09_輸入輸出資料/整合_起訴書_四段(FINAL)_3062.xlsx"
    output_file = "09_輸入輸出資料/整合_起訴書_四段(FINAL)_3062_金額修正版.xlsx"

    extractor = ConclusionAmountExtractor()

    print(f"📂 輸入檔案: {input_file}")
    print(f"📂 工作表: 3062結論")
    print(f"📂 輸出檔案: {output_file}")
    print(f"\n⏱️  預估時間: 約2-3小時（3062筆 × 3秒/筆）")
    print(f"💡 建議: 睡覺時執行，會自動每100筆儲存進度")
    print("="*70)

    confirm = input("\n確定要開始嗎？(y/n): ")
    if confirm.lower() == 'y':
        extractor.process_excel(input_file, output_file)
    else:
        print("❌ 已取消")
