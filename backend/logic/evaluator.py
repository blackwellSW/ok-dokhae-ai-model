from sentence_transformers import SentenceTransformer, util, CrossEncoder
import torch
import re
from typing import List, Dict, Tuple

class Evaluator:
    def __init__(self):
        # 1. 유사도 평가 모델 (Bi-Encoder: 빠름)
        self.sts_model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
        
        # 2. 논리적 일관성 평가 모델 (Cross-Encoder: 정확함, KLUE-NLI 기반)
        # 사용 가능한 적절한 공개 모델이 없을 경우 대비하여 try-except 구성
        try:
            self.nli_model = CrossEncoder('klue/roberta-base-nli')
        except Exception:
            self.nli_model = None

    def evaluate_answer(self, user_answer: str, reference_text: str) -> Dict:
        """
        사용자 답변을 다각도로 평가합니다.
        1. STS Score: 답변 vs 핵심 논리 유닛들의 평균 유사도 (부분 정답 과대평가 방지)
        2. Weighted Coverage: 중요도가 높은 유닛(주장, 반전 등) 중심의 포함 여부
        3. NLI Penalty: 논리적 모순 발생 시 감점 (단독 탈락 조건은 아님)
        """
        # 0. 전처리
        user_answer = user_answer.strip()
        reference_text = reference_text.strip()
        
        if not user_answer:
            return {
                "is_passed": False,
                "sts_score": 0.0,
                "coverage_score": 0.0,
                "final_score": 0.0,
                "nli_label": "neutral",
                "feedback": "답변을 입력해 주세요."
            }

        # 1. 핵심 논리 유닛 및 가중치 추출
        logic_units_info = self._get_weighted_logic_units(reference_text)
        unit_texts = [info["text"] for info in logic_units_info]
        unit_weights = [info["weight"] for info in logic_units_info]
        
        # 2. 인코딩 및 유사도 계산
        answer_emb = self.sts_model.encode(user_answer, convert_to_tensor=True)
        unit_embs = self.sts_model.encode(unit_texts, convert_to_tensor=True)
        unit_sims = util.cos_sim(unit_embs, answer_emb).flatten().tolist()
        
        # 3. STS 점수: 각 유닛과의 유사도 평균 (전체 문맥 파악 정도)
        sts_score = sum(unit_sims) / len(unit_sims) if unit_sims else 0.0
        
        # 4. Weighted Coverage 계산
        covered_weight = 0.0
        total_weight = sum(unit_weights)
        covered_units = []
        
        for i, sim in enumerate(unit_sims):
            if sim > 0.6:  # 개별 유항 반영 임계값
                covered_weight += unit_weights[i]
                covered_units.append(unit_texts[i])
        
        coverage_score = covered_weight / total_weight if total_weight > 0 else 1.0
        
        # 5. NLI 분석 및 패널티 산출
        nli_label, nli_confidence = self._get_nli_status(user_answer, reference_text)
        nli_penalty = 0.0
        if nli_label == "contradiction":
            # 모순 시 강한 감점 (최대 -0.3)
            nli_penalty = 0.3 * nli_confidence
        elif nli_label == "entailment":
            # 함의 시 가점 (최대 +0.05)
            nli_penalty = -0.05 * nli_confidence

        # 6. 최종 이해 충실도 (Understanding Fidelity) 점수
        # 가중치: Coverage(0.7) + STS(0.3) - Penalty
        final_score = (coverage_score * 0.7) + (sts_score * 0.3) - nli_penalty
        final_score = max(0.0, min(1.0, final_score))
        
        # 7. 종료 조건 (성공 여부)
        # STS와 Coverage가 일정 수준 이상이면 NLI 모순이 있어도 통과 가능 (NLI 오판 구제)
        is_passed = final_score > 0.55
        
        # 높은 수준의 이해도일 경우 추가 검증 (중요 유닛 누락 체크)
        important_missing = any(info["weight"] >= 1.4 and unit_texts[i] not in covered_units 
                               for i, info in enumerate(logic_units_info))
        if important_missing and final_score < 0.7:
             is_passed = False

        return {
            "sts_score": round(sts_score, 3),
            "coverage_score": round(coverage_score, 3),
            "final_score": round(final_score, 3),
            "nli_label": nli_label,
            "nli_confidence": round(nli_confidence, 3),
            "is_passed": is_passed,
            "feedback": self._generate_feedback(is_passed, nli_label, sts_score, coverage_score, logic_units_info, covered_units)
        }

    def _get_weighted_logic_units(self, text: str) -> List[Dict]:
        """
        문장을 핵심 논리 단위로 분리하고 각 단위에 중요도 가중치를 부여합니다.
        가중치 기준: 주장(1.5) > 반전(1.3) > 근거(1.2) > 일반(1.0)
        """
        # 1. 분리
        delimiters = r'[,.?!]|\s그리고\s|\s하지만\s|\s따라서\s|\s그러므로\s|\s그런데\s'
        raw_units = re.split(delimiters, text)
        refined_units = [u.strip() for u in raw_units if len(u.strip()) > 5]
        
        if not refined_units:
            refined_units = [text]

        # 2. 가중치 부여 패턴
        patterns = {
            "claim": (r"결론적으로|따라서|그러므로|~해야 한다|~임이 분명하다|중요하다", 1.5),
            "contrast": (r"하지만|그러나|반면|이와 달리|반대로", 1.3),
            "evidence": (r"왜냐하면|~때문에|예를 들어|실제로|~에 따르면", 1.2)
        }
        
        weighted_units = []
        for unit in refined_units:
            max_weight = 1.0
            for label, (pattern, weight) in patterns.items():
                if re.search(pattern, unit):
                    max_weight = max(max_weight, weight)
            
            weighted_units.append({
                "text": unit,
                "weight": max_weight
            })
            
        return weighted_units

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

    def _generate_feedback(self, is_passed, nli_label, sts_score, coverage_score, logic_units_info, covered_units):
        if nli_label == "contradiction" and sts_score < 0.5:
            return "본문과 상충되는 핵심 내용이 있습니다. 다시 한번 꼼꼼히 읽어보세요."
        
        if is_passed:
            if coverage_score > 0.9:
                return "완벽합니다! 지문의 핵심 논리를 아주 정확하게 파악하셨어요."
            return "핵심 내용을 잘 짚어내셨습니다. 이해 충실도가 높네요."
        
        # 미흡한 경우 상세 피드백
        important_missed = [info["text"] for info in logic_units_info 
                           if info["weight"] >= 1.3 and info["text"] not in covered_units]
        
        if important_missed:
            return f"가장 중요한 지점('{important_missed[0][:15]}...')에 대한 이해를 조금 더 보완해볼까요?"
            
        if coverage_score < 0.5:
            return "본문의 핵심적인 내용들을 조금 더 구체적으로 포함해서 답변해 보세요."
            
        if sts_score < 0.4:
            return "답변의 전반적인 방향은 맞지만, 의미적 정확성을 높이면 더 좋겠습니다."
            
        return "조금 더 깊이 있게 설명해 주실 수 있을까요? 핵심 논리 사이의 관계를 생각하며 답변해 보세요."
from sentence_transformers import SentenceTransformer, util, CrossEncoder
import torch

class Evaluator:
    def __init__(self):
        # 1. 유사도 평가 모델 (Bi-Encoder: 빠름)
        self.sts_model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
        
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
