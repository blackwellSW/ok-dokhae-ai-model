"""
Thinking Path 엔진
역할: 사고 단계 관리,

 동적 질문 생성, 게이트 통과 로직
"""

import uuid
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    ThinkingStage, QuestionTemplate, AnswerEvaluation, 
    GateResult, LearningState, ThinkingLog
)
from app.services.gemini_evaluator import GeminiEvaluator
from app.services.language_analyzer import LanguageAnalyzer
import google.generativeai as genai
from app.core.config import get_settings

settings = get_settings()


class ThinkingPathEngine:
    """사고 단계 관리 및 질문 생성 엔진"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gemini_eval = GeminiEvaluator()
        self.lang_analyzer = LanguageAnalyzer()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def get_current_stage(self, stage_id: str) -> Optional[Dict]:
        """현재 단계 정보 조회"""
        stmt = select(ThinkingStage).where(ThinkingStage.stage_id == stage_id)
        result = await self.db.execute(stmt)
        stage = result.scalar_one_or_none()
        
        if not stage:
            return None
        
        return {
            "stage_id": stage.stage_id,
            "stage_name": stage.stage_name,
            "sequence": stage.sequence,
            "objective": stage.objective,
            "expected_skill": stage.expected_skill,
            "pass_criteria": stage.pass_criteria,
            "min_answer_length": stage.min_answer_length,
            "required_elements": stage.required_elements
        }
    
    async def generate_dynamic_question(
        self,
        state_id: str,
        stage_id: str,
        context: Dict
    ) -> str:
        """
        동적 질문 생성 (분기 로직 포함)
        
        Args:
            state_id: 학습 상태 ID
            stage_id: 현재 단계 ID
            context: 콘텐츠 정보 (작품, 지문 등)
        
        Returns:
            질문 텍스트
        """
        
        # 학습 상태 조회 (약점 파악)
        stmt = select(LearningState).where(LearningState.state_id == state_id)
        result = await self.db.execute(stmt)
        state = result.scalar_one_or_none()
        
        weak_skills = state.weak_skills if state else {}
        
        # 현재 단계 정보
        stage_info = await self.get_current_stage(stage_id)
        if not stage_info:
            return "단계 정보를 찾을 수 없습니다."
        
        # 템플릿 선택 (약점 기반)
        template = await self._select_question_template(stage_id, weak_skills)
        
        if template:
            # 템플릿 기반 질문
            question = await self._fill_template(template, context)
        else:
            # LLM 기반 동적 질문 생성
            question = await self._generate_llm_question(stage_info, context, weak_skills)
        
        return question
    
    async def _select_question_template(
        self,
        stage_id: str,
        weak_skills: Dict
    ) -> Optional[Dict]:
        """약점 기반 템플릿 선택"""
        
        # 약점이 있으면 remedial 템플릿 우선
        if weak_skills:
            main_weakness = max(weak_skills.items(), key=lambda x: x[1])[0]
            
            stmt = select(QuestionTemplate).where(
                QuestionTemplate.stage_id == stage_id,
                QuestionTemplate.template_type == "remedial"
            )
            result = await self.db.execute(stmt)
            templates = result.scalars().all()
            
            for template in templates:
                if template.use_when.get("weak_skill") == main_weakness:
                    return {
                        "template_id": template.template_id,
                        "template_text": template.template_text,
                        "variables": template.variables
                    }
        
        #  기본 템플릿
        stmt = select(QuestionTemplate).where(
            QuestionTemplate.stage_id == stage_id,
            QuestionTemplate.template_type == "basic"
        ).limit(1)
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        
        if template:
            return {
                "template_id": template.template_id,
                "template_text": template.template_text,
                "variables": template.variables
            }
        
        return None
    
    async def _fill_template(self, template: Dict, context: Dict) -> str:
        """템플릿에 변수 채우기"""
        question = template["template_text"]
        
        for var in template["variables"]:
            if var in context:
                question = question.replace(f"{{{var}}}", str(context[var]))
        
        return question
    
    async def _generate_llm_question(
        self,
        stage_info: Dict,
        context: Dict,
        weak_skills: Dict
    ) -> str:
        """LLM 기반 동적 질문 생성"""
        
        weakness_context = ""
        if weak_skills:
            main_weakness = max(weak_skills.items(), key=lambda x: x[1])[0]
            weakness_context = f"\n학생의 약점: {main_weakness}을 보완하는 질문을 생성하세요."
        
        prompt = f"""당신은 고전문학 교육 전문가입니다. 다음 조건에 맞는 질문을 생성하세요.

[현재 단계]
- 단계명: {stage_info['stage_name']}
- 목표: {stage_info['objective']}
- 기대 기술: {stage_info['expected_skill']}

[작품 정보]
- 작품: {context.get('work_title', '미상')}
- 지문: {context.get('chunk_content', '')}

{weakness_context}

