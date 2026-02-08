"""
통합 평가 시스템
역할: 질적 평가 (70%) + 정량 평가 (30%) 통합 및 개인 맞춤 피드백 생성
"""

from typing import Dict, List
from app.services.gemini_evaluator import GeminiEvaluator
from app.services.language_analyzer import LanguageAnalyzer


class IntegratedEvaluator:
    """질적 + 정량 통합 평가 시스템"""
    
    def __init__(self):
        self.gemini_eval = GeminiEvaluator()
        self.lang_analyzer = LanguageAnalyzer()
    
    async def evaluate_comprehensive(
        self,
        student_input: str,
        thought_log: str = ""
    ) -> Dict:
        """
        학생 응답에 대한 종합 평가
        
        Args:
            student_input: 학생 질문/답변
            thought_log: 사고 과정 로그
        
        Returns:
            {
                "질적_평가": Gemini 평가 결과,
                "정량_분석": 언어 분석 결과,
                "통합_평가": 최종 점수 및 등급,
                "개인_피드백": 맞춤 피드백 리스트
            }
        """
        
        # 1. 질적 평가 (Gemini)
        qualitative = await self.gemini_eval.evaluate(student_input, thought_log)
        
        # 2. 정량 분석 (언어 분석)
        quantitative = self.lang_analyzer.analyze(student_input)
        
        # 3. 통합 점수 계산
        integrated = self._integrate_scores(qualitative, quantitative)
        
        # 4. 개인 맞춤 피드백 생성
        feedback = self._generate_feedback(qualitative, quantitative)
        
        return {
            "질적_평가": qualitative,
            "정량_분석": quantitative,
            "통합_평가": integrated,
            "개인_피드백": feedback
        }
    
    def _integrate_scores(self, qualitative: Dict, quantitative: Dict) -> Dict:
        """
        질적 (70%) + 정량 (30%) 점수 통합
        
        Returns:
            {
                "질적_점수": 70점 만점,
                "정량_점수": 30점 만점,
                "총점": 100점 만점,
                "등급": A+~C+
            }
        """
        
        # 질적 점수 (70% 가중치)
        qual_avg = qualitative.get("평균", 3.0)
        qual_score = round(qual_avg * 0.7 * 20, 1)  # 5점 만점 → 70점 만점
        
        # 정량 점수 (30% 가중치)
        vocab_score = quantitative["어휘_다양성"]["점수"] * 10
        concept_count = quantitative["핵심_개념어"]["총_개념_사용"]
        concept_score = min(concept_count * 2, 10)
        complexity_score = min(quantitative["문장_복잡도"]["점수"], 10)
        quan_score = round(vocab_score + concept_score + complexity_score, 1)
        
        # 총점
        total = round(qual_score + quan_score, 1)
        
        # 등급 산정
        grade = self._calculate_grade(total)
        
        return {
            "질적_점수": qual_score,
            "정량_점수": quan_score,
            "총점": total,
            "등급": grade,
            "세부": {
                "어휘_점수": round(vocab_score, 1),
                "개념_점수": round(concept_score, 1),
                "복잡도_점수": round(complexity_score, 1)
            }
        }
    
    def _calculate_grade(self, total: float) -> str:
        """총점을 기반으로 등급 산정"""
        if total >= 90:
            return "A+"
        elif total >= 85:
            return "A"
        elif total >= 80:
            return "B+"
        elif total >= 75:
            return "B"
        elif total >= 70:
            return "C+"
        elif total >= 65:
            return "C"
        else:
            return "D"
    
    def _generate_feedback(self, qualitative: Dict, quantitative: Dict) -> List[str]:
        """
        개인 맞춤 피드백 생성
        
        Returns:
            피드백 메시지 리스트 (강점 ✅, 개선점 💡, 경고 ⚠️)
        """
        
        feedback = []
        
        # === 강점 피드백 ===
        
        # 질적 평가 강점
        if qualitative.get("평균", 0) >= 4:
            feedback.append("✅ 사고의 깊이가 우수합니다.")
        
        if qualitative.get("추론_깊이", {}).get("점수", 0) >= 4:
            feedback.append("✅ 논리적 추론 능력이 뛰어납니다.")
        
        if qualitative.get("비판적_사고", {}).get("점수", 0) >= 4:
            feedback.append("✅ 비판적 사고 능력이 뛰어납니다.")
        
        if qualitative.get("문학적_이해", {}).get("점수", 0) >= 4:
            feedback.append("✅ 문학적 이해도가 높습니다.")
        
        # 정량 분석 강점
        vocab_score = quantitative["어휘_다양성"]["점수"]
        if vocab_score >= 0.6:
            feedback.append("✅ 다양한 어휘를 사용하고 있습니다.")
        
        concept_count = quantitative["핵심_개념어"]["총_개념_사용"]
        if concept_count >= 5:
            feedback.append("✅ 핵심 개념을 잘 활용하고 있습니다.")
        
        complexity = quantitative["문장_복잡도"]["점수"]
        if complexity >= 8:
            feedback.append("✅ 복잡하고 심층적인 문장을 구사합니다.")
        
        sentiment = quantitative["감정_톤"]["학습_태도"]
        if sentiment in ["탐구적", "적극적"]:
            feedback.append(f"✅ 학습 태도가 {sentiment}입니다.")
        
        # === 개선점 피드백 ===
        
        # 질적 평가 개선점
        if qualitative.get("추론_깊이", {}).get("점수", 0) < 3:
            feedback.append("💡 추론을 더 깊이 있게 전개해보세요.")
        
        if qualitative.get("비판적_사고", {}).get("점수", 0) < 3:
            feedback.append("💡 다양한 관점에서 생각해보세요.")
        
        if qualitative.get("문학적_이해", {}).get("점수", 0) < 3:
            feedback.append("💡 작품의 시대적 배경을 고려해보세요.")
        
        # 정량 분석 개선점
        if vocab_score < 0.4:
            feedback.append("💡 더 다양한 어휘를 사용해보세요.")
        
        if concept_count < 3:
            feedback.append("💡 핵심 개념어를 더 활용해보세요.")
        
        repetition_rate = quantitative["반복_패턴"]["반복률"]
        if repetition_rate > 0.2:
            feedback.append("💡 다양한 표현을 시도해보세요.")
        
        if complexity < 4:
            feedback.append("💡 문장을 좀 더 정교하게 다듬어보세요.")
        
        if sentiment == "소극적":
            feedback.append("💡 학습에 더 흥미를 가져보세요.")
        
        # === 경고 피드백 ===
        
        # 매우 낮은 점수
        if qualitative.get("평균", 0) < 2:
            feedback.append("⚠️ 기본적인 이해도가 부족합니다. 작품을 다시 읽어보세요.")
        
        if vocab_score < 0.3:
            feedback.append("⚠️ 어휘력이 매우 부족합니다. 다양한 표현을 연습하세요.")
        
        # 피드백이 없는 경우 기본 메시지
        if not feedback:
            feedback.append("✅ 적절한 수준의 답변입니다.")
        
        return feedback
    
    async def quick_evaluate(self, student_input: str) -> Dict:
        """
        간단한 평가 (사고로그 없이)
        
        Args:
            student_input: 학생 답변
        
        Returns:
            통합 평가 결과
        """
        return await self.evaluate_comprehensive(student_input, "")
