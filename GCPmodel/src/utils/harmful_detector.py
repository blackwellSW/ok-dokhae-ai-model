"""
유해표현 감지 모듈
AI HUB 유해표현 검출 AI 모델 연동
"""

import os
from pathlib import Path
from typing import Dict, List, Optional


class HarmfulExpressionDetector:
    """AI HUB 유해표현 검출 AI 모델 래퍼"""

    def __init__(
        self,
        model_path: str = "",  # TODO: AI HUB 유해표현 모델 경로
        device: str = "auto"
    ):
        """
        Args:
            model_path: AI HUB 유해표현 모델 경로
            device: 사용할 디바이스 ("auto", "cuda", "cpu")
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        self.tokenizer = None
        self.is_loaded = False

        # 유해표현 카테고리
        self.categories = {
            "욕설": "swear",
            "비속어": "profanity",
            "혐오표현": "hate_speech",
            "성적표현": "sexual",
            "폭력표현": "violence",
            "차별표현": "discrimination"
        }

        # 경고 레벨 임계값
        self.thresholds = {
            "safe": 0,
            "caution": 2,
            "warning": 3
        }

        if model_path and Path(model_path).exists():
            self.load_model()

    def load_model(self):
        """
        AI HUB 유해표현 모델 로드

        TODO: 실제 AI HUB 모델 구조에 맞게 구현 필요
        AI HUB 모델 파일 구조:
        - model.pt 또는 model.bin (모델 가중치)
        - config.json (모델 설정)
        - vocab.txt 또는 tokenizer.json (토크나이저)
        """
        if not self.model_path:
            print("⚠️ 유해표현 모델 경로가 설정되지 않았습니다.")
            return

        model_dir = Path(self.model_path)
        if not model_dir.exists():
            print(f"⚠️ 모델 경로를 찾을 수 없습니다: {self.model_path}")
            return

        print(f"📦 유해표현 모델 로딩: {self.model_path}")

        # TODO: AI HUB 모델 로딩 로직 구현
        # 예시 구조 (실제 모델에 맞게 수정 필요):
        """
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        # 모델 로드
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)

        # 디바이스 설정
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        self.model.eval()

        self.is_loaded = True
        print("✅ 유해표현 모델 로드 완료")
        """

        print("   ⚠️ 모델 로딩 로직을 구현해주세요.")
        print("   AI HUB 모델 구조에 맞게 코드를 수정해야 합니다.")

    def detect(self, text: str) -> Dict:
        """
        유해표현 감지

        Args:
            text: 분석할 텍스트

        Returns:
            Dict: {
                "is_harmful": bool,
                "harmful_expressions": List[Dict],
                "warning_level": str,
                "scores": Dict[str, float]
            }
        """
        if not text.strip():
            return self._empty_result()

        if not self.is_loaded:
            # 모델 없이 간단한 키워드 기반 감지 (fallback)
            return self._keyword_based_detection(text)

        # TODO: 실제 모델 추론 구현
        """
        import torch

        # 토큰화
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(self.device)

        # 추론
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)

        # 결과 파싱
        scores = {cat: float(probs[0][i]) for i, cat in enumerate(self.categories.values())}
        harmful_expressions = [
            {"category": cat_kr, "score": scores[cat_en]}
            for cat_kr, cat_en in self.categories.items()
            if scores[cat_en] > 0.5
        ]

        return {
            "is_harmful": len(harmful_expressions) > 0,
            "harmful_expressions": harmful_expressions,
            "warning_level": self._get_warning_level(len(harmful_expressions)),
            "scores": scores
        }
        """

        return self._keyword_based_detection(text)

    def _keyword_based_detection(self, text: str) -> Dict:
        """
        키워드 기반 유해표현 감지 (모델 없을 때 fallback)

        Args:
            text: 분석할 텍스트

        Returns:
            Dict: 감지 결과
        """
        # 기본 유해표현 키워드 (예시)
        # 실제 사용 시 더 포괄적인 목록 필요
        harmful_keywords = {
            "욕설": ["바보", "멍청", "짜증"],
            "비속어": [],
            "혐오표현": [],
            "차별표현": []
        }

        detected = []
        for category, keywords in harmful_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    detected.append({
                        "category": category,
                        "keyword": keyword,
                        "score": 1.0
                    })

        warning_level = self._get_warning_level(len(detected))

        return {
            "is_harmful": len(detected) > 0,
            "harmful_expressions": detected,
            "warning_level": warning_level,
            "detection_method": "keyword_based",
            "note": "AI 모델 로드 후 더 정확한 감지 가능"
        }

    def _get_warning_level(self, count: int) -> str:
        """경고 레벨 결정"""
        if count == 0:
            return "안전"
        elif count <= self.thresholds["caution"]:
            return "주의"
        else:
            return "경고"

    def _empty_result(self) -> Dict:
        """빈 결과"""
        return {
            "is_harmful": False,
            "harmful_expressions": [],
            "warning_level": "안전",
            "scores": {}
        }

    def batch_detect(self, texts: List[str]) -> List[Dict]:
        """
        배치 감지

        Args:
            texts: 텍스트 리스트

        Returns:
            List[Dict]: 감지 결과 리스트
        """
        return [self.detect(text) for text in texts]

    def get_report(self, detection_result: Dict) -> str:
        """
        감지 결과 리포트 생성

        Args:
            detection_result: detect() 결과

        Returns:
            str: 리포트 텍스트
        """
        report = "## 유해표현 감지 결과\n\n"
        report += f"- **경고 레벨**: {detection_result.get('warning_level', 'N/A')}\n"
        report += f"- **유해표현 여부**: {'예' if detection_result.get('is_harmful') else '아니오'}\n\n"

        expressions = detection_result.get('harmful_expressions', [])
        if expressions:
            report += "### 감지된 표현\n"
            for expr in expressions:
                report += f"- **{expr.get('category', 'N/A')}**: "
                if 'keyword' in expr:
                    report += f"'{expr['keyword']}'"
                if 'score' in expr:
                    report += f" (신뢰도: {expr['score']:.2f})"
                report += "\n"
        else:
            report += "감지된 유해표현이 없습니다.\n"

        return report


# 직접 실행 시
if __name__ == "__main__":
    # 테스트
    detector = HarmfulExpressionDetector(
        model_path=""  # TODO: AI HUB 모델 경로
    )

    test_text = "이 부분이 이해가 잘 안 됩니다. 좀 더 설명해주세요."
    result = detector.detect(test_text)

    print("=" * 60)
    print("🔍 유해표현 감지 결과")
    print("=" * 60)

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n" + detector.get_report(result))
