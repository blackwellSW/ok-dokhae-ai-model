from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Optional

class Evaluator:
    VALIDATION_RULES = {
        "min_chars": 30,         # TOO_SHORT 기준 
        "qa_th": 0.38,           # OFF_PATH 기준
        "link_th": 0.42,         # WEAK_LINK 기준
        "min_tokens": 8,
    }

    DIAG = {
        "OK": "OK",
        "TOO_SHORT_OR_THIN": "TOO_SHORT_OR_THIN",
        "OFF_PATH": "OFF_PATH",
        "NO_GROUNDING": "NO_GROUNDING",
        "MISSING_WHY": "MISSING_WHY",
        "GENERIC": "GENERIC",
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

        # 1) INSUFFICIENT_REASONING
        if length_chars < self.VALIDATION_RULES["min_chars"] or length_tokens < self.VALIDATION_RULES["min_tokens"]:
            qa_score = self._safe_sts(question, reasoning_text) if question else 0.0
            link_score = self._safe_sts(self._build_context(claim_text, evidence_texts), reasoning_text)
            return {
                "label": "INSUFFICIENT_REASONING",
                "diag": self.DIAG["TOO_SHORT_OR_THIN"],
                "scores": {
                    "qa_score": round(qa_score, 3),
                    "link_score": round(link_score, 3),
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": len(evidence_texts),
                },
                "debug": {"rule": "INSUFFICIENT_REASONING"}
            }

        # 2) OFF_PATH (질문 무시)
        if not question:
            raise ValueError("validate_reasoning requires non-empty question")
        qa_score = self._safe_sts(question, reasoning_text)
        if qa_score < self.VALIDATION_RULES["qa_th"]:
            link_score = self._safe_sts(self._build_context(claim_text, evidence_texts), reasoning_text)
            return {
                "label": "OFF_PATH",
                "diag": self.DIAG["OFF_PATH"],
                "scores": {
                    "qa_score": round(qa_score, 3),
                    "link_score": round(link_score, 3),
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": len(evidence_texts),
                },
                "debug": {"rule": "OFF_PATH"}
            }

        # 3) WEAK_LINK (근거-주장 연결 설명 약함)
        context = self._build_context(claim_text, evidence_texts)
        link_score = self._safe_sts(context, reasoning_text)
        diag = self._pick_diag_for_weak_link(claim_text, evidence_texts, reasoning_text)
        if link_score < self.VALIDATION_RULES["link_th"]:
            return {
                "label": "WEAK_LINK",
                "diag": diag,
                "scores": {
                    "qa_score": round(qa_score, 3),
                    "link_score": round(link_score, 3),
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": len(evidence_texts),
                },
                "debug": {"rule": "WEAK_LINK"}
            }

        # 4) GOOD
        # link_score가 높게 나와도, 근거 사용 흔적이 없으면 GOOD으로 보내지 않음
        if diag == self.DIAG["NO_GROUNDING"]:
            return {
                "label": "WEAK_LINK",
                "diag": diag,
                "scores": {
                    "qa_score": round(qa_score, 3),
                    "link_score": round(link_score, 3),
                    "length_chars": length_chars,
                    "length_tokens": length_tokens,
                    "evidence_count": len(evidence_texts),
                },
                "debug": {"rule": "GOOD_GATE_NO_GROUNDING"}
            }

        return {
            "label": "GOOD",
            "diag": self.DIAG["OK"],
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

    def _pick_diag_for_weak_link(self, claim_text: str, evidence_texts: List[str], reasoning_text: str) -> str:
        # 1) 근거 자체가 없으면: grounding 불가
        if not evidence_texts:
            return self.DIAG["NO_GROUNDING"]

        # 2) 근거 사용 흔적(아주 단순한 overlap 체크)
        evidence_blob = " ".join(evidence_texts[:3])
        overlap_hits = 0
        for tok in set(evidence_blob.split()):
            if len(tok) >= 2 and tok in reasoning_text:
                overlap_hits += 1
                if overlap_hits >= 2:
                    break
        if overlap_hits < 2:
            return self.DIAG["NO_GROUNDING"]

        # 3) 연결어가 거의 없으면 '왜' 설명 부재로 간주
        connectors = ["왜", "때문", "따라서", "그러므로", "즉", "하지만", "반면", "만약"]
        if not any(c in reasoning_text for c in connectors):
            return self.DIAG["MISSING_WHY"]

        # 4) 나머지는 뭉뚱그린 설명으로 처리
        return self.DIAG["GENERIC"]
    
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