질문만 출력하세요. 설명이나 부가 텍스트 없이 질문 하나만 작성하세요.
"""
        
        try:
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            return question
        except Exception as e:
            print(f"LLM 질문 생성 오류: {e}")
            return f"{stage_info['stage_name']}에 대해 설명해보세요."
    
    async def evaluate_and_gate(
        self,
        state_id: str,
        stage_id: str,
        question: str,
        answer: str,
        time_spent: int
    ) -> Dict:
        """
        답변 평가 및 게이트 통과 판단
        
        Returns:
            {
                "passed": bool,
                "action": str,  # pass, retry, hint, strategy_change
                "feedback": str,
                "hint": str (optional),
                "next_stage_id": str (optional),
                "fail_reason": str (optional),
                "weak_skill": str (optional)
            }
        """
        
        # 1. 형식 체크
        stage_info = await self.get_current_stage(stage_id)
        format_check = self._check_format(answer, stage_info)
        
        if not format_check["passed"]:
            return await self._create_retry_result(
                state_id,
                stage_id,
                question,
                answer,
                "형식 미달",
                format_check["fail_reason"]
            )
        
        # 2. 의미 평가 (LLM + 언어 분석)
        qualitative = await self.gemini_eval.evaluate(answer, "")
        quantitative = self.lang_analyzer.analyze(answer)
        
        semantic_check = self._check_semantics(
            answer,
            qualitative,
            quantitative,
            stage_info
        )
        
        # 3. 평가 결과 저장
        eval_id = str(uuid.uuid4())
        evaluation = AnswerEvaluation(
            eval_id=eval_id,
            state_id=state_id,
            stage_id=stage_id,
            question=question,
            answer=answer,
            passed=semantic_check["passed"],
            fail_reason=semantic_check.get("fail_reason"),
            weak_skill=semantic_check.get("weak_skill"),
            format_check=format_check,
            semantic_check=semantic_check,
            qualitative_score=qualitative.get("평균", 0),
            quantitative_score=quantitative["어휘_다양성"]["점수"],
            evaluation_strategy="hybrid"
        )
        
        self.db.add(evaluation)
        
        # 4. 사고 로그 저장
        thinking_log = ThinkingLog(
            log_id=str(uuid.uuid4()),
            state_id=state_id,
            stage_id=stage_id,
            question=question,
            answer=answer,
            eval_result=semantic_check,
            strategy_used="default",
            time_spent=time_spent,
            thinking_pattern=qualitative,
            skill_demonstrated=self._extract_skills(semantic_check),
            error_type=semantic_check.get("weak_skill")
        )
        
        self.db.add(thinking_log)
        
        # 5. 게이트 판단
        if semantic_check["passed"]:
            # 통과 → 다음 단계
            result = await self._create_pass_result(
                eval_id,
                state_id,
                stage_id,
                qualitative
            )
        else:
            # 실패 → 재시도/힌트
            # 재시도 횟수 확인
            retry_count = await self._get_retry_count(state_id, stage_id)
            
            if retry_count >= 2:
                # 전략 변경
                result = await self._create_strategy_change_result(
                    eval_id,
                    state_id,
                    stage_id,
                    semantic_check
                )
            else:
                # 재시도
                result = await self._create_retry_result(
                    state_id,
                    stage_id,
                    question,
                    answer,
                    semantic_check.get("fail_reason", "평가 미통과"),
                    semantic_check.get("weak_skill")
                )
        
        await self.db.commit()
        
        return result
    
    def _check_format(self, answer: str, stage_info: Dict) -> Dict:
        """형식 체크"""
        
        # 글자 수
        if len(answer) < stage_info.get("min_answer_length", 20):
            return {
                "passed": False,
                "fail_reason": f"답변이 너무 짧습니다. 최소 {stage_info.get('min_answer_length', 20)}자 이상 작성해주세요."
            }
        
        # 문장 수
        sentences = [s for s in answer.split('.') if s.strip()]
        if len(sentences) < 2:
            return {
                "passed": False,
                "fail_reason": "최소 2문장 이상으로 답변해주세요."
            }
        
        # 필수 요소 (향후 확장)
        required_elements = stage_info.get("required_elements", [])
        # TODO: 더 정교한 요소 체크
        
        return {"passed": True}
    
    def _check_semantics(
        self,
        answer: str,
        qualitative: Dict,
        quantitative: Dict,
        stage_info: Dict
    ) -> Dict:
        """의미 평가"""
        
        # 기준 점수
        qual_avg = qualitative.get("평균", 0)
        vocab_score = quantitative["어휘_다양성"]["점수"]
        
        # Pass 기준
        pass_criteria = stage_info.get("pass_criteria", {})
        min_qual_score = pass_criteria.get("min_qualitative", 3.0)
        
        if qual_avg < min_qual_score:
            # 약점 파악
            weak_skill = self._identify_weak_skill(qualitative)
            
            return {
                "passed": False,
                "fail_reason": f"사고의 깊이가 부족합니다. (평균 {qual_avg}/5.0)",
                "weak_skill": weak_skill
            }
        
        if vocab_score < 0.3:
            return {
                "passed": False,
                "fail_reason": "어휘가 너무 단순합니다. 더 다양한 표현을 사용해보세요.",
                "weak_skill": "어휘_표현력"
            }
        
        return {"passed": True}
    
    def _identify_weak_skill(self, qualitative: Dict) -> str:
        """약점 기술 파악"""
        scores = {
            "추론깊이": qualitative.get("추론_깊이", {}).get("점수", 3),
            "비판적사고": qualitative.get("비판적_사고", {}).get("점수", 3),
            "문학적이해": qualitative.get("문학적_이해", {}).get("점수", 3)
        }
        
        # 가장 낮은 점수
        weak_skill = min(scores.items(), key=lambda x: x[1])[0]
        return weak_skill
    
    def _extract_skills(self, semantic_check: Dict) -> List[str]:
        """발휘된 기술 추출"""
        skills = []
        
        if semantic_check.get("passed"):
            skills.append("기본사고")
        
        return skills
    
    async def _get_retry_count(self, state_id: str, stage_id: str) -> int:
        """현재 단계의 재시도 횟수 조회"""
        stmt = select(GateResult).where(
            GateResult.state_id == state_id,
            GateResult.action.in_(["retry", "hint"])
        )
        result = await self.db.execute(stmt)
        results = result.scalars().all()
        
        # 최근 단계의 재시도만 카운트
        recent_retries = [r for r in results if "retry" in r.action or "hint" in r.action]
        return len(recent_retries)
    
    async def _create_pass_result(
        self,
        eval_id: str,
        state_id: str,
        stage_id: str,
        qualitative: Dict
    ) -> Dict:
        """통과 결과 생성"""
        
        # 다음 단계 찾기
        current_stage = await self.get_current_stage(stage_id)
        next_sequence = current_stage["sequence"] + 1
        
        stmt = select(ThinkingStage).where(ThinkingStage.sequence == next_sequence)
        result = await self.db.execute(stmt)
        next_stage = result.scalar_one_or_none()
        
        next_stage_id = next_stage.stage_id if next_stage else None
        
        # 게이트 결과 저장
        gate_result = GateResult(
            result_id=str(uuid.uuid4()),
            eval_id=eval_id,
            state_id=state_id,
            action="pass",
            next_stage_id=next_stage_id,
            feedback=f"훌륭합니다! {current_stage['stage_name']}을(를) 통과했습니다.",
            retry_count=0
        )
        
        self.db.add(gate_result)
        
        return {
            "passed": True,
            "action": "pass",
            "feedback": gate_result.feedback,
            "next_stage_id": next_stage_id
        }
    
    async def _create_retry_result(
        self,
        state_id: str,
        stage_id: str,
        question: str,
        answer: str,
        fail_reason: str,
        weak_skill: Optional[str] = None
    ) -> Dict:
        """재시도 결과 생성"""
        
        eval_id = str(uuid.uuid4())
        
        # 힌트 생성
        hint = await self._generate_hint(stage_id, fail_reason, weak_skill)
        
        gate_result = GateResult(
            result_id=str(uuid.uuid4()),
            eval_id=eval_id,
            state_id=state_id,
            action="retry",
            feedback=fail_reason,
            hint=hint,
            retry_count=1
        )
        
        self.db.add(gate_result)
        
        return {
            "passed": False,
            "action": "retry",
            "feedback": fail_reason,
            "hint": hint,
            "fail_reason": fail_reason,
            "weak_skill": weak_skill
        }
    
    async def _create_strategy_change_result(
        self,
        eval_id: str,
        state_id: str,
        stage_id: str,
        semantic_check: Dict
    ) -> Dict:
        """전략 변경 결과"""
        
        gate_result = GateResult(
            result_id=str(uuid.uuid4()),
            eval_id=eval_id,
            state_id=state_id,
            action="strategy_change",
            feedback="다른 방법으로 접근해봅시다.",
            hint="예시를 통해 이해해볼까요?",
            retry_count=0
        )
        
        self.db.add(gate_result)
        
        return {
            "passed": False,
            "action": "strategy_change",
            "feedback": "다른 방법으로 접근해봅시다.",
            "hint": "예시를 통해 이해해볼까요?",
            "fail_reason": semantic_check.get("fail_reason"),
            "weak_skill": semantic_check.get("weak_skill")
        }
    
    async def _generate_hint(
        self,
        stage_id: str,
        fail_reason: str,
        weak_skill: Optional[str]
    ) -> str:
        """힌트 생성"""
        
        stage_info = await self.get_current_stage(stage_id)
        
        prompt = f"""학생이 다음 단계에서 실패했습니다. 힌트를 생성하세요.

[단계]: {stage_info['stage_name']}
[실패 이유]: {fail_reason}
[약점]: {weak_skill if weak_skill else '없음'}

직접 답을 주지 말고, 생각의 방향을 제시하는 힌트만 작성하세요.
2-3문장 이내로 간단히 작성하세요.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return "다시 한 번 차근차근 생각해보세요."
