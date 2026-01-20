from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Optional

class Evaluator:
    VALIDATION_RULES = {
        "min_chars": 30,         # TOO_SHORT 기준 (초기값)
        "qa_th": 0.38,           # OFF_TOPIC 기준
        "link_th": 0.42,         # WEAK_LINK 기준
    }

    def validate_reasoning(
        self,
        question: str,
        claim_text: str,
        evidence_texts: List[str],
        reasoning_text: str,
    ) -> Dict:
        question = (question or "").strip()
        claim_text = (claim_text or "").strip()
        reasoning_text = (reasoning_text or "").strip()
        evidence_texts = [e.strip() for e in (evidence_texts or []) if e and e.strip()]

        # --- basic features ---
        length_chars = len(reasoning_text)
        length_tokens = len(reasoning_text.split())

        # 1) NO_EVIDENCE
        if len(evidence_texts) == 0:
            return {
                "label": "NO_EVIDENCE",
                "scores": {
                    "qa_score": 0.0,
                    "link_score": 0.0,
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": 0,
                },
                "debug": {"rule": "NO_EVIDENCE"}
            }

        # 2) TOO_SHORT
        if length_chars < self.VALIDATION_RULES["min_chars"]:
            qa_score = self._safe_sts(question, reasoning_text) if question else 0.0
            link_score = self._safe_sts(self._build_context(claim_text, evidence_texts), reasoning_text)
            return {
                "label": "TOO_SHORT",
                "scores": {
                    "qa_score": round(qa_score, 3),
                    "link_score": round(link_score, 3),
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": len(evidence_texts),
                },
                "debug": {"rule": "TOO_SHORT"}
            }

        # 3) OFF_TOPIC (질문 무시)
        if not question:
            raise ValueError("validate_reasoning requires non-empty question")
        qa_score = self._safe_sts(question, reasoning_text)
        if qa_score < self.VALIDATION_RULES["qa_th"]:
            link_score = self._safe_sts(self._build_context(claim_text, evidence_texts), reasoning_text)
            return {
                "label": "OFF_TOPIC",
                "scores": {
                    "qa_score": round(qa_score, 3),
                    "link_score": round(link_score, 3),
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": len(evidence_texts),
                },
                "debug": {"rule": "OFF_TOPIC"}
            }

        # 4) WEAK_LINK (근거-주장 연결 설명 약함)
        context = self._build_context(claim_text, evidence_texts)
        link_score = self._safe_sts(context, reasoning_text)
        if link_score < self.VALIDATION_RULES["link_th"]:
            return {
                "label": "WEAK_LINK",
                "scores": {
                    "qa_score": round(qa_score, 3),
                    "link_score": round(link_score, 3),
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": len(evidence_texts),
                },
                "debug": {"rule": "WEAK_LINK"}
            }

        # 5) GOOD
        return {
            "label": "GOOD",
            "scores": {
                "qa_score": round(qa_score, 3),
                "link_score": round(link_score, 3),
                "length_chars": length_chars,
                "length_tokens": length_tokens,
                "evidence_count": len(evidence_texts),
            },
            "debug": {"rule": "GOOD"}
        }

    def _build_context(self, claim_text: str, evidence_texts: List[str]) -> str:
        parts = []
        if claim_text:
            parts.append(f"주장: {claim_text}")
        parts.append("근거: " + " / ".join(evidence_texts[:3]))  # 너무 길면 상위 3개만
        return "\n".join(parts)

    def _safe_sts(self, a: str, b: str) -> float:
        a = (a or "").strip()
        b = (b or "").strip()
        if not a or not b:
            return 0.0
        try:
            return max(0.0, min(1.0, self._get_sts_score(a, b)))
        except Exception:
            return 0.0
    
    def __init__(self):
        # 유사도 평가 모델 (Bi-Encoder: 빠름)
        self.sts_model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

    def _get_sts_score(self, text1: str, text2: str) -> float:
        embeddings = self.sts_model.encode([text1, text2])
        score = util.cos_sim(embeddings[0], embeddings[1])
        return float(score.item())