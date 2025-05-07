import re
from typing import List

class TextProcessor:
    @staticmethod
    def extract_law_numbers(law_text: str) -> List[str]:
        """
        從輸入文本中提取所有法條號碼。
        例如：傳入 "依據第184條、第191-2條及第195條"，返回 ["184", "191-2", "195"]
        """
        pattern = r"第\s*(\d+(?:-\d+)?)\s*條"
        matches = re.findall(pattern, law_text)
        return matches

    @staticmethod
    def classify_chunk(chunk: str) -> str:
        """
        根據文本內容，將區塊分類為:
          - 'fact'：若文本描述事故發生的經過、背景或事實緣由。
          - 'injuries'：若文本描述受傷情形或醫療後果。
          - 'compensation'：若文本涉及賠償請求、費用、損失等。
        此處採用簡單關鍵字匹配，如有需要可進一步整合 ML 模型進行分類。
        """
        chunk_lower = chunk.lower()
        if any(keyword in chunk_lower for keyword in ["事故", "緣由", "發生", "車禍", "撞"]):
            return "fact"
        elif any(keyword in chunk_lower for keyword in ["受傷", "醫療", "治療", "手術", "傷勢"]):
            return "injuries"
        elif any(keyword in chunk_lower for keyword in ["賠償", "損失", "費用", "慰撫金"]):
            return "compensation"
        else:
            # 無法明確分類時預設為事實描述
            return "fact"

    @staticmethod
    def clean_text(text: str) -> str:
        """
        清洗文本：移除多餘空白與換行，並回傳處理後的文本。
        """
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """
        將文本根據標點符號或換行分割成句子列表。
        """
        sentences = re.split(r"[。！？\n]", text)
        return [sentence.strip() for sentence in sentences if sentence.strip()]

# 測試用範例
if __name__ == "__main__":
    sample_text = "依據第184條、第191-2條及第195條，原告因車禍受傷需請求賠償。"
    print("提取法條號碼:", TextProcessor.extract_law_numbers(sample_text))
    
    sample_chunk = "被告於民國105年4月12日發生車禍，未注意前車狀況導致碰撞。"
    print("分類結果:", TextProcessor.classify_chunk(sample_chunk))
    
    messy_text = "  這是一段   測試文本。\n\n有多餘空白  與換行。"
    print("清洗後文本:", TextProcessor.clean_text(messy_text))
    
    long_text = "第一句。第二句！第三句？第四句\n第五句。"
    print("分句結果:", TextProcessor.split_into_sentences(long_text))
