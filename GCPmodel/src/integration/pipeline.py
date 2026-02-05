"""
통합 파이프라인
사고유도 → 평가 → 피드백 전체 플로우 관리
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from src.model.inferencer import ThoughtInducer
from src.evaluation.gemini_evaluator import GeminiEvaluator
from src.evaluation.language_analyzer import ComprehensiveLanguageAnalyzer


class IntegratedPipeline:
    """전체 시스템 통합 파이프라인"""

    def __init__(
        self,
        model_path: str = "",  # TODO: 파인튜닝된 모델 경로
        gemini_key: Optional[str] = None,
        harmful_model_path: str = "",  # TODO: 유해표현 AI 모델 경로
        config_path: str = "configs/evaluation_config.yaml"
    ):
        """
        Args:
            model_path: 파인튜닝된 Gemma 모델 경로
            gemini_key: Gemini API 키
            harmful_model_path: 유해표현 AI 모델 경로
            config_path: 평가 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        resolved_gemini_key = self._resolve_config_value(
            self.config.get("gemini", {}).get("api_key", "")
        )
        resolved_harmful_model_path = self._resolve_config_value(
            self.config.get("harmful_detection", {}).get("model_path", "")
        )

        # 모듈 초기화
        print("🔧 파이프라인 초기화 중...")

        # 1. 사고유도 추론 엔진
        self.thought_inducer = ThoughtInducer(model_path=model_path)

        # 2. Gemini 평가기
        self.gemini_eval = GeminiEvaluator(
            api_key=gemini_key or resolved_gemini_key
        )

        # 3. 언어 분석기
        self.lang_analyzer = ComprehensiveLanguageAnalyzer(
            harmful_model_path=harmful_model_path or resolved_harmful_model_path
        )

        # 평가 가중치
        self.qual_weight = self.config.get("weights", {}).get("qualitative", 0.7)
        self.quan_weight = self.config.get("weights", {}).get("quantitative", 0.3)

        print("✅ 파이프라인 초기화 완료")

    def _load_config(self, config_path: str) -> Dict:
        """설정 로드"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return {"weights": {"qualitative": 0.7, "quantitative": 0.3}}

    def _resolve_config_value(self, value: str) -> str:
        """${ENV_VAR} 형식의 설정값을 실제 환경변수로 치환"""
        if not isinstance(value, str):
            return ""
        value = value.strip()
        if value.startswith("${") and value.endswith("}") and len(value) > 3:
            env_name = value[2:-1].strip()
            return os.getenv(env_name, "")
        return value

    def process(
        self,
        student_input: str,
        context: Optional[str] = None,
        save_result: bool = True
    ) -> Dict:
        """
        전체 파이프라인 실행

        Args:
            student_input: 학생 질문/입력
            context: 맥락 (작품명 등)
            save_result: 결과 저장 여부

        Returns:
            Dict: 전체 처리 결과
        """
        timestamp = datetime.now().isoformat()

        # 1. 사고유도 대화 생성
        print("💭 사고유도 응답 생성 중...")
        response = self.thought_inducer.generate_response(
            student_input=student_input,
            context=context
        )

        # 2. 질적 평가 (Gemini)
        print("📊 질적 평가 수행 중...")
        qualitative = self.gemini_eval.evaluate(
            student_input=student_input,
            thought_log=response.get('log', ''),
            context=context
        )

        # 3. 정량 분석 (언어)
        print("📈 정량 분석 수행 중...")
        quantitative = self.lang_analyzer.analyze(student_input)

        # 4. 통합 평가
        integrated = self._integrate_evaluation(qualitative, quantitative)

        # 5. 개인 맞춤 피드백
        feedback = self._generate_feedback(qualitative, quantitative)

        result = {
            "timestamp": timestamp,
            "input": {
                "student_input": student_input,
                "context": context
            },
            "사고유도_응답": response.get('induction', ''),
            "사고로그": response.get('log', ''),
            "질적_평가": qualitative,
            "정량_분석": quantitative,
            "통합_평가": integrated,
            "개인_피드백": feedback
        }

        # 결과 저장
        if save_result:
            self._save_result(result)

        print("✅ 처리 완료!")
        return result

    def _integrate_evaluation(self, qual: Dict, quan: Dict) -> Dict:
        """질적 + 정량 통합 평가"""
        # 질적 점수 (70%)
        qual_avg = qual.get('평균', 3.0)
        qual_score = qual_avg * self.qual_weight * 20  # 최대 70점

        # 정량 점수 (30%)
        vocab_score = quan.get('어휘_다양성', {}).get('점수', 0.5) * 10  # 최대 10점
        concept_count = quan.get('핵심_개념어', {}).get('총_개념_사용', 0)
        concept_score = min(concept_count * 2, 10)  # 최대 10점
        complexity_score = min(quan.get('문장_복잡도', {}).get('점수', 5), 10)  # 최대 10점

        quan_score = (vocab_score + concept_score + complexity_score) * (self.quan_weight / 0.3)

        # 총점
        total = qual_score + quan_score

        # 등급
        if total >= 90:
            grade = "A+"
        elif total >= 85:
            grade = "A"
        elif total >= 80:
            grade = "B+"
        elif total >= 75:
            grade = "B"
        elif total >= 70:
            grade = "C+"
        else:
            grade = "C"

        return {
            "질적_점수": round(qual_score, 1),
            "정량_점수": round(quan_score, 1),
            "세부_정량": {
                "어휘_점수": round(vocab_score, 1),
                "개념_점수": round(concept_score, 1),
                "복잡도_점수": round(complexity_score, 1)
            },
            "총점": round(total, 1),
            "등급": grade,
            "등급_설명": self._grade_description(grade)
        }

    def _grade_description(self, grade: str) -> str:
        """등급 설명"""
        descriptions = {
            "A+": "탁월한 수준. 깊이 있는 사고와 풍부한 표현력.",
            "A": "우수한 수준. 논리적 사고와 적절한 개념 활용.",
            "B+": "양호한 수준. 기본적인 이해와 표현 능력 보유.",
            "B": "보통 수준. 추가적인 사고 연습 권장.",
            "C+": "기초 수준. 지속적인 학습과 피드백 필요.",
            "C": "미흡한 수준. 기초부터 체계적 학습 필요."
        }
        return descriptions.get(grade, "")

    def _generate_feedback(self, qual: Dict, quan: Dict) -> List[str]:
        """개인 맞춤 피드백 생성"""
        feedback = []

        # 강점
        qual_avg = qual.get('평균', 0)
        if qual_avg >= 4:
            feedback.append("✅ 사고의 깊이가 우수합니다.")

        vocab_score = quan.get('어휘_다양성', {}).get('점수', 0)
        if vocab_score >= 0.6:
            feedback.append("✅ 다양한 어휘를 사용하고 있습니다.")

        concept_count = quan.get('핵심_개념어', {}).get('총_개념_사용', 0)
        if concept_count >= 5:
            feedback.append("✅ 핵심 개념을 잘 활용하고 있습니다.")

        # Gemini 평가의 강점 추가
        for strength in qual.get('강점', []):
            if strength and strength not in feedback:
                feedback.append(f"✅ {strength}")

        # 개선점
        critical_score = qual.get('비판적_사고', {}).get('점수', 3)
        if critical_score < 3:
            feedback.append("💡 다양한 관점에서 생각해보세요.")

        if concept_count < 3:
            feedback.append("💡 핵심 개념어를 더 활용해보세요.")

        repetition_rate = quan.get('반복_패턴', {}).get('반복률', 0)
        if repetition_rate > 0.2:
            feedback.append("💡 다양한 표현을 시도해보세요.")

        # Gemini 평가의 개선점 추가
        for improvement in qual.get('개선점', []):
            if improvement and f"💡 {improvement}" not in feedback:
                feedback.append(f"💡 {improvement}")

        # 경고
        harmful_level = quan.get('유해표현', {}).get('경고_레벨', '안전')
        if harmful_level != "안전":
            feedback.append("⚠️ 긍정적인 언어 사용을 권장합니다.")

        sentiment_tone = quan.get('감정_톤', {}).get('최종_톤', '중립적')
        if "부정" in sentiment_tone:
            feedback.append("⚠️ 학습에 대한 긍정적 태도를 가져보세요.")

        return feedback

    def _save_result(self, result: Dict):
        """결과 저장"""
        output_dir = Path("outputs/evaluations")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_{timestamp}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"📁 결과 저장: {filepath}")

    def generate_student_report(self, result: Dict) -> str:
        """학생용 리포트 생성"""
        report = "# 📚 학습 평가 리포트\n\n"

        # 사고유도 응답
        report += "## 💭 AI의 사고유도 질문\n"
        report += f"{result.get('사고유도_응답', '')}\n\n"

        # 종합 결과
        integrated = result.get('통합_평가', {})
        report += "## 📊 종합 평가\n"
        report += f"- **등급**: {integrated.get('등급', 'N/A')}\n"
        report += f"- **총점**: {integrated.get('총점', 0)} / 100\n"
        report += f"- **평가**: {integrated.get('등급_설명', '')}\n\n"

        # 피드백
        feedback = result.get('개인_피드백', [])
        if feedback:
            report += "## 💡 개인 맞춤 피드백\n"
            for fb in feedback:
                report += f"{fb}\n"
            report += "\n"

        return report

    def generate_teacher_report(self, result: Dict) -> str:
        """교사용 상세 리포트 생성"""
        report = "# 📋 교사용 상세 평가 리포트\n\n"

        # 학생 입력
        input_data = result.get('input', {})
        report += "## 학생 정보\n"
        report += f"- **질문/답변**: {input_data.get('student_input', '')}\n"
        report += f"- **맥락**: {input_data.get('context', 'N/A')}\n"
        report += f"- **평가 시간**: {result.get('timestamp', '')}\n\n"

        # 사고로그
        report += "## 사고로그 (AI 분석)\n"
        report += f"```\n{result.get('사고로그', '')}\n```\n\n"

        # 질적 평가 상세
        qual = result.get('질적_평가', {})
        report += "## 질적 평가 (Gemini)\n"
        for dim in ['추론_깊이', '비판적_사고', '문학적_이해']:
            dim_data = qual.get(dim, {})
            report += f"### {dim}\n"
            report += f"- **점수**: {dim_data.get('점수', 'N/A')} / 5\n"
            report += f"- **피드백**: {dim_data.get('피드백', '')}\n\n"

        # 정량 분석 상세
        quan = result.get('정량_분석', {})
        report += "## 정량 분석\n"
        report += f"- **어휘 다양성**: {quan.get('어휘_다양성', {}).get('등급', 'N/A')} ({quan.get('어휘_다양성', {}).get('점수', 0):.3f})\n"
        report += f"- **핵심 개념어 사용**: {quan.get('핵심_개념어', {}).get('총_개념_사용', 0)}개 ({quan.get('핵심_개념어', {}).get('평가', 'N/A')})\n"
        report += f"- **문장 복잡도**: {quan.get('문장_복잡도', {}).get('등급', 'N/A')}\n"
        report += f"- **감정 톤**: {quan.get('감정_톤', {}).get('최종_톤', 'N/A')}\n"
        report += f"- **유해표현**: {quan.get('유해표현', {}).get('경고_레벨', '안전')}\n\n"

        # 통합 평가
        integrated = result.get('통합_평가', {})
        report += "## 통합 점수\n"
        report += f"- **질적 점수**: {integrated.get('질적_점수', 0)} / 70\n"
        report += f"- **정량 점수**: {integrated.get('정량_점수', 0)} / 30\n"
        report += f"- **총점**: {integrated.get('총점', 0)} / 100\n"
        report += f"- **최종 등급**: {integrated.get('등급', 'N/A')}\n\n"

        return report

    def batch_process(
        self,
        inputs: List[Dict],
        output_path: Optional[str] = None
    ) -> List[Dict]:
        """
        배치 처리

        Args:
            inputs: [{"student_input": ..., "context": ...}, ...]
            output_path: 결과 저장 경로

        Returns:
            List[Dict]: 처리 결과 리스트
        """
        from tqdm import tqdm

        results = []
        for item in tqdm(inputs, desc="처리 중"):
            result = self.process(
                student_input=item.get("student_input", ""),
                context=item.get("context"),
                save_result=False
            )
            results.append(result)

        # 저장
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                for item in results:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

            print(f"✅ 배치 결과 저장: {output_path}")

        return results


# 직접 실행 시
if __name__ == "__main__":
    # 사용 예시
    pipeline = IntegratedPipeline(
        model_path="",  # TODO: 파인튜닝된 모델 경로
        gemini_key=None,  # TODO: API 키 또는 환경변수
        harmful_model_path=""  # TODO: 유해표현 모델 경로
    )

    # 테스트
    # result = pipeline.process(
    #     student_input="춘향전에서 이몽룡은 왜 신분을 숨겼나요?",
    #     context="춘향전"
    # )

    # 리포트 생성
    # student_report = pipeline.generate_student_report(result)
    # teacher_report = pipeline.generate_teacher_report(result)

    print("파이프라인 준비 완료. model_path와 gemini_key를 설정하고 사용하세요.")
