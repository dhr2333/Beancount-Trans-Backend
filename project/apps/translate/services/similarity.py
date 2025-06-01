import spacy
import torch
import logging
from pathlib import Path
from typing import List, Dict
from transformers import BertTokenizer, BertModel
from openai import OpenAI


class SimilarityModel:
    """抽象基类，定义相似度计算接口"""
    def calculate_similarity(self, text: str, candidates: List[str]) -> str:
        raise NotImplementedError


class BertSimilarity(SimilarityModel):
    """BERT相似度计算实现"""
    _tokenizer = None
    _model = None
    _embedding_cache: Dict[str, torch.Tensor] = {}

    @classmethod
    def load_model(cls):
        if cls._model is None:
            local_model_path = Path(__file__).parent.parent.parent.parent.parent / "pretrained_models" / "bert-base-chinese"
            try:
                cls._tokenizer = BertTokenizer.from_pretrained(local_model_path)
                cls._model = BertModel.from_pretrained(local_model_path)
            except OSError:
                cls._tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
                cls._model = BertModel.from_pretrained('bert-base-chinese')
            cls._model.eval()
        return cls._tokenizer, cls._model

    def _get_embedding(self, text: str) -> torch.Tensor:
        """获取文本嵌入，带缓存"""
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        tokenizer, model = self.load_model()
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=64)
        with torch.no_grad():
            outputs = model(**inputs)
        embedding = outputs.last_hidden_state[:,0,:]
        self._embedding_cache[text] = embedding
        return embedding

    def calculate_similarity(self, text: str, candidates: List[str]) -> Dict[str, float]:
        """返回每个候选词的相似度分数及最高分条目"""
        text_embed = self._get_embedding(text)
        scores = {}

        for candidate in candidates:
            cand_embed = self._get_embedding(candidate)
            similarity = torch.cosine_similarity(text_embed, cand_embed, dim=1)
            scores[candidate] = similarity.item()

        best_match = max(scores.items(), key=lambda x: x[1])[0]
        return {"best_match": best_match, "scores": scores}


class SpacySimilarity(SimilarityModel):
    """spaCy相似度计算实现"""
    _nlp = None

    @classmethod
    def load_model(cls):
        if cls._nlp is None:
            cls._nlp = spacy.load("zh_core_web_md", exclude=["parser", "ner", "lemmatizer"])
        return cls._nlp

    def calculate_similarity(self, text: str, candidates: List[str]) -> Dict[str, float]:
        """返回每个候选词的相似度分数及最高分条目"""
        nlp = self.load_model()
        doc = nlp(text)
        scores = {}

        for candidate in candidates:
            cand_doc = nlp(candidate)
            scores[candidate] = doc.similarity(cand_doc)

        best_match = max(scores.items(), key=lambda x: x[1])[0]
        return {"best_match": best_match, "scores": scores}


class DeepSeekSimilarity(SimilarityModel):
    """DeepSeek API相似度计算实现"""
    def __init__(self, api_key: str, enable_realtime: bool = True):
        self.api_key = api_key
        self.enable_realtime = enable_realtime
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def calculate_similarity(self, text: str, candidates: List[str]) -> dict:
        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )

        prompt = f"""请从以下候选列表中选择最匹配文本的条目：
        文本内容：{text}
        候选列表：{", ".join(candidates)}
        只需返回最匹配的候选值，不要任何解释"""

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            result = response.choices[0].message.content.strip()
            best_match = result if result in candidates else candidates[0]
            # DeepSeek没有分数，全部置为None或0
            scores = {c: (1.0 if c == best_match else 0.0) for c in candidates}
            return {"best_match": best_match, "scores": scores}
        except Exception as e:
            raise ValueError(f"DeepSeek调用失败，请检查API密钥是否正确")
