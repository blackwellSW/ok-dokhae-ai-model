"""
Gemini 기반 질적 평가 모듈
- 추론 깊이
- 비판적 사고
- 문학적 이해
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class GeminiEvaluator:
    """Gemini Pro 기반 질적 평가"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        rubric_path: str = "configs/rubric.json"
    ):
        """
        Args:
            api_key: Gemini API 키 (None이면 환경변수 GEMINI_API_KEY 사용)
            rubric_path: 평가 루브릭 파일 경로
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = None
        self.rubric = self._load_rubric(rubric_path)

        self._init_model()

    def _load_rubric(self, rubric_path: str) -> Dict:
        """평가 루브릭 로드"""
        try:
            with open(rubric_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ 루브릭 파일을 찾을 수 없습니다: {rubric_path}")
            return self._default_rubric()

    def _default_rubric(self) -> Dict:
        """기본 루브릭"""
        return {
            "추론_깊이": {
                "5": "다층적 사고, 텍스트 맥락 깊이 이해",
                "4": "논리적 추론, 맥락 연결",
                "3": "기본적 추론",
                "2": "단편적 이해",
                "1": "표면적 반응"
            },
            "비판적_사고": {
                "5": "독자적 해석, 다양한 관점",
                "4": "대안적 해석 시도",
                "3": "직접적 답변",
                "2": "단순 정보 회상",
                "1": "관련 없는 응답"
            },
            "문학적_이해": {
                "5": "시대/문화 맥락 통합",
                "4": "작품 구조 이해",
                "3": "줄거리 이해",
                "2": "부분적 이해",
                "1": "오해"
            }
        }

    def _init_model(self):
        """Gemini 모델 초기화"""
        if not self.api_key:
            print("⚠️ Gemini API 키가 설정되지 않았습니다.")
            print("   환경변수 GEMINI_API_KEY를 설정하거나 api_key를 전달해주세요.")
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            print("✅ Gemini Pro 모델 초기화 완료")
        except ImportError:
            print("⚠️ google-generativeai 패키지를 설치해주세요.")
            self.model = None
        except Exception as e:
            print(f"⚠️ Gemini 초기화 실패: {e}")
            self.model = None

    def evaluate(
        self,
        student_input: str,
        thought_log: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        질적 평가 수행

        Args:
            student_input: 학생 질문/답변
            thought_log: AI가 생성한 사고로그
            context: 추가 맥락 (작품명 등)

        Returns:
            Dict: 평가 결과
        """
        if not self.model:
            return self._fallback_eval()

        # 루브릭 텍스트 생성
        rubric_text = self._format_rubric()

        # 프롬프트 구성
        prompt = f"""고전문학 교육 평가 전문가로서 학생의 사고를 평가하세요.

[평가 루브릭]
{rubric_text}

[맥락]
{context or "고전문학 학습"}

[학생 질문/답변]
{student_input}

[사고로그]
{thought_log}

[평가 지침]
1. 각 차원별로 1-5점 척도로 평가하세요.
2. 각 점수에 대한 구체적인 피드백을 제공하세요.
3. 학생의 사고 과정을 긍정적으로 평가하면서 개선점도 제시하세요.

[출력 형식 - JSON만 출력]
{{
  "추론_깊이": {{"점수": X, "피드백": "..."}},
  "비판적_사고": {{"점수": X, "피드백": "..."}},
  "문학적_이해": {{"점수": X, "피드백": "..."}},
  "종합_평가": "...",
  "강점": ["...", "..."],
  "개선점": ["...", "..."]
}}"""

        try:
            response = self.model.generate_content(prompt)
            evaluation = self._parse_response(response.text)

            # 총점 및 평균 계산
            scores = [
                evaluation.get("추론_깊이", {}).get("점수", 3),
                evaluation.get("비판적_사고", {}).get("점수", 3),
                evaluation.get("문학적_이해", {}).get("점수", 3)
            ]
            evaluation["총점"] = sum(scores)
            evaluation["평균"] = round(sum(scores) / 3, 2)

            # 메타데이터 추가
            evaluation["metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "model": "gemini-pro"
            }

            return evaluation

        except Exception as e:
            print(f"⚠️ 평가 중 오류 발생: {e}")
            return self._fallback_eval()

    def _format_rubric(self) -> str:
        """루브릭을 문자열로 포맷"""
        rubric = self.rubric.get("qualitative_rubric", self._default_rubric())

        text = ""
        for dimension, criteria in rubric.items():
            text += f"\n{dimension}:\n"
            if isinstance(criteria, dict) and "criteria" in criteria:
                criteria = criteria["criteria"]
            for score, desc in criteria.items():
                text += f"  {score}점: {desc}\n"

        return text

    def _parse_response(self, response_text: str) -> Dict:
        """응답 파싱"""
        try:
            # JSON 블록 추출
            json_text = response_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]

            return json.loads(json_text.strip())

        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트에서 정보 추출 시도
            return self._extract_from_text(response_text)

    def _extract_from_text(self, text: str) -> Dict:
        """텍스트에서 평가 정보 추출 (fallback)"""
        import re

        result = {
            "추론_깊이": {"점수": 3, "피드백": ""},
            "비판적_사고": {"점수": 3, "피드백": ""},
            "문학적_이해": {"점수": 3, "피드백": ""},
            "종합_평가": text[:200] if text else "평가 텍스트 파싱 실패"
        }

        # 점수 패턴 찾기
        patterns = {
            "추론": r"추론.*?(\d)",
            "비판": r"비판.*?(\d)",
            "문학": r"문학.*?(\d)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                score = int(match.group(1))
                if key == "추론":
                    result["추론_깊이"]["점수"] = score
                elif key == "비판":
                    result["비판적_사고"]["점수"] = score
                elif key == "문학":
                    result["문학적_이해"]["점수"] = score

        return result

    def _fallback_eval(self) -> Dict:
        """폴백 평가 (API 사용 불가 시)"""
        return {
            "추론_깊이": {"점수": 3, "피드백": "API 연결 필요"},
            "비판적_사고": {"점수": 3, "피드백": "API 연결 필요"},
            "문학적_이해": {"점수": 3, "피드백": "API 연결 필요"},
            "종합_평가": "Gemini API 연결 후 평가 가능",
            "총점": 9,
            "평균": 3.0,
            "강점": [],
            "개선점": ["Gemini API 키 설정 필요"],
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "model": "fallback"
            }
        }

    def batch_evaluate(
        self,
        evaluations: list,
        output_path: Optional[str] = None
    ) -> list:
        """
        배치 평가

        Args:
            evaluations: [{"student_input": ..., "thought_log": ..., "context": ...}, ...]
            output_path: 결과 저장 경로

        Returns:
            list: 평가 결과 리스트
        """
        from tqdm import tqdm

        results = []
        for item in tqdm(evaluations, desc="평가 중"):
            result = self.evaluate(
                student_input=item.get("student_input", ""),
                thought_log=item.get("thought_log", ""),
                context=item.get("context")
            )
            result["input_data"] = item
            results.append(result)

        # 저장
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                for item in results:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

            print(f"✅ 평가 결과 저장: {output_path}")

        return results

    def generate_report(
        self,
        evaluation: Dict,
        include_rubric: bool = True
    ) -> str:
        """
        평가 리포트 생성

        Args:
            evaluation: 평가 결과
            include_rubric: 루브릭 포함 여부

        Returns:
            str: 마크다운 형식 리포트
        """
        report = "# 📊 학생 사고력 평가 리포트\n\n"

        # 종합 점수
        report += "## 종합 결과\n"
        report += f"- **총점**: {evaluation.get('총점', 'N/A')} / 15\n"
        report += f"- **평균**: {evaluation.get('평균', 'N/A')} / 5.0\n\n"

        # 차원별 평가
        report += "## 세부 평가\n\n"

        dimensions = ["추론_깊이", "비판적_사고", "문학적_이해"]
        for dim in dimensions:
            dim_eval = evaluation.get(dim, {})
            score = dim_eval.get("점수", "N/A")
            feedback = dim_eval.get("피드백", "")

            report += f"### {dim.replace('_', ' ')}\n"
            report += f"- **점수**: {score} / 5\n"
            report += f"- **피드백**: {feedback}\n\n"

        # 종합 평가
        report += "## 종합 평가\n"
        report += f"{evaluation.get('종합_평가', '')}\n\n"

        # 강점 및 개선점
        strengths = evaluation.get("강점", [])
        improvements = evaluation.get("개선점", [])

        if strengths:
            report += "## ✅ 강점\n"
            for s in strengths:
                report += f"- {s}\n"
            report += "\n"

        if improvements:
            report += "## 💡 개선점\n"
            for i in improvements:
                report += f"- {i}\n"
            report += "\n"

        return report


# 직접 실행 시
if __name__ == "__main__":
    # 테스트
    evaluator = GeminiEvaluator()

    test_result = evaluator.evaluate(
        student_input="춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
        thought_log="학생이 신분제와 사랑의 진정성을 연결지어 사고 시작. 추론 깊이: 중상.",
        context="춘향전"
    )

    print("=" * 60)
    print("📊 평가 결과")
    print("=" * 60)
    print(json.dumps(test_result, ensure_ascii=False, indent=2))
