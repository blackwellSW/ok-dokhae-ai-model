from sentence_transformers import SentenceTransformer, util, CrossEncoder
import torch

class Evaluator:
    def __init__(self):
        # 1. 유사도 평가 모델 (Bi-Encoder: 빠름)
        self.sts_model = SentenceTransformer('snunlp/KR-SBERT-V40-KRE-STS')
        
        # 2. 논리적 일관성 평가 모델 (Cross-Encoder: 정확함, KLUE-NLI 기반)
        # 사용 가능한 적절한 공개 모델이 없을 경우 대비하여 try-except 구성
        try:
            self.nli_model = CrossEncoder('klue/roberta-base-nli')
        except:
            self.nli_model = None

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
        # - 유사도가 높고(>0.5) 함의(Entailment)인 경우: 최상
        # - 모순(Contradiction)인 경우: 유사도와 관계없이 오답 처리 권장
        is_passed = (sts_score > 0.6) and (nli_label != "contradiction")
        
        return {
            "sts_score": sts_score,
            "nli_label": nli_label,
            "nli_confidence": nli_confidence,
            "is_passed": is_passed,
            "feedback": self._generate_feedback(is_passed, nli_label, sts_score)
        }

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

    def _generate_feedback(self, is_passed, nli_label, sts_score):
        if nli_label == "contradiction":
            return "본문과 상충되는 내용이 포함되어 있습니다. 다시 한번 읽어볼까요?"
        if is_passed:
            return "정확한 이해입니다! 핵심을 잘 짚어내셨어요."
        if sts_score < 0.3:
            return "답변이 본문의 주제와 다소 거리가 있는 것 같습니다."
        return "조금 더 구체적으로 본문의 핵심어를 포함해서 답변해 보세요."
