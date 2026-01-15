from sentence_transformers import SentenceTransformer, util, CrossEncoder
import torch
import sys
import os
from pathlib import Path

# QuestionGenerator import를 위한 경로 설정
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from generator import QuestionGenerator

class Evaluator:
    def __init__(self):
        # 1. 유사도 평가 모델 (Bi-Encoder: 빠름)
        self.sts_model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
        
        # 2. 논리적 일관성 평가 모델 (Cross-Encoder: 정확함, KLUE-NLI 기반)
        try:
            self.nli_model = CrossEncoder('klue/roberta-base-nli')
        except:
            self.nli_model = None
            
        # 3. 질문/피드백 생성기
        self.generator = QuestionGenerator()

    def evaluate_answer(self, user_answer: str, reference_text: str):
        """
        사용자 답변을 다각도로 평가합니다.
        1. Semantic Similarity (STS)
        2. Logical Entailment (NLI)
        """
        # STS 점수 계산
        sts_score = self._get_sts_score(user_answer, reference_text)
        
        # NLI 상태 분석 (함의, 중립, 모순)
        nli_label, nli_confidence = self._get_nli_status(user_answer, reference_text)
        
        # 종합 판단
        is_passed = (sts_score > 0.6) and (nli_label != "contradiction")
        
        # 평가 결과 딕셔너리
        result = {
            "sts_score": sts_score,
            "nli_label": nli_label,
            "nli_confidence": nli_confidence,
            "is_passed": is_passed,
            "user_answer": user_answer  # [중요] generator 전달용
        }
        
        # 피드백 생성 (Generator 위임)
        # reference_text를 node 정보로 활용
        node = {"text": reference_text}
        result["feedback"] = self.generator.generate_feedback_question(result, node=node)
        
        return result

    def _get_sts_score(self, text1: str, text2: str) -> float:
        embeddings = self.sts_model.encode([text1, text2])
        score = util.cos_sim(embeddings[0], embeddings[1])
        return float(score.item())

    def _get_nli_status(self, answer: str, context: str):
        if not self.nli_model:
            return "neutral", 0.0
        
        # KLUE NLI Labels: 0: entailment, 1: neutral, 2: contradiction
        scores = self.nli_model.predict([(context, answer)])
        label_id = torch.argmax(torch.tensor(scores)).item()
        labels = ["entailment", "neutral", "contradiction"]
        
        return labels[label_id], float(torch.softmax(torch.tensor(scores), dim=1)[0][label_id].item())